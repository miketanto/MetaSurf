"""CLI: fetch new mtgo.com events and land them as CacheItem files.

    python -m ingest.mtgo_scraper [--cache-root DIR] [--raw-root DIR]

Scrape only (no DB). The full nightly chain (scrape -> import -> match-extract
-> label -> rollups, with alerting) is `python -m ingest.mtgo_scraper.daily`.
"""

from __future__ import annotations

import argparse
from pathlib import Path

from ingest.mtgo_scraper.daily import DEFAULT_CACHE_ROOT, DEFAULT_RAW_ROOT
from ingest.mtgo_scraper.fetch import Fetcher, RawArchive
from ingest.mtgo_scraper.scrape import run_scrape


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--game", default="mtg")
    parser.add_argument("--cache-root", type=Path, default=DEFAULT_CACHE_ROOT)
    parser.add_argument("--raw-root", type=Path, default=DEFAULT_RAW_ROOT)
    args = parser.parse_args()
    fetcher = Fetcher(RawArchive(args.raw_root))
    stats = run_scrape(fetcher, args.cache_root, game=args.game)
    print(stats.summary())


if __name__ == "__main__":
    main()
