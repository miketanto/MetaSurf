"""Shared plumbing for the rollup jobs.

Definitions are lifted from the validated suites, not re-invented:

- Weeks are Sat..Fri buckets keyed by their Saturday (the V3 panel
  convention; see validation/v3_evolution/data.py).
- "Share" pools labeled weekend decks over the trailing
  ``UNIVERSE_TRAILING_WEEKS`` buckets ending at ``as_of``.
- The "universe" — the archetypes a metagame page lists, and the matchup
  matrix axes — is the pooled-share >= ``UNIVERSE_MIN_SHARE`` rule from the
  V3/V-REC walk-forwards (imported from there so the product and the
  validation stay on one definition).

``as_of`` semantics: a snapshot describes all data with event date
<= ``as_of``; the winrate model fits strictly-before, so its cutoff is
``as_of + 1`` day. Callers pass ``as_of`` explicitly (on the frozen corpus,
"current" = the latest stored event date); nothing here reads the wall clock.
"""

from __future__ import annotations

import datetime as dt
from dataclasses import dataclass

import psycopg

from validation.v3_evolution.walkforward import (
    UNIVERSE_MIN_SHARE,
    UNIVERSE_TRAILING_WEEKS,
)

__all__ = [
    "UNIVERSE_MIN_SHARE",
    "UNIVERSE_TRAILING_WEEKS",
    "SnapshotStats",
    "fit_cutoff_day",
    "resolve_format_id",
    "trailing_window_start",
    "universe_ids",
    "week_saturday",
    "weekend_archetype_counts",
]

CI_LEVEL = 0.90


@dataclass(frozen=True)
class SnapshotStats:
    format_id: int
    as_of: dt.date
    rows_written: int

    def summary(self) -> str:
        return f"format {self.format_id} as_of {self.as_of}: {self.rows_written} rows"


def resolve_format_id(conn: psycopg.Connection, game_name: str, format_name: str) -> int:
    with conn.cursor() as cur:
        cur.execute(
            "SELECT f.id FROM formats f JOIN games g ON g.id = f.game_id"
            " WHERE g.name = %s AND f.name = %s",
            (game_name, format_name),
        )
        row = cur.fetchone()
    if row is None:
        raise LookupError(f"unknown game/format: {game_name}/{format_name}")
    return int(row[0])


def week_saturday(d: dt.date) -> dt.date:
    """The Saturday keying ``d``'s Sat..Fri bucket."""
    return d - dt.timedelta(days=(d.isoweekday() + 1) % 7)


def trailing_window_start(as_of: dt.date) -> dt.date:
    """First Saturday of the pooled trailing share window ending at as_of."""
    return week_saturday(as_of) - dt.timedelta(weeks=UNIVERSE_TRAILING_WEEKS - 1)


def fit_cutoff_day(as_of: dt.date) -> int:
    """Winrate-model cutoff including matches played on as_of itself."""
    return as_of.toordinal() + 1


def weekend_archetype_counts(
    conn: psycopg.Connection,
    format_id: int,
    first: dt.date,
    last: dt.date,
    format_name: str,
) -> dict[int, int]:
    """Labeled weekend decks per archetype, event date in [first, last], that
    are still LEGAL in the format now — a deck is excluded iff it holds a card
    explicitly ``banned`` or ``not_legal`` for the format (per the ingested
    Scryfall legalities). This keeps the served 'current' meta free of rotated
    or banned-card decks; historical decks stay in the DB for backtesting.
    Cards with unknown/missing legality never exclude (benefit of the doubt).
    """
    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT d.archetype_id, count(*)
            FROM decks d
            JOIN events e ON e.id = d.event_id
            WHERE e.format_id = %s
              AND d.archetype_id IS NOT NULL
              AND extract(isodow FROM e.date) IN (6, 7)
              AND e.date BETWEEN %s AND %s
              AND NOT EXISTS (
                SELECT 1 FROM deck_cards dc
                JOIN cards c ON c.id = dc.card_id
                WHERE dc.deck_id = d.id
                  AND c.attrs->'legalities'->>%s IN ('banned', 'not_legal')
              )
            GROUP BY 1 ORDER BY 1
            """,
            (format_id, first, last, format_name),
        )
        return {int(a): int(n) for a, n in cur.fetchall()}


def universe_ids(counts: dict[int, int]) -> list[int]:
    """Archetype ids holding >= UNIVERSE_MIN_SHARE of the pooled counts."""
    total = sum(counts.values())
    if total == 0:
        return []
    return sorted(a for a, n in counts.items() if n / total >= UNIVERSE_MIN_SHARE)
