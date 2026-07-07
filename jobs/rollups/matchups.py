"""rollup_matchups builder — the S2 matchup-matrix table.

One row per ordered pair over the snapshot's universe (trailing pooled share
>= the validated threshold): ``p_a_beats_b`` and its ``CI_LEVEL`` credible
interval from the Layer-2 pair posterior, plus ``n_matches`` — the raw
(undecayed) count of stored matches between the pair with event date
<= ``as_of``, both orientations, the honest sample size behind the cell.
Mirror cells are exactly 0.5 by model construction.
"""

from __future__ import annotations

import datetime as dt

import numpy as np
import psycopg

from jobs.rollups.common import (
    CI_LEVEL,
    SnapshotStats,
    fit_cutoff_day,
    resolve_format_id,
    trailing_window_start,
    universe_ids,
    weekend_archetype_counts,
)
from models.winrate import WinrateModel
from validation.v2_winrates.data import load_match_data, n_archetype_slots


def _pair_match_counts(
    conn: psycopg.Connection, format_id: int, as_of: dt.date
) -> dict[tuple[int, int], int]:
    """Stored both-labeled matches per ordered archetype pair, date <= as_of."""
    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT da.archetype_id, db.archetype_id, count(*)
            FROM matches m
            JOIN events e ON e.id = m.event_id
             AND e.format_id = %s AND e.date <= %s
            JOIN decks da ON da.id = m.deck_id_a
            JOIN decks db ON db.id = m.deck_id_b
            WHERE da.archetype_id IS NOT NULL AND db.archetype_id IS NOT NULL
            GROUP BY 1, 2
            """,
            (format_id, as_of),
        )
        return {(int(a), int(b)): int(c) for a, b, c in cur.fetchall()}


def build_matchups(
    conn: psycopg.Connection, game_name: str, format_name: str, as_of: dt.date
) -> SnapshotStats:
    format_id = resolve_format_id(conn, game_name, format_name)
    counts = weekend_archetype_counts(conn, format_id, trailing_window_start(as_of), as_of)
    universe = universe_ids(counts)

    rows: list[tuple[int, dt.date, int, int, float, float, float, int]] = []
    if universe:
        data, names, _stats = load_match_data(conn, format_name)
        post = WinrateModel().fit(data, fit_cutoff_day(as_of), n_archetype_slots(names))
        ids = np.asarray(universe, dtype=np.int64)
        k = len(ids)
        ai = np.repeat(ids, k)
        bi = np.tile(ids, k)
        p = post.match_prob(ai, bi)
        lo, hi = post.matchup_interval(ai, bi, CI_LEVEL)
        stored = _pair_match_counts(conn, format_id, as_of)
        for i in range(k * k):
            a, b = int(ai[i]), int(bi[i])
            n = stored.get((a, b), 0) + (stored.get((b, a), 0) if a != b else 0)
            rows.append((format_id, as_of, a, b, float(p[i]), float(lo[i]), float(hi[i]), n))

    with conn.cursor() as cur:
        cur.execute(
            "DELETE FROM rollup_matchups WHERE format_id = %s AND as_of = %s",
            (format_id, as_of),
        )
        cur.executemany(
            "INSERT INTO rollup_matchups (format_id, as_of, arch_a, arch_b, p_a_beats_b,"
            " ci_lo, ci_hi, n_matches) VALUES (%s, %s, %s, %s, %s, %s, %s, %s)",
            rows,
        )
    conn.commit()
    return SnapshotStats(format_id, as_of, len(rows))
