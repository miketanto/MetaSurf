"""DB -> MatchData loader for the V2 winrate suites.

Bridges the canonical schema (matches + decks.archetype_id) to the
game-neutral model input. Deterministic: rows ordered by match id.

Outcome encoding (observed result grammar: always ``W-L-D`` from deck_id_a's
perspective, game counts on mtgo/melee/manatraders, match-level on topdeck —
see the Rounds/Matches deep-dive note): W>L -> side-a match win (1.0),
W<L -> loss (0.0), W==L -> drawn match (0.5, split evidence).

Matches whose side-a deck has no archetype label (card-less decks) are
flipped to the labeled side when possible, otherwise dropped and counted —
the model requires side_a resolved.
"""

from __future__ import annotations

import datetime as dt
from dataclasses import dataclass

import numpy as np
import psycopg

from models.winrate import UNKNOWN, MatchData


@dataclass
class LoadStats:
    matches_loaded: int = 0
    flipped_unlabeled_a: int = 0
    dropped_both_unlabeled: int = 0
    opponent_unknown: int = 0  # deck_id_b null or unlabeled
    draws: int = 0

    def summary(self) -> str:
        return (
            f"matches loaded: {self.matches_loaded}"
            f" (flipped: {self.flipped_unlabeled_a},"
            f" dropped both-unlabeled: {self.dropped_both_unlabeled},"
            f" opponent unknown: {self.opponent_unknown}, draws: {self.draws})"
        )


def load_match_data(
    conn: psycopg.Connection, format_name: str
) -> tuple[MatchData, dict[int, str], LoadStats]:
    """All stored matches of the format as MatchData columns.

    Returns (data, archetype_id -> name for every id that can occur, stats).
    Archetype ids are used directly as the model's dense indexes.
    """
    stats = LoadStats()
    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT a.id, a.name FROM archetypes a
            JOIN formats f ON f.id = a.format_id
            WHERE f.name = %s ORDER BY a.id
            """,
            (format_name,),
        )
        names: dict[int, str] = dict(cur.fetchall())
        cur.execute(
            """
            SELECT e.date, da.archetype_id, db.archetype_id,
                   split_part(m.result, '-', 1)::int,
                   split_part(m.result, '-', 2)::int
            FROM matches m
            JOIN events e ON e.id = m.event_id
            JOIN formats f ON f.id = e.format_id AND f.name = %s
            JOIN decks da ON da.id = m.deck_id_a
            LEFT JOIN decks db ON db.id = m.deck_id_b
            ORDER BY m.id
            """,
            (format_name,),
        )
        day: list[int] = []
        side_a: list[int] = []
        side_b: list[int] = []
        win_frac: list[float] = []
        for date, arch_a, arch_b, w, lo in cur:
            frac = 1.0 if w > lo else (0.0 if w < lo else 0.5)
            if arch_a is None:
                if arch_b is None:
                    stats.dropped_both_unlabeled += 1
                    continue
                arch_a, arch_b = arch_b, None
                frac = 1.0 - frac
                stats.flipped_unlabeled_a += 1
            if arch_b is None:
                stats.opponent_unknown += 1
            if frac == 0.5:
                stats.draws += 1
            day.append(_to_day(date))
            side_a.append(arch_a)
            side_b.append(arch_b if arch_b is not None else UNKNOWN)
            win_frac.append(frac)
    stats.matches_loaded = len(day)
    data = MatchData(
        day=np.asarray(day, dtype=np.int64),
        side_a=np.asarray(side_a, dtype=np.int64),
        side_b=np.asarray(side_b, dtype=np.int64),
        win_frac=np.asarray(win_frac, dtype=np.float64),
    )
    return data, names, stats


def _to_day(date: dt.date) -> int:
    return date.toordinal()


def n_archetype_slots(names: dict[int, str]) -> int:
    """Dense array size for archetype-indexed model arrays."""
    return (max(names) + 1) if names else 1
