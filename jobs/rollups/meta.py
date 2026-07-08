"""rollup_meta builder — the S1 meta-snapshot table.

Per archetype with at least one labeled weekend deck in the trailing window:
``share`` (fraction of those decks), ``winrate`` with a ``CI_LEVEL`` central
credible interval (Layer-2 posterior as of ``as_of``), and ``n_decks`` (the
raw count behind the share). Re-running for the same (format, as_of) replaces
exactly that snapshot.
"""

from __future__ import annotations

import datetime as dt

import psycopg

from jobs.rollups.common import (
    CI_LEVEL,
    SnapshotStats,
    fit_cutoff_day,
    resolve_format_id,
    trailing_window_start,
    weekend_archetype_counts,
)
from models.winrate import WinrateModel
from validation.v2_winrates.data import load_match_data, n_archetype_slots


def build_meta(
    conn: psycopg.Connection, game_name: str, format_name: str, as_of: dt.date
) -> SnapshotStats:
    format_id = resolve_format_id(conn, game_name, format_name)
    counts = weekend_archetype_counts(
        conn, format_id, trailing_window_start(as_of), as_of, format_name
    )
    total = sum(counts.values())

    rows: list[tuple[int, dt.date, int, float, float, float, float, int]] = []
    if total:
        data, names, _stats = load_match_data(conn, format_name)
        post = WinrateModel().fit(data, fit_cutoff_day(as_of), n_archetype_slots(names))
        mean = post.archetype_mean()
        lo, hi = post.archetype_interval(CI_LEVEL)
        for arch in sorted(counts):
            n = counts[arch]
            rows.append(
                (
                    format_id,
                    as_of,
                    arch,
                    n / total,
                    float(mean[arch]),
                    float(lo[arch]),
                    float(hi[arch]),
                    n,
                )
            )

    with conn.cursor() as cur:
        cur.execute(
            "DELETE FROM rollup_meta WHERE format_id = %s AND as_of = %s", (format_id, as_of)
        )
        cur.executemany(
            "INSERT INTO rollup_meta (format_id, as_of, archetype_id, share, winrate,"
            " wr_ci_lo, wr_ci_hi, n_decks) VALUES (%s, %s, %s, %s, %s, %s, %s, %s)",
            rows,
        )
    conn.commit()
    return SnapshotStats(format_id, as_of, len(rows))
