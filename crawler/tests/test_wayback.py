import asyncio
import time

import aiohttp

from afterlife import wayback
from afterlife.db import connect, save_check, save_stories
from afterlife.net import NoAnswer
from afterlife.wayback import Wayback, changed, due, save_capture

URL = "https://straight2spam.xyz/"


def test_a_capture_wayback_cant_serve_is_no_capture_not_an_outage():
    class Garbled:
        def get(self, *args, **kwargs):
            raise aiohttp.ClientResponseError(None, ())

    assert asyncio.run(Wayback(Garbled()).then("https://koreader.rocks/", 0)) is None


def test_a_repurposed_home_page_is_spotted():
    then = ("20200101000000", "Straight2Spam - disposable email")
    assert changed(then, "A pollinator garden blog", URL)


def test_a_home_page_that_kept_its_name_is_fine():
    then = ("20200101000000", "FreedomBox Private Cloud Server")
    assert not changed(
        then, "Overview | FreedomBox Private Cloud Server", "https://freedombox.org/"
    )


def test_no_capture_or_no_title_means_no_verdict():
    assert not changed(None, "Anything", URL)
    assert not changed(("20200101000000", ""), "Anything", URL)
    assert not changed(("20200101000000", "Something"), "", URL)


def test_the_pass_picks_flagged_home_pages_and_walled_links_once(tmp_path):
    db = connect(tmp_path / "afterlife.db")
    stories = [
        {
            "id": i,
            "url": f"https://site{i}.example/",
            "title": f"Story {i}",
            "points": 100,
            "comments": 0,
            "posted": 0,
            "show_hn": 0,
        }
        for i in range(1, 5)
    ]
    save_stories(db, stories)
    save_check(db, 1, 10, {"fate": "alive", "evidence": "alive", "detail": {"then": True}})
    save_check(db, 2, 10, {"fate": "alive", "evidence": "alive"})
    save_check(db, 3, 10, {"fate": "unsure", "evidence": "wall-403"})
    save_check(db, 4, 10, {"fate": "unsure", "evidence": "noanswer"})
    homes = "latest.fate = 'alive' and latest.detail like '%\"then\": true%'"
    walled = "latest.fate = 'unsure' and latest.evidence != 'noanswer'"
    assert [s["id"] for s in due(db, "then", homes)] == [1]
    assert [s["id"] for s in due(db, "good", walled)] == [3]
    save_capture(db, 3, "good", ("20200101000000", 200))
    assert due(db, "good", walled) == []


def test_out_of_minutes_the_wayback_pass_keeps_what_it_found(tmp_path, monkeypatch):
    db, clock = connect(tmp_path / "afterlife.db"), [0.0]
    story = {"title": "A story", "points": 100, "comments": 0, "posted": 0, "show_hn": 0}
    save_stories(db, [{**story, "id": i, "url": f"https://site{i}.example/"} for i in range(1, 6)])
    for i in range(1, 6):
        save_check(db, i, 10, {"fate": "unsure", "evidence": "wall-403"})

    async def slow_lookup(self, url):
        clock[0] += 25
        await asyncio.sleep(0)
        return ("20200101000000", 200)

    monkeypatch.setattr(time, "monotonic", lambda: clock[0])
    monkeypatch.setattr(Wayback, "last_good", slow_lookup)
    asyncio.run(wayback.run(db, minutes=1))
    found = connect(tmp_path / "afterlife.db").execute("select count(*) from captures").fetchone()
    assert 0 < found[0] < 5


def walled_db(tmp_path):
    db = connect(tmp_path / "afterlife.db")
    story = {"title": "A story", "points": 100, "comments": 0, "posted": 0, "show_hn": 0}
    save_stories(db, [{**story, "id": 1, "url": "https://site1.example/"}])
    save_check(db, 1, 10, {"fate": "unsure", "evidence": "wall-403"})
    return db


def test_a_short_outage_is_waited_out(tmp_path, monkeypatch):
    db, answers = walled_db(tmp_path), iter([NoAnswer("wayback"), NoAnswer("wayback"), None])

    async def flaky(self, url):
        if isinstance(answer := next(answers), NoAnswer):
            raise answer
        return ("20200101000000", 200)

    monkeypatch.setattr(wayback, "OUTAGE_WAIT", 0)
    monkeypatch.setattr(Wayback, "last_good", flaky)
    asyncio.run(wayback.run(db))
    assert db.execute("select count(*) from captures").fetchone()[0] == 1


def test_a_long_outage_ends_the_pass_with_nothing_made_up(tmp_path, monkeypatch):
    db, calls = walled_db(tmp_path), []

    async def silent(self, url):
        calls.append(url)
        raise NoAnswer("wayback")

    monkeypatch.setattr(wayback, "OUTAGE_WAIT", 0)
    monkeypatch.setattr(Wayback, "last_good", silent)
    asyncio.run(wayback.run(db))
    assert len(calls) == wayback.PATIENCE + 1
    assert db.execute("select count(*) from captures").fetchone()[0] == 0
