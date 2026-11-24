"""HN's own front page for each day of the coming week, 5, 10 and 15 years back, so the day view
can show them as HN ranked them. Fetched at the pace HN's robots.txt asks for."""

import logging
import re
import sqlite3
from collections import defaultdict
from datetime import UTC, date, datetime, timedelta

from . import hn
from .net import MAX_BODY, Fetcher, NoAnswer, session

FRONT = "https://news.ycombinator.com/front"
YEARS = (5, 10, 15)
ROW = re.compile(r'<tr class="athing[^"]*" id="(\d+)"')
log = logging.getLogger(__name__)


def years_before(day: date, years: int) -> date:
    """The same date that many years back, or the 28th for a leap day."""
    try:
        return day.replace(year=day.year - years)
    except ValueError:
        return day.replace(year=day.year - years, day=28)


def due(db: sqlite3.Connection, today: date) -> list[str]:
    """The week either side of today, 5, 10 and 15 years back, bar any already stored, so a
    week the job missed gets picked up the week after."""
    week = [today + timedelta(days=ahead) for ahead in range(-7, 7)]
    days = {years_before(day, years).isoformat() for day in week for years in YEARS}
    stored = {day for (day,) in db.execute("select distinct day from fronts")}
    return sorted(days - stored)


def ranked(page: str) -> list[int]:
    return [int(story) for story in ROW.findall(page)]


async def front(fetcher: Fetcher, day: str) -> list[int]:
    """The day's 30 story ids in rank order, or NoAnswer if HN won't show us all of them."""
    url = f"{FRONT}?day={day}"
    if problem := await fetcher.allowed(url):
        raise NoAnswer(problem)
    reply = await fetcher.send(url, MAX_BODY)
    if reply.status != 200:
        raise NoAnswer(f"status-{reply.status}")
    stories = ranked(reply.text)
    if len(stories) != 30:
        raise NoAnswer(f"{len(stories)} stories")
    return stories


async def fetch(db: sqlite3.Connection, fetcher: Fetcher, days: list[str]):
    for day in days:
        try:
            stories = await front(fetcher, day)
        except NoAnswer as e:
            log.warning("Skipping HN's front page for %s (%s)", day, e.kind)
            continue
        rows = [(day, rank, story) for rank, story in enumerate(stories, 1)]
        db.executemany("insert into fronts values (?, ?, ?)", rows)
        db.commit()


def front_pages(db: sqlite3.Connection) -> dict[str, list[int]]:
    """Each stored day's story ids, in HN's order."""
    pages = defaultdict(list)
    for day, story in db.execute("select day, story from fronts order by day, rank"):
        pages[day].append(story)
    return dict(pages)


async def run(db: sqlite3.Connection):
    days = due(db, datetime.now(UTC).date())
    log.info("%d front pages to fetch", len(days))
    async with session() as http:
        await fetch(db, Fetcher(http), days)
    missing = db.execute(
        "select distinct story from fronts where story not in (select id from stories)"
    ).fetchall()
    log.info("%d front-page stories are new to us, asking Algolia", len(missing))
    await hn.fill_in(db, [story for (story,) in missing])
