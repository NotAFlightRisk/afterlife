import asyncio

import aiohttp

from afterlife.wayback import Wayback, changed

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
    from afterlife.db import connect, save_check, save_stories
    from afterlife.wayback import due, save_capture

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
