import argparse
import asyncio
import fcntl
import logging
from pathlib import Path

from . import build, crawl, fronts, hn, wayback
from .db import connect


def main():
    parser = argparse.ArgumentParser(prog="afterlife", description=__doc__)
    parser.add_argument("--db", default="data/afterlife.db", help="SQLite file to keep state in")
    commands = parser.add_subparsers(dest="command", required=True)
    commands.add_parser("stories", help="fetch every 100+ point story and each day's top 30")
    check = commands.add_parser("crawl", help="check unchecked stories and due re-checks")
    check.add_argument("--workers", type=int, default=64, help="sites to crawl at once")
    check.add_argument("--limit", type=int, help="stop after this many stories")
    check.add_argument(
        "--recheck", action="store_true", help="also re-check this week's 52nd of the stories"
    )
    archive = commands.add_parser(
        "wayback", help="compare home pages and find walled links' captures"
    )
    archive.add_argument("--limit", type=int, help="stop after this many of each")
    commands.add_parser(
        "fronts", help="HN's own front pages for the coming week, 5, 10 and 15 years back"
    )
    commands.add_parser("run", help="stories, crawl, then the Wayback pass")
    commands.add_parser("stats", help="fates by year, as things stand")
    commands.add_parser("reclassify", help="re-run the classifier over every stored check")
    site = commands.add_parser("build", help="write the static files the site reads")
    site.add_argument("--out", type=Path, default=Path("static/data"), help="where they go")
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    db = connect(args.db)
    lock = open(f"{args.db}.lock", "w")  # noqa: SIM115 - held until we exit
    if args.command not in ("stats", "build"):
        try:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            parser.exit(1, f"Something else is already crawling into {args.db}\n")
    if args.command in ("stories", "run"):
        asyncio.run(hn.fetch(db))
    if args.command in ("crawl", "run"):
        asyncio.run(
            crawl.run(
                db,
                getattr(args, "workers", 64),
                getattr(args, "limit", None),
                getattr(args, "recheck", False),
            )
        )
    if args.command in ("wayback", "run"):
        asyncio.run(wayback.run(db, getattr(args, "limit", None)))
    if args.command == "fronts":
        asyncio.run(fronts.run(db))
    if args.command == "stats":
        crawl.stats(db)
    if args.command == "reclassify":
        crawl.reclassify(db)
    if args.command == "build":
        build.run(db, args.out)
