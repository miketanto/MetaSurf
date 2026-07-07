"""CLI: python -m ingest.scryfall --file data/scryfall/oracle-cards.jsonl"""

from __future__ import annotations

import argparse
from pathlib import Path

from db.connection import connect
from ingest.scryfall import ScryfallStats, load_cards, parse_cards


def main() -> None:
    parser = argparse.ArgumentParser(description="Ingest Scryfall bulk data into cards")
    parser.add_argument("--file", type=Path, required=True)
    parser.add_argument("--game", default="mtg")
    args = parser.parse_args()
    stats = ScryfallStats()
    rows = parse_cards(args.file, stats)
    with connect() as conn:
        load_cards(conn, rows, game=args.game)
    print(stats.summary())


if __name__ == "__main__":
    main()
