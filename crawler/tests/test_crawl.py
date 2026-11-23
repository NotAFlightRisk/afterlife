import asyncio

from afterlife import crawl


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


def test_a_host_that_stops_answering_marks_the_rest_as_not_answering(monkeypatch):
    saved = run_site(monkeypatch, {"fate": "unsure", "evidence": "noanswer"})
    assert len(saved) == 8 and {evidence for _, evidence in saved} == {"noanswer"}


def test_one_good_answer_resets_the_count(monkeypatch):
    answers = iter(["noanswer"] * 4 + ["alive"] + ["noanswer"] * 4)

    async def fake_check(fetcher, github, story):
        return {"fate": "unsure", "evidence": next(answers)}

    monkeypatch.setattr(crawl, "check", fake_check)
    tally = Tally()
    asyncio.run(crawl.crawl_site(None, None, stories(9), tally))
    assert len(tally.saved) == 9


def test_reclassify_brings_old_verdicts_up_to_date(tmp_path):
    from afterlife.db import connect, save_check, save_stories

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
