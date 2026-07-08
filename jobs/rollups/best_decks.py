"""rollup_best_decks builder — the ranked "best decks this weekend" list.

Exactly the V-REC MODEL strategy (validated: 0.564 pooled realized winrate):
rank the universe by expected winrate against the current field,
``score_a = sum_b P(a beats b) * share_b``, where the field is the most
recent non-empty weekend bucket at ``as_of`` (normalized over the universe)
and P comes from the Layer-2 posterior as of ``as_of``. Ties break to the
lowest archetype id via the model's stable sort.
"""

from __future__ import annotations

import datetime as dt

import numpy as np
import psycopg

from jobs.rollups.common import (
    SnapshotStats,
    fit_cutoff_day,
    resolve_format_id,
    trailing_window_start,
    universe_ids,
    week_saturday,
    weekend_archetype_counts,
)
from models.recommender import field_response_scores, rank_by_best_response
from models.winrate import WinrateModel
from validation.v2_winrates.data import load_match_data, n_archetype_slots


def _latest_weekend_field(
    conn: psycopg.Connection,
    format_id: int,
    as_of: dt.date,
    universe: list[int],
    format_name: str,
) -> np.ndarray | None:
    """Universe shares of the most recent weekend bucket with any labeled
    decks, walking back within the trailing window; None if all are empty."""
    sat = week_saturday(as_of)
    first = trailing_window_start(as_of)
    while sat >= first:
        bucket = weekend_archetype_counts(
            conn, format_id, sat, min(as_of, sat + dt.timedelta(days=1)), format_name
        )
        vec = np.array([bucket.get(a, 0) for a in universe], dtype=np.float64)
        if vec.sum() > 0:
            return vec / vec.sum()
        sat -= dt.timedelta(days=7)
    return None


def build_best_decks(
    conn: psycopg.Connection, game_name: str, format_name: str, as_of: dt.date
) -> SnapshotStats:
    format_id = resolve_format_id(conn, game_name, format_name)
    counts = weekend_archetype_counts(
        conn, format_id, trailing_window_start(as_of), as_of, format_name
    )
    universe = universe_ids(counts)

    rows: list[tuple[int, dt.date, int, int, float]] = []
    if universe:
        field = _latest_weekend_field(conn, format_id, as_of, universe, format_name)
        if field is not None:
            data, names, _stats = load_match_data(conn, format_name)
            post = WinrateModel().fit(data, fit_cutoff_day(as_of), n_archetype_slots(names))
            ids = np.asarray(universe, dtype=np.int64)
            k = len(ids)
            payoff = post.match_prob(np.repeat(ids, k), np.tile(ids, k)).reshape(k, k)
            scores = field_response_scores(field, payoff)
            for rank, idx in enumerate(rank_by_best_response(field, payoff), start=1):
                rows.append((format_id, as_of, rank, int(ids[idx]), float(scores[idx])))

    with conn.cursor() as cur:
        cur.execute(
            "DELETE FROM rollup_best_decks WHERE format_id = %s AND as_of = %s",
            (format_id, as_of),
        )
        cur.executemany(
            "INSERT INTO rollup_best_decks (format_id, as_of, rank, archetype_id,"
            " exp_winrate_vs_field) VALUES (%s, %s, %s, %s, %s)",
            rows,
        )
    conn.commit()
    return SnapshotStats(format_id, as_of, len(rows))
