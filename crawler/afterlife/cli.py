import argparse
import asyncio
import logging

from . import crawl, hn
from .db import connect


def main():
    parser = argparse.ArgumentParser(prog="afterlife", description=__doc__)
    parser.add_argument("--db", default="data/afterlife.db", help="SQLite file to keep state in")
    commands = parser.add_subparsers(dest="command", required=True)
    commands.add_parser("stories", help="fetch every 100+ point story and each day's top 30")
    check = commands.add_parser("crawl", help="check unchecked stories and due re-checks")
    check.add_argument("--workers", type=int, default=64, help="sites to crawl at once")
    check.add_argument("--limit", type=int, help="stop after this many stories")
    commands.add_parser("run", help="stories, then crawl")
    commands.add_parser("stats", help="fates by year, as things stand")
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    db = connect(args.db)
    if args.command in ("stories", "run"):
        asyncio.run(hn.fetch(db))
    if args.command in ("crawl", "run"):
        asyncio.run(crawl.run(db, getattr(args, "workers", 64), getattr(args, "limit", None)))
    if args.command == "stats":
        crawl.stats(db)
