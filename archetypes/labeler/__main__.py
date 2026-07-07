"""CLI: python -m archetypes.labeler [--format modern]"""

from __future__ import annotations

import argparse

import psycopg

from archetypes.labeler import label_corpus
from db.connection import database_url


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--format", default="modern", dest="format_name")
    args = parser.parse_args()
    with psycopg.connect(database_url()) as conn:
        stats = label_corpus(conn, args.format_name)
    print(stats.summary())


if __name__ == "__main__":
    main()
