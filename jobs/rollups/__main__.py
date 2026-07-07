"""Nightly rollup entrypoint: rebuild every rollup table for one format.

Usage:
    python -m jobs.rollups --game <game> --format <format> [--as-of YYYY-MM-DD]

Without --as-of, uses the latest stored event date for the format (frozen
corpus: the snapshot of everything we have; live: last night's data).
"""

from __future__ import annotations

import argparse
import datetime as dt

import psycopg

from db.connection import database_url
from jobs.rollups import (
    build_archetype_ts,
    build_best_decks,
    build_events,
    build_matchups,
    build_meta,
)
from jobs.rollups.common import resolve_format_id

JOBS = {
    "meta": build_meta,
    "matchups": build_matchups,
    "best_decks": build_best_decks,
    "archetype_ts": build_archetype_ts,
    "events": build_events,
}


def latest_event_date(conn: psycopg.Connection, format_id: int) -> dt.date | None:
    with conn.cursor() as cur:
        cur.execute("SELECT max(date) FROM events WHERE format_id = %s", (format_id,))
        row = cur.fetchone()
    return row[0] if row else None


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--game", required=True)
    parser.add_argument("--format", dest="format_name", required=True)
    parser.add_argument("--as-of", type=dt.date.fromisoformat, default=None)
    parser.add_argument(
        "--only",
        choices=sorted(JOBS),
        nargs="*",
        default=None,
        help="run a subset of jobs (default: all)",
    )
    args = parser.parse_args()

    with psycopg.connect(database_url()) as conn:
        as_of = args.as_of
        if as_of is None:
            format_id = resolve_format_id(conn, args.game, args.format_name)
            as_of = latest_event_date(conn, format_id)
            if as_of is None:
                raise SystemExit("no stored events for this format; nothing to roll up")
        for name in args.only if args.only is not None else sorted(JOBS):
            stats = JOBS[name](conn, args.game, args.format_name, as_of)
            print(f"{name}: {stats.summary()}")


if __name__ == "__main__":
    main()
