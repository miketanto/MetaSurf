"""CLI: python -m ingest.cardsem [--out validation/reports/cardsem-coverage.md]

Measures CardGuru feature coverage over MetaSurf's card universe and decklist
corpus. Runs from the committed snapshots — no database, no network.
"""

from __future__ import annotations

import argparse
from datetime import date
from pathlib import Path

from ingest.cardsem.coverage import (
    DEFAULT_CORPUS,
    DEFAULT_FEATURES,
    DEFAULT_SCRYFALL,
    build_report,
    read_corpus_usage,
    render,
    scryfall_identities,
)
from ingest.cardsem.loader import load_feature_table


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--features", type=Path, default=DEFAULT_FEATURES)
    parser.add_argument("--scryfall", type=Path, default=DEFAULT_SCRYFALL)
    parser.add_argument("--corpus", type=Path, default=DEFAULT_CORPUS)
    parser.add_argument("--out", type=Path, default=None)
    parser.add_argument(
        "--today",
        default=date.today().isoformat(),
        help="date stamp for the report header (explicit for reproducibility)",
    )
    args = parser.parse_args()

    table = load_feature_table(args.features)
    identities = scryfall_identities(args.scryfall)
    corpus = read_corpus_usage(args.corpus)
    report = build_report(table, identities, corpus)
    text = render(report, today=args.today)

    if args.out:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(text, encoding="utf-8")
        print(f"wrote {args.out}")
    print(text)


if __name__ == "__main__":
    main()
