"""rollup_archetype_ts builder — weekly share/winrate history (S1 sparkline,
S3 premium series).

One row per (archetype, Sat-keyed week) where the archetype had labeled
weekend decks: its share of that week's labeled weekend decks, and the
Layer-2 posterior winrate (with credible interval) fitted at the end of that
week's bucket (capped at ``as_of``), i.e. the model state after that
weekend's evidence. A missing (archetype, week) row means share 0 that week;
the API densifies at read time. Full-history rebuild each run: the table is
derived data, and relabeling can rewrite any part of the past.
"""

from __future__ import annotations

import datetime as dt

import psycopg

from jobs.rollups.common import (
    CI_LEVEL,
    SnapshotStats,
    fit_cutoff_day,
    resolve_format_id,
)
from models.winrate import WinrateModel
from validation.v2_winrates.data import load_match_data, n_archetype_slots


def _weekly_counts(
    conn: psycopg.Connection, format_id: int, as_of: dt.date
) -> dict[dt.date, dict[int, int]]:
    """Labeled weekend decks per (Sat-keyed week, archetype), date <= as_of."""
    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT date_trunc('week', e.date - 5)::date + 5 AS sat,
                   d.archetype_id, count(*)
            FROM decks d
            JOIN events e ON e.id = d.event_id
            WHERE e.format_id = %s
              AND d.archetype_id IS NOT NULL
              AND extract(isodow FROM e.date) IN (6, 7)
              AND e.date <= %s
            GROUP BY 1, 2 ORDER BY 1, 2
            """,
            (format_id, as_of),
        )
        weeks: dict[dt.date, dict[int, int]] = {}
        for sat, arch, n in cur.fetchall():
            weeks.setdefault(sat, {})[int(arch)] = int(n)
    return weeks


def build_archetype_ts(
    conn: psycopg.Connection, game_name: str, format_name: str, as_of: dt.date
) -> SnapshotStats:
    format_id = resolve_format_id(conn, game_name, format_name)
    weeks = _weekly_counts(conn, format_id, as_of)

    rows: list[tuple[int, int, dt.date, float, float, float, float, int]] = []
    if weeks:
        data, names, _stats = load_match_data(conn, format_name)
        slots = n_archetype_slots(names)
        model = WinrateModel()
        for sat in sorted(weeks):
            counts = weeks[sat]
            total = sum(counts.values())
            # end of this week's bucket, never beyond the as_of horizon
            cutoff = min((sat + dt.timedelta(days=7)).toordinal(), fit_cutoff_day(as_of))
            post = model.fit(data, cutoff, slots)
            mean = post.archetype_mean()
            lo, hi = post.archetype_interval(CI_LEVEL)
            for arch in sorted(counts):
                n = counts[arch]
                rows.append(
                    (
                        format_id,
                        arch,
                        sat,
                        n / total,
                        float(mean[arch]),
                        float(lo[arch]),
                        float(hi[arch]),
                        n,
                    )
                )

    with conn.cursor() as cur:
        cur.execute("DELETE FROM rollup_archetype_ts WHERE format_id = %s", (format_id,))
        cur.executemany(
            "INSERT INTO rollup_archetype_ts (format_id, archetype_id, week, share,"
            " winrate, wr_ci_lo, wr_ci_hi, n_decks) VALUES (%s, %s, %s, %s, %s, %s, %s, %s)",
            rows,
        )
    conn.commit()
    return SnapshotStats(format_id, as_of, len(rows))
