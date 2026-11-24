import asyncio

import pytest

from afterlife import crawl
from afterlife.classify import Seen
from afterlife.db import connect, save_check, save_stories


class Tally:
    def __init__(self):
        self.saved = []

    def add(self, story, outcome):
        self.saved.append((story["id"], outcome["evidence"]))


def stories(count):
    return [
        {"id": i, "url": f"https://slow.example/{i}", "title": f"Story {i}", "before": None}
        for i in range(count)
    ]


def run_site(monkeypatch, outcome, count=8):
    async def fake_check(fetcher, github, story):
        return dict(outcome)

    monkeypatch.setattr(crawl, "check", fake_check)
    tally = Tally()
    asyncio.run(crawl.crawl_site(None, None, stories(count), tally))
    return tally.saved


def test_a_rate_limiting_host_leaves_the_rest_for_next_time(monkeypatch):
    saved = run_site(monkeypatch, {"fate": "unsure", "evidence": "wall-429", "status": 429})
    assert [story for story, _ in saved] == [0, 1, 2, 3, 4]


def test_a_host_that_stops_answering_leaves_the_rest_for_their_own_tries(monkeypatch):
    saved = run_site(monkeypatch, {"fate": "unsure", "evidence": "noanswer"})
    assert [story for story, _ in saved] == [0, 1, 2, 3, 4]


def test_one_good_answer_resets_the_count(monkeypatch):
    answers = iter(["noanswer"] * 4 + ["alive"] + ["noanswer"] * 4)

    async def fake_check(fetcher, github, story):
        return {"fate": "unsure", "evidence": next(answers)}

    monkeypatch.setattr(crawl, "check", fake_check)
    tally = Tally()
    asyncio.run(crawl.crawl_site(None, None, stories(9), tally))
    assert len(tally.saved) == 9


def test_reclassify_brings_old_verdicts_up_to_date(tmp_path):
    db = connect(tmp_path / "afterlife.db")
    url, title = "https://blog.example.com/accounting.html", "The math of consulting"
    save_stories(
        db,
        [
            {
                "id": 1,
                "url": url,
                "title": title,
                "points": 100,
                "comments": 0,
                "posted": 0,
                "show_hn": 0,
            }
        ],
    )
    stale = {
        "fate": "elsewhere",
        "evidence": "home",
        "status": 200,
        "title": title,
        "final": "https://longform.example.com/accounting/",
        "detail": {"hops": 1, "html": True},
    }
    save_check(db, 1, 100, stale)
    save_check(db, 1, 200, {"fate": "dead", "evidence": "404", "detail": {"via": "github"}})
    crawl.reclassify(db)
    fates = [tuple(row) for row in db.execute("select fate, evidence from checks order by id")]
    assert fates == [("moved", "moved"), ("dead", "404")]


def test_a_host_that_stalls_every_request_is_a_wall_for_the_rest(monkeypatch):
    saved = run_site(monkeypatch, {"fate": "unsure", "evidence": "stall"})
    assert len(saved) == 8 and {evidence for _, evidence in saved} == {"stall"}


class Walled:
    def __init__(self, home):
        self.home_page = home

    async def get(self, url):
        return Seen(url, error="stall")

    async def home(self, origin):
        return self.home_page


def stalled(home):
    story = {"url": "https://slow.example/2014/a-story", "title": "A story", "before": None}
    return asyncio.run(crawl.check(Walled(home), None, story))["evidence"]


def test_a_story_that_stalls_on_a_host_whose_home_page_answers_isnt_answering():
    assert stalled(Seen("https://slow.example/", 200, html=True, title="Slow")) == "noanswer"


@pytest.mark.parametrize(
    "home",
    [
        Seen("https://slow.example/", 403),
        Seen("https://slow.example/", error="robots"),
        Seen("https://slow.example/", error="stall"),
        Seen("https://slow.example/", 200, html=True, title="Just a moment..."),
    ],
)
def test_a_stall_stays_a_wall_unless_the_home_page_plainly_answers(home):
    assert stalled(home) == "stall"


def test_a_server_error_gets_another_go_a_week_later(tmp_path):
    db = connect(tmp_path / "afterlife.db")
    story = {"url": "https://a.example/x", "title": "X", "points": 100, "comments": 0}
    save_stories(db, [{"id": 1, **story, "posted": 0, "show_hn": 0}])
    save_check(db, 1, 0, {"fate": "unsure", "evidence": "status-503", "status": 503})
    assert [row["id"] for row in crawl.pending(db, int(crawl.RECHECK_AFTER) + 1)] == [1]


def checked_long_ago(tmp_path, *ids):
    db = connect(tmp_path / "afterlife.db")
    story = {"title": "A story", "points": 100, "comments": 0, "posted": 0, "show_hn": 0}
    save_stories(db, [{**story, "id": i, "url": f"https://a.example/{i}"} for i in ids])
    for i in ids:
        save_check(db, i, 0, {"fate": "alive", "evidence": "alive"})
    return db


WEEK_527 = 527 * 7 * 86_400  # 527 % 52 is 7, so it's the turn of ids 7, 59, 111...


def test_a_recheck_adds_this_weeks_fifty_second_of_the_stories(tmp_path):
    db = checked_long_ago(tmp_path, 6, 7, 8, 59, 60)
    assert crawl.pending(db, WEEK_527) == []
    assert [row["id"] for row in crawl.pending(db, WEEK_527, recheck=True)] == [7, 59]


def test_a_recheck_leaves_a_story_checked_this_month_alone(tmp_path):
    db = checked_long_ago(tmp_path, 7, 59)
    save_check(db, 59, WEEK_527 - 29 * 86_400, {"fate": "alive", "evidence": "alive"})
    assert [row["id"] for row in crawl.pending(db, WEEK_527, recheck=True)] == [7]
