"""rollup_events builder — the S4 recent-results feed.

Denormalizes every stored event of the format (date <= as_of) with its
winning archetype: the best-finishing labeled deck (finish_rank, NULLs last,
then deck id — deterministic). Full replace each run; the feed is derived
data and cheap to rebuild.
"""

from __future__ import annotations

import datetime as dt

import psycopg

from jobs.rollups.common import SnapshotStats, resolve_format_id


def build_events(
    conn: psycopg.Connection, game_name: str, format_name: str, as_of: dt.date
) -> SnapshotStats:
    format_id = resolve_format_id(conn, game_name, format_name)
    with conn.cursor() as cur:
        cur.execute("DELETE FROM rollup_events WHERE format_id = %s", (format_id,))
        cur.execute(
            """
            INSERT INTO rollup_events (format_id, event_id, date, name, source,
                                       player_count, top_archetype_id)
            SELECT e.format_id, e.id, e.date, e.name, e.source, e.player_count,
                   (SELECT d.archetype_id FROM decks d
                     WHERE d.event_id = e.id AND d.archetype_id IS NOT NULL
                     ORDER BY d.finish_rank NULLS LAST, d.id LIMIT 1)
            FROM events e
            WHERE e.format_id = %s AND e.date <= %s
            """,
            (format_id, as_of),
        )
        written = cur.rowcount
    conn.commit()
    return SnapshotStats(format_id, as_of, written)
