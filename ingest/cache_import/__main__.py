"""CLI: python -m ingest.cache_import --cache data/MTGODecklistCache"""

from __future__ import annotations

import argparse
from pathlib import Path

from db.connection import connect
from ingest.cache_import.importer import run_import


def main() -> None:
    parser = argparse.ArgumentParser(description="Import MTGODecklistCache into Postgres")
    parser.add_argument("--cache", type=Path, default=Path("data/MTGODecklistCache"))
    parser.add_argument("--game", default="mtg")
    parser.add_argument(
        "--format",
        action="append",
        dest="formats",
        help="restrict to specific format(s); default = all import-enabled formats",
    )
    args = parser.parse_args()
    with connect() as conn:
        stats = run_import(
            conn,
            args.cache,
            game=args.game,
            only_formats=set(args.formats) if args.formats else None,
        )
    print(stats.summary())


if __name__ == "__main__":
    main()
