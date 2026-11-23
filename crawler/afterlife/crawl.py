"""Checks stories a site at a time, 64 sites at once, and keeps every check."""

import asyncio
import json
import logging
import os
import sqlite3
import subprocess
import time
from collections import Counter, defaultdict
from dataclasses import replace

from . import known
from .classify import ALIVE, DEAD, ELSEWHERE, MOVED, UNSURE, Seen, classify, wants_probe, wants_then
from .db import LATEST, save_check
from .net import Fetcher, NoAnswer, session
from .urls import host_of, is_root, origin, site

RECHECK_AFTER = 6.5 * 86_400
TRY_AGAIN = ("noanswer", "badreply", "error", "robots-error", "tls", "wall-429")
STREAK_LIMIT = 5
WALLED = ("reset", "stall")
FAILURES = {"noanswer", "noanswer-twice", "wall-429", *WALLED}
FATES = (ALIVE, MOVED, DEAD, ELSEWHERE, UNSURE)
log = logging.getLogger(__name__)


def github_token() -> str | None:
    if token := os.environ.get("GITHUB_TOKEN"):
        return token
    try:
        found = subprocess.run(["gh", "auth", "token"], capture_output=True, text=True, timeout=10)
        return found.stdout.strip() or None
    except (OSError, subprocess.SubprocessError):
        return None


def pending(db: sqlite3.Connection, now: int) -> list[sqlite3.Row]:
    """Stories never checked, plus those whose last check said to try again in a week."""
    marks = ",".join("?" * len(TRY_AGAIN))
    return db.execute(
        f"""with {LATEST}
            select s.id, s.url, s.title, latest.evidence before from stories s
            left join latest on latest.story = s.id
            where s.url is not null
              and (latest.id is null or (latest.evidence in ({marks}) and latest.at < ?))
            order by s.id""",
        (*TRY_AGAIN, now - RECHECK_AFTER),
    ).fetchall()


def result(url: str, title: str, seen: Seen, before: str | None) -> dict:
    fate, evidence = classify(url, title, seen, before or "")
    detail = {
        "hops": seen.hops,
        "error": seen.error,
        "parked": seen.parked,
        "html": seen.html,
        "probe": seen.probe,
        "gone": seen.gone,
        "then": fate == ALIVE and wants_then(url, title, seen),
    }
    return {
        "fate": fate,
        "evidence": evidence,
        "status": seen.status or None,
        "final": seen.url if seen.url != url else None,
        "title": seen.title or None,
        "detail": {k: v for k, v in detail.items() if v} or None,
    }


async def check(fetcher: Fetcher, github: known.GitHub | None, story: sqlite3.Row) -> dict:
    url, title = story["url"], story["title"]
    try:
        if settled := await known.check(fetcher, github, url):
            return settled
    except NoAnswer as failure:
        return result(url, title, Seen(url, error=failure.kind), story["before"])
    seen = await fetcher.get(url)
    if seen.error in WALLED:
        home = seen.error if is_root(seen.url) else await fetcher.home(origin(seen.url))
        if home not in WALLED:
            seen = replace(seen, error="conn")
    if wants_probe(url, title, seen):
        seen = replace(seen, probe=await fetcher.probe(seen.url))
    return result(url, title, seen, story["before"])


class Tally:
    """Batches writes and says how it's going once a minute."""

    def __init__(self, db: sqlite3.Connection, total: int):
        self.db, self.total, self.fates = db, total, Counter()
        self.started = self.saved_at = time.monotonic()

    def add(self, story: sqlite3.Row, outcome: dict):
        save_check(self.db, story["id"], int(time.time()), outcome)
        self.fates[outcome["fate"]] += 1
        if time.monotonic() - self.saved_at > 10:
            self.db.commit()
            self.saved_at = time.monotonic()

    def report(self):
        done = sum(self.fates.values())
        rate = done / max(time.monotonic() - self.started, 1) * 60
        split = ", ".join(f"{fate} {self.fates[fate]}" for fate in FATES)
        log.info("checked %d of %d (%.0f a minute): %s", done, self.total, rate, split)


async def crawl_site(fetcher, github, stories: list[sqlite3.Row], tally: Tally):
    """One site's stories in turn. A host that fails five times running gets left alone: the
    rest of its stories get the same wall, count as not answering, or wait for the next run if
    it was rate limiting."""
    streak, last_failure = Counter(), {}
    for story in stories:
        url, host = story["url"], host_of(story["url"])
        if streak[host] >= STREAK_LIMIT:
            evidence = last_failure[host]
            if evidence == "wall-429":
                continue
            if evidence in WALLED:
                outcome = {"fate": UNSURE, "evidence": evidence}
            else:
                outcome = result(url, story["title"], Seen(url, error="conn"), story["before"])
            tally.add(story, {**outcome, "detail": {"skipped": True}})
            continue
        try:
            outcome = await check(fetcher, github, story)
        except Exception:
            log.exception("checking %s fell over", story["url"])
            outcome = {"fate": UNSURE, "evidence": "error"}
        failed = outcome["evidence"] in FAILURES
        streak[host] = streak[host] + 1 if failed else 0
        if failed:
            last_failure[host] = outcome["evidence"]
        tally.add(story, outcome)


async def run(db: sqlite3.Connection, workers: int = 64, limit: int | None = None):
    stories = pending(db, int(time.time()))[:limit]
    token = github_token()
    lanes = defaultdict(list)
    for story in stories:
        url = story["url"]
        lanes[known.lane(url, bool(token)) or site(host_of(url))].append(story)
    queue = iter(sorted(lanes.values(), key=len, reverse=True))
    log.info(
        "%d stories to check over %d sites, GitHub API %s",
        len(stories),
        len(lanes),
        "on" if token else "off",
    )
    tally = Tally(db, len(stories))

    async with session() as http:
        fetcher = Fetcher(http)
        github = known.GitHub(fetcher, token) if token else None

        async def worker():
            for group in queue:
                await crawl_site(
                    fetcher, github, sorted(group, key=lambda s: host_of(s["url"])), tally
                )

        async def progress():
            while True:
                await asyncio.sleep(60)
                tally.report()

        reporter = asyncio.create_task(progress())
        await asyncio.gather(*(worker() for _ in range(workers)))
        reporter.cancel()
    db.commit()
    tally.report()


def seen_of(check: sqlite3.Row, detail: dict) -> Seen:
    """Rebuild what a stored check saw, so the classifier can have another go at it."""
    probe = detail.get("probe")
    return Seen(
        check["final"] or check["url"],
        check["status"] or 0,
        detail.get("hops", 0),
        detail.get("html", False),
        check["title"] or "",
        detail.get("parked", False),
        detail.get("error", ""),
        tuple(probe) if probe else None,
        detail.get("gone", 0),
    )


def reclassify(db: sqlite3.Connection):
    """Re-run the classifier over every stored check, for when it's learnt something new.
    API answers, skipped hosts and the Wayback pass's verdicts are left as they are."""
    checks = db.execute(
        """select c.id, c.story, c.fate, c.evidence, c.status, c.final, c.title, c.detail, s.url,
             s.title hn from checks c join stories s on s.id = c.story order by c.id"""
    ).fetchall()
    before, changed = {}, Counter()
    for check in checks:
        detail = json.loads(check["detail"] or "{}")
        fixed = {"via", "skipped", "captured"} & detail.keys() or check["evidence"] == "error"
        outcome = {"fate": check["fate"], "evidence": check["evidence"]}
        if not fixed:
            outcome = result(
                check["url"], check["hn"], seen_of(check, detail), before.get(check["story"])
            )
        if (outcome["fate"], outcome["evidence"]) != (check["fate"], check["evidence"]):
            db.execute(
                "update checks set fate = ?, evidence = ?, detail = ? where id = ?",
                (outcome["fate"], outcome["evidence"], json.dumps(outcome["detail"]), check["id"]),
            )
            changed[(check["fate"], outcome["fate"])] += 1
        before[check["story"]] = outcome["evidence"]
    db.commit()
    log.info("%d of %d checks changed: %s", sum(changed.values()), len(checks), dict(changed))


def stats(db: sqlite3.Connection):
    rows = db.execute(
        f"""with {LATEST}
            select strftime('%Y', s.posted, 'unixepoch') year, latest.fate, count(*) n
            from stories s join latest on latest.story = s.id group by 1, 2"""
    ).fetchall()
    years = defaultdict(Counter)
    for row in rows:
        years[row["year"]][row["fate"]] = row["n"]
    print("year  " + "".join(f"{fate:>10}" for fate in FATES) + "    dead%  unsure%")
    for year, fates in sorted(years.items()):
        total = sum(fates.values())
        cells = "".join(f"{fates[fate]:>10}" for fate in FATES)
        print(f"{year}  {cells}   {fates[DEAD] / total:6.1%}   {fates[UNSURE] / total:6.1%}")
