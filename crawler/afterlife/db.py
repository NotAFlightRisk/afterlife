import json
import sqlite3
from pathlib import Path

SCHEMA = """
create table if not exists stories (
  id integer primary key,
  url text,
  title text not null,
  points integer not null,
  comments integer not null,
  posted integer not null,
  show_hn integer not null
);
create index if not exists stories_posted on stories(posted);
create table if not exists fetched (start integer primary key, stop integer not null);
create table if not exists checks (
  id integer primary key,
  story integer not null references stories(id),
  at integer not null,
  fate text not null,
  evidence text not null,
  status integer,
  final text,
  title text,
  detail text
);
create index if not exists checks_story on checks(story, at);
create table if not exists captures (
  story integer not null references stories(id),
  at integer not null,
  kind text not null,
  captured text,
  status integer,
  title text
);
create index if not exists captures_story on captures(story, kind);
"""


def connect(path: str | Path) -> sqlite3.Connection:
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    db = sqlite3.connect(path, timeout=60)
    db.row_factory = sqlite3.Row
    db.execute("pragma journal_mode = wal")
    db.execute("pragma synchronous = normal")
    db.executescript(SCHEMA)
    return db


def save_stories(db: sqlite3.Connection, hits: list[dict]):
    db.executemany(
        """insert into stories values (:id, :url, :title, :points, :comments, :posted, :show_hn)
           on conflict(id) do update set url = excluded.url, title = excluded.title,
             points = excluded.points, comments = excluded.comments""",
        hits,
    )


def save_check(db: sqlite3.Connection, story: int, at: int, result: dict):
    detail = result.get("detail")
    db.execute(
        """insert into checks (story, at, fate, evidence, status, final, title, detail)
           values (?, ?, ?, ?, ?, ?, ?, ?)""",
        (
            story,
            at,
            result["fate"],
            result["evidence"],
            result.get("status"),
            result.get("final"),
            result.get("title"),
            json.dumps(detail) if detail else None,
        ),
    )


LATEST = """latest as (
  select c.* from checks c
  join (select story, max(id) id from checks group by story) newest on newest.id = c.id)"""
