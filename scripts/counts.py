"""Prints the crawl's table counts, or with --at-least, refuses a database that's lost anything."""

import sqlite3
import sys

TABLES = ("stories", "checks", "captures", "fronts")

db = sqlite3.connect(sys.argv[1])
if len(sys.argv) > 3 and sys.argv[2] == "--at-least":
    assert db.execute("pragma wal_checkpoint(truncate)").fetchone()[0] == 0, (
        "the WAL is still busy"
    )
    assert db.execute("pragma quick_check").fetchone()[0] == "ok", (
        "the database is damaged"
    )
    before = dict(pair.split("=") for pair in sys.argv[3].split())
    for table in TABLES:
        now = db.execute(f"select count(*) from {table}").fetchone()[0]
        assert now >= int(before.get(table, 0)), (
            f"{table} went from {before[table]} to {now}"
        )
else:
    print(
        " ".join(
            f"{t}={db.execute(f'select count(*) from {t}').fetchone()[0]}"
            for t in TABLES
        )
    )
