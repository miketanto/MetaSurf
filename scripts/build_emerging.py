#!/usr/bin/env python3
"""Build the emerging-deck rollup for one format (plan §8 S5).

Runs the game's clustering-stage characterizer behind the EmergingBuilder
seam, so this lives outside the game-neutrality-gated packages (like serve.py):
it wires the MTG adapter and invokes the Protocol. The nightly chain calls this
after labeling, alongside ``python -m jobs.rollups`` (which builds the
game-neutral rollups but cannot cluster).

Usage:
    python -m scripts.build_emerging --game <game> --format <format> [--as-of YYYY-MM-DD]

Without --as-of, uses the latest stored event date for the format.
"""

from __future__ import annotations

import argparse
import datetime as dt

import psycopg

from api.emerging import EmergingBuilder
from archetypes.emerging_service import MtgEmergingBuilder
from db.connection import database_url

# game name -> EmergingBuilder adapter (the composition root, outside the gate)
BUILDERS: dict[str, EmergingBuilder] = {"mtg": MtgEmergingBuilder()}


def _latest_event_date(conn: psycopg.Connection, game: str, format_name: str) -> dt.date | None:
    with conn.cursor() as cur:
        cur.execute(
            "SELECT max(e.date) FROM events e"
            " JOIN formats f ON f.id = e.format_id"
            " JOIN games g ON g.id = f.game_id"
            " WHERE g.name = %s AND f.name = %s",
            (game, format_name),
        )
        row = cur.fetchone()
    return row[0] if row else None


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--game", required=True)
    parser.add_argument("--format", dest="format_name", required=True)
    parser.add_argument("--as-of", type=dt.date.fromisoformat, default=None)
    args = parser.parse_args()

    builder = BUILDERS.get(args.game)
    if builder is None:
        raise SystemExit(f"no emerging builder wired for game {args.game!r}")

    with psycopg.connect(database_url()) as conn:
        as_of = args.as_of
        if as_of is None:
            as_of = _latest_event_date(conn, args.game, args.format_name)
            if as_of is None:
                raise SystemExit("no stored events for this format; nothing to roll up")
        stats = builder.build_emerging(conn, args.game, args.format_name, as_of)
        print(f"emerging: {stats.summary()}")


if __name__ == "__main__":
    main()
