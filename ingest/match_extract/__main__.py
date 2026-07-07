"""CLI: python -m ingest.match_extract --cache data/MTGODecklistCache"""

from __future__ import annotations

import argparse
from pathlib import Path

import psycopg

from db.connection import database_url
from ingest.match_extract.extractor import extract_matches


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--cache", type=Path, required=True, help="MTGODecklistCache clone root")
    args = parser.parse_args()
    with psycopg.connect(database_url()) as conn:
        stats = extract_matches(conn, args.cache)
    print(stats.summary())


if __name__ == "__main__":
    main()
