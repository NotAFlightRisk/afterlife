"""The Wayback Machine, at the 15 or so lookups a minute it puts up with from one IP.

Two jobs. A home page whose title doesn't look like the story gets compared with its capture from
around the day it was posted, since that's where Show HN sites get repurposed. And a link behind a
wall gets the newest capture that isn't one, which annotates the verdict but never changes it.
"""

import asyncio
import json
import logging
import sqlite3
import time
from datetime import UTC, datetime

import aiohttp

from .classify import UNSURE, overlap
from .db import LATEST
from .net import HEADERS, TIMEOUT, Gate, NoAnswer, decode, kind_of, retry_after, title_of
from .urls import host_of

AVAILABLE = "https://archive.org/wayback/available"
CDX = "https://web.archive.org/cdx/search/cdx"
log = logging.getLogger(__name__)


class Wayback:
    def __init__(self, session: aiohttp.ClientSession):
        self.session, self.gate = session, Gate(4.0)

    async def get(self, url: str, params: dict | None = None) -> tuple[int, str]:
        for _ in range(4):
            try:
                async with (
                    self.gate,
                    self.session.get(url, params=params, headers=HEADERS, timeout=TIMEOUT) as r,
                ):
                    if r.status == 429:
                        self.gate.hold(retry_after(r.headers.get("retry-after")))
                        continue
                    return r.status, decode(await r.read(), r.charset)
            except aiohttp.ClientResponseError:
                log.warning("Wayback can't serve %s cleanly, so it counts as no capture", url)
                return 0, ""
            except (TimeoutError, aiohttp.ClientError, OSError) as e:
                log.warning("Wayback fell over on %s (%s)", url, kind_of(e))
                self.gate.hold(60)
        raise NoAnswer("wayback")

    async def then(self, url: str, posted: int) -> tuple[str, str] | None:
        """(timestamp, title) of the capture nearest the day it was posted, if there is one."""
        day = datetime.fromtimestamp(posted, UTC).strftime("%Y%m%d")
        _, body = await self.get(AVAILABLE, {"url": url, "timestamp": day})
        closest = json.loads(body or "{}").get("archived_snapshots", {}).get("closest") or {}
        if not closest.get("available"):
            return None
        raw = f"https://web.archive.org/web/{closest['timestamp']}id_/{url}"
        status, page = await self.get(raw)
        return (closest["timestamp"], title_of(page)) if status == 200 else None

    async def last_good(self, url: str) -> tuple[str, int] | None:
        """(timestamp, status) of the newest capture that answered with a page or a 404."""
        params = {
            "url": url,
            "output": "json",
            "fl": "timestamp,statuscode",
            "limit": "-1",
            "filter": "statuscode:(200|404|410)",
        }
        status, body = await self.get(CDX, params)
        rows = json.loads(body) if status == 200 and body.strip() else []
        return (rows[1][0], int(rows[1][1])) if len(rows) > 1 else None


def changed(then: tuple[str, str] | None, now: str, url: str) -> bool:
    """Does today's home page look like something else entirely, next to its old capture?"""
    if not then or not then[1] or not now:
        return False
    was = then[1]
    return not overlap(was, now, host_of(url)) and was.strip().lower() != now.strip().lower()


def save_capture(db: sqlite3.Connection, story: int, kind: str, found: tuple | None):
    captured, extra = found or (None, None)
    status, title = (extra, None) if isinstance(extra, int) else (None, extra)
    db.execute(
        "insert into captures values (?, ?, ?, ?, ?, ?)",
        (story, int(time.time()), kind, captured, status, title),
    )


def due(db: sqlite3.Connection, kind: str, where: str) -> list[sqlite3.Row]:
    return db.execute(
        f"""with {LATEST}
            select s.id, s.url, s.title, s.posted, latest.id check_id, latest.title now,
              latest.detail from stories s
            join latest on latest.story = s.id
            where {where} and not exists (
              select 1 from captures c where c.story = s.id and c.kind = ? and c.at >= latest.at)
            order by s.points desc""",
        (kind,),
    ).fetchall()


async def compare_home(db: sqlite3.Connection, wayback: Wayback, story: sqlite3.Row):
    then = await wayback.then(story["url"], story["posted"])
    save_capture(db, story["id"], "then", then)
    if changed(then, story["now"], story["url"]):
        detail = {**json.loads(story["detail"]), "captured": then[0], "was": then[1]}
        db.execute(
            "update checks set fate = ?, evidence = ?, detail = ? where id = ?",
            (UNSURE, "home-changed", json.dumps(detail), story["check_id"]),
        )


async def note_last_good(db: sqlite3.Connection, wayback: Wayback, story: sqlite3.Row):
    save_capture(db, story["id"], "good", await wayback.last_good(story["url"]))


async def run(db: sqlite3.Connection, limit: int | None = None, minutes: int | None = None):
    homes = due(db, "then", "latest.fate = 'alive' and latest.detail like '%\"then\": true%'")
    walled = due(db, "good", "latest.fate = 'unsure' and latest.evidence != 'noanswer'")
    log.info(
        "Wayback: %d home pages to compare, %d walled links to look up", len(homes), len(walled)
    )
    async with aiohttp.ClientSession() as session:
        wayback = Wayback(session)
        lookups = [(compare_home, s) for s in homes[:limit]]
        lookups += [(note_last_good, s) for s in walled[:limit]]
        try:
            async with asyncio.timeout(minutes * 60 if minutes else None):
                for done, (look_up, story) in enumerate(lookups, 1):
                    await look_up(db, wayback, story)
                    db.commit()
                    if done % 500 == 0:
                        log.info("Wayback: %d of %d looked up", done, len(lookups))
        except NoAnswer:
            log.warning("The Wayback Machine has stopped answering, the next run carries on")
            return
        except TimeoutError:
            log.info("Wayback: %d-minute limit reached, the next run carries on", minutes)
            return
    log.info("Wayback pass done")
