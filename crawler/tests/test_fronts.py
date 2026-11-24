import asyncio
from datetime import date
from pathlib import Path

import pytest

from afterlife import fronts
from afterlife.db import connect
from afterlife.net import Reply

PAGE = (Path(__file__).parent / "fixtures/front-2016-11-24.html").read_text("utf-8")


class HN:
    """Lets us in and serves the same page whatever the day."""

    def __init__(self, status: int, page: str):
        self.reply = Reply(status, None, True, page, {})

    async def allowed(self, url):
        return ""

    async def send(self, url, limit):
        return self.reply


def stored(tmp_path, status, page):
    db = connect(tmp_path / "afterlife.db")
    asyncio.run(fronts.fetch(db, HN(status, page), ["2016-11-24"]))
    return fronts.front_pages(db)


def test_a_front_page_reads_as_its_thirty_stories_in_rank_order():
    stories = fronts.ranked(PAGE)
    assert len(stories) == 30
    assert stories[:3] == [13031492, 13030603, 13027718] and stories[-1] == 13032264


def test_a_front_page_is_kept_in_rank_order(tmp_path):
    page = stored(tmp_path, 200, PAGE)["2016-11-24"]
    assert page[:3] == [13031492, 13030603, 13027718] and len(page) == 30


@pytest.mark.parametrize("status,page", [(503, PAGE), (200, PAGE[: len(PAGE) // 2])])
def test_a_front_page_that_fails_or_comes_up_short_isnt_kept(tmp_path, status, page):
    assert stored(tmp_path, status, page) == {}


def test_a_day_already_stored_isnt_fetched_again(tmp_path):
    db = connect(tmp_path / "afterlife.db")
    db.executemany("insert into fronts values ('2016-11-24', ?, ?)", [(r, r) for r in range(1, 31)])
    days = fronts.due(db, date(2026, 11, 24))
    assert len(days) == 41 and "2016-11-24" not in days


def test_a_week_the_job_missed_is_picked_up_the_week_after(tmp_path):
    days = fronts.due(connect(tmp_path / "afterlife.db"), date(2026, 11, 24))
    assert "2016-11-17" in days and "2016-11-30" in days and "2016-12-01" not in days


def test_a_leap_day_looks_back_to_the_28th(tmp_path):
    days = fronts.due(connect(tmp_path / "afterlife.db"), date(2028, 2, 29))
    assert len(days) == 39 and "2023-02-28" in days
