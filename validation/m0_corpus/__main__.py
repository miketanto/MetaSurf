"""CLI: python -m validation.m0_corpus --out validation/reports/m0-data-quality.md"""

from __future__ import annotations

import argparse
import datetime
from pathlib import Path

from db.connection import connect
from validation.m0_corpus.report import generate_report


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate the M0 data-quality report")
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument(
        "--date",
        default=datetime.date.today().isoformat(),
        help="date stamp for the report title (default: today)",
    )
    args = parser.parse_args()
    with connect() as conn:
        report = generate_report(conn, args.date)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(report)
    print(f"wrote {args.out}")


if __name__ == "__main__":
    main()
