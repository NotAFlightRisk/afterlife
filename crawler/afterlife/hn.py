"""Every story with 100+ points, plus each day's top 30, from Algolia's HN search."""

import asyncio
import logging
import sqlite3
import time
from datetime import UTC, datetime

import aiohttp

from .db import save_stories
from .net import UA

API = "https://hn.algolia.com/api/v1/search_by_date"
FIELDS = "title,url,points,num_comments,created_at_i,_tags"
FIRST_DAY = int(datetime(2007, 2, 19, tzinfo=UTC).timestamp())
DAY, MONTH = 86_400, 30 * 86_400
log = logging.getLogger(__name__)


class Algolia:
    """Algolia allows 10,000 requests an hour per IP, so two a second stays well clear."""

    def __init__(self, session: aiohttp.ClientSession, per_second: float = 2):
        self.session, self.gap, self.free_at = session, 1 / per_second, 0.0
        self.lock = asyncio.Lock()

    async def search(self, start: int, stop: int, min_points: int, size: int = 1000) -> dict:
        async with self.lock:
            await asyncio.sleep(max(0, self.free_at - time.monotonic()))
            self.free_at = time.monotonic() + self.gap
        params = {
            "tags": "story",
            "hitsPerPage": size,
            "attributesToRetrieve": FIELDS,
            "attributesToHighlight": "[]",
            "numericFilters": f"created_at_i>={start},created_at_i<{stop},points>={min_points}",
        }
        for attempt in range(6):
            try:
                async with self.session.get(API, params=params, headers={"User-Agent": UA}) as r:
                    r.raise_for_status()
                    return await r.json()
            except (TimeoutError, aiohttp.ClientError) as e:
                log.warning("Algolia fell over (%s), trying again shortly", e)
                await asyncio.sleep(5 * 2**attempt)
        raise RuntimeError(f"Algolia won't answer for {params['numericFilters']}")


def story(hit: dict) -> dict:
    return {
        "id": int(hit["objectID"]),
        "url": hit.get("url") or None,
        "title": hit.get("title") or "",
        "points": hit.get("points") or 0,
        "comments": hit.get("num_comments") or 0,
        "posted": hit["created_at_i"],
        "show_hn": int("show_hn" in hit.get("_tags", [])),
    }


def todo(db: sqlite3.Connection, start: int, stop: int) -> bool:
    return (
        db.execute("select 1 from fetched where start = ? and stop = ?", (start, stop)).fetchone()
        is None
    )


def done(db: sqlite3.Connection, start: int, stop: int):
    db.execute("insert or replace into fetched values (?, ?)", (start, stop))
    db.commit()


async def popular(api: Algolia, db: sqlite3.Connection, until: int):
    """Every 100+ point story, a month at a time, halving any window that's over Algolia's 1,000."""
    windows = [(start, min(start + MONTH, until)) for start in range(FIRST_DAY, until, MONTH)]
    while windows:
        start, stop = windows.pop()
        if not todo(db, start, stop):
            continue
        found = await api.search(start, stop, 100)
        if found["nbHits"] > 1000:
            middle = (start + stop) // 2
            windows += [(start, middle), (middle, stop)]
            continue
        save_stories(db, [story(h) for h in found["hits"]])
        done(db, start, stop)
    log.info(
        "%d stories with 100+ points", db.execute("select count(*) from stories").fetchone()[0]
    )


async def thin_day(api: Algolia, db: sqlite3.Connection, day: int):
    """Top 30 by points for a day that had fewer than 30 stories reach 100."""
    found = await api.search(day, day + DAY, 10)
    if found["nbHits"] > 1000:
        found = await api.search(day, day + DAY, 50)
    elif found["nbHits"] < 30:
        found = await api.search(day, day + DAY, 0)
    top = sorted(found["hits"], key=lambda h: (-(h.get("points") or 0), int(h["objectID"])))[:30]
    save_stories(db, [story(h) for h in top])
    done(db, day, day + DAY)


async def front_pages(api: Algolia, db: sqlite3.Connection, until: int):
    counts = dict(db.execute("select posted / 86400 * 86400, count(*) from stories group by 1"))
    days = [
        d for d in range(FIRST_DAY, until, DAY) if counts.get(d, 0) < 30 and todo(db, d, d + DAY)
    ]
    log.info("%d days need their top 30 filling in", len(days))
    for i in range(0, len(days), 8):
        await asyncio.gather(*(thin_day(api, db, d) for d in days[i : i + 8]))
        if i % 400 == 0:
            log.info("front pages: %d of %d days", i, len(days))


async def fetch(db: sqlite3.Connection):
    """Settled stories only: anything posted in the last two days is still gathering points."""
    until = int(time.time()) // DAY * DAY - 2 * DAY
    async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=60)) as session:
        api = Algolia(session)
        await popular(api, db, until)
        await front_pages(api, db, until)
    log.info("%d stories in all", db.execute("select count(*) from stories").fetchone()[0])
