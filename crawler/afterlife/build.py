"""Turns the crawl's SQLite state into the static files the site reads."""

import csv
import gzip
import io
import json
import logging
import shutil
import sqlite3
import zlib
from collections import Counter, defaultdict
from datetime import UTC, datetime
from pathlib import Path

from .classify import ALIVE, DEAD, ELSEWHERE, MOVED, UNSURE
from .urls import host_of

FATES = [ALIVE, MOVED, DEAD, ELSEWHERE, UNSURE]
SHARDS = 1024
log = logging.getLogger(__name__)

VERDICTS = """
with ranked as (
  select c.*, row_number() over (
    partition by c.story order by c.fate != 'unsure' desc, c.id desc) pick
  from checks c),
good as (
  select story, captured, status, row_number() over (partition by story order by at desc) pick
  from captures where kind = 'good')
select s.id, s.url, s.title, s.points, s.comments, s.posted, s.show_hn,
  v.fate, v.evidence, v.status, v.final, v.title now, v.at checked,
  g.captured, g.status captured_status
from stories s
left join ranked v on v.story = s.id and v.pick = 1
left join good g on g.story = s.id and g.pick = 1
order by s.posted, s.id
"""


def verdicts(db: sqlite3.Connection) -> list[sqlite3.Row]:
    """Each story with the verdict it shows: its newest decisive check, so an unsure re-check
    never hides the alive or dead one before it."""
    return db.execute(VERDICTS).fetchall()


def day_of(stamp: int) -> str:
    return datetime.fromtimestamp(stamp, UTC).strftime("%Y-%m-%d")


def shard(key: str | int) -> int:
    return (key if isinstance(key, int) else zlib.crc32(key.encode())) % SHARDS


def card(story: sqlite3.Row) -> dict:
    """Everything a story card shows, minus the blanks."""
    fields = dict(story)
    fields.update(
        day=day_of(story["posted"]), checked=story["checked"] and day_of(story["checked"])
    )
    del fields["posted"], fields["show_hn"]
    return {key: value for key, value in fields.items() if value is not None}


def dot(story: sqlite3.Row) -> list:
    """id, day, points, fate (an index into FATES) and title, plus the status of the last
    capture that wasn't a wall when we can't tell."""
    fate = FATES.index(story["fate"])
    extra = [story["captured_status"]] if story["fate"] == UNSURE and story["captured"] else []
    return [story["id"], day_of(story["posted"]), story["points"], fate, story["title"], *extra]


def write(out: Path, name: str, data):
    path = out / name
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, separators=(",", ":")), "utf-8")


def year_stats(linked: list[sqlite3.Row]) -> dict:
    years = defaultdict(Counter)
    for story in linked:
        years[day_of(story["posted"])[:4]][story["fate"]] += 1
    return {year: {fate: fates[fate] for fate in FATES} for year, fates in sorted(years.items())}


def graveyard(linked: list[sqlite3.Row], size: int = 500) -> dict:
    """The most-upvoted dead links, the hosts that took the most stories with them, and the
    Show HN launches that don't load any more."""
    by_host = defaultdict(Counter)
    for story in linked:
        by_host[host_of(story["url"])][story["fate"]] += 1
    hosts = [
        {
            "host": host,
            "dead": fates[DEAD],
            "elsewhere": fates[ELSEWHERE],
            "stories": sum(fates.values()),
        }
        for host, fates in by_host.items()
        if fates[DEAD] + fates[ELSEWHERE] >= 5
    ]
    upvoted = sorted(linked, key=lambda story: -story["points"])
    return {
        "upvoted": [dot(s) for s in upvoted if s["fate"] == DEAD][:size],
        "hosts": sorted(hosts, key=lambda h: -(h["dead"] + h["elsewhere"]))[:size],
        "show_hn": [dot(s) for s in upvoted if s["show_hn"] and s["fate"] in (DEAD, ELSEWHERE)][
            :size
        ],
    }


def export_csv(linked: list[sqlite3.Row]) -> bytes:
    text = io.StringIO()
    table = csv.writer(text)
    table.writerow(["hn_id", "url", "fate", "checked"])
    for story in linked:
        table.writerow([story["id"], story["url"], story["fate"], day_of(story["checked"])])
    return gzip.compress(text.getvalue().encode(), mtime=0)


def run(db: sqlite3.Connection, out: Path):
    stories = verdicts(db)
    linked = [story for story in stories if story["url"] and story["fate"]]
    shutil.rmtree(out, ignore_errors=True)
    out.mkdir(parents=True)

    groups = {key: defaultdict(list) for key in ("grid", "day", "id", "host")}
    for story in stories:
        groups["day"][day_of(story["posted"])].append(story)
    for story in linked:
        groups["grid"][day_of(story["posted"])[:4]].append(story)
        groups["id"][shard(story["id"])].append(story)
        groups["host"][shard(host_of(story["url"]))].append(story)

    for year, group in groups["grid"].items():
        write(out, f"grid/{year}.json", [dot(s) for s in group])
    for day, group in groups["day"].items():
        top = sorted(group, key=lambda s: (-s["points"], s["id"]))[:30]
        write(out, f"day/{day}.json", [card(s) for s in top])
    for number, group in groups["id"].items():
        write(out, f"id/{number}.json", {s["id"]: card(s) for s in group})
    for number, group in groups["host"].items():
        hosts = defaultdict(list)
        for story in group:
            hosts[host_of(story["url"])].append(dot(story))
        write(out, f"host/{number}.json", hosts)

    checked = max((story["checked"] for story in linked), default=0)
    write(out, "stats.json", {"years": year_stats(linked), "checked": day_of(checked)})
    write(out, "graveyard.json", graveyard(linked))
    (out / "afterlife.csv.gz").write_bytes(export_csv(linked))
    files = sum(1 for path in out.rglob("*") if path.is_file())
    log.info("built %d files from %d stories, %d with a verdict", files, len(stories), len(linked))
