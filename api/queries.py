"""Rollup + reference reads backing the endpoints.

The API reads ``rollup_*`` tables plus the reference tables needed to
resolve names and ids (games, formats, archetypes) — never fact tables
(decks, matches, deck_cards) and never a model at request time (plan §4:
the app reads only precomputed rollups).
"""

from __future__ import annotations

import datetime as dt

import psycopg

# snapshot-keyed tables whose "current" as_of is queried by name
_SNAPSHOT_TABLES = frozenset({"rollup_meta", "rollup_matchups", "rollup_best_decks"})


def resolve_format_id(conn: psycopg.Connection, game_name: str, format_name: str) -> int | None:
    with conn.cursor() as cur:
        cur.execute(
            "SELECT f.id FROM formats f JOIN games g ON g.id = f.game_id"
            " WHERE g.name = %s AND f.name = %s",
            (game_name, format_name),
        )
        row = cur.fetchone()
    return int(row[0]) if row else None


def latest_snapshot(conn: psycopg.Connection, table: str, format_id: int) -> dt.date | None:
    if table not in _SNAPSHOT_TABLES:
        raise ValueError(f"not a snapshot table: {table}")
    with conn.cursor() as cur:
        cur.execute(
            f"SELECT max(as_of) FROM {table} WHERE format_id = %s",
            (format_id,),
        )
        row = cur.fetchone()
    return row[0] if row else None


def archetype_names(conn: psycopg.Connection, format_id: int) -> dict[int, str]:
    with conn.cursor() as cur:
        cur.execute("SELECT id, name FROM archetypes WHERE format_id = %s", (format_id,))
        return {int(a): str(n) for a, n in cur.fetchall()}


def archetype_id_by_name(
    conn: psycopg.Connection, format_id: int, name: str
) -> int | None:
    with conn.cursor() as cur:
        cur.execute(
            "SELECT id FROM archetypes WHERE format_id = %s AND name = %s", (format_id, name)
        )
        row = cur.fetchone()
    return int(row[0]) if row else None


def meta_rows(conn: psycopg.Connection, format_id: int, as_of: dt.date) -> list[tuple]:
    with conn.cursor() as cur:
        cur.execute(
            "SELECT archetype_id, share, winrate, wr_ci_lo, wr_ci_hi, n_decks"
            " FROM rollup_meta WHERE format_id = %s AND as_of = %s"
            " ORDER BY share DESC, archetype_id",
            (format_id, as_of),
        )
        return cur.fetchall()


def week_grid(
    conn: psycopg.Connection, format_id: int, first: dt.date, last: dt.date
) -> list[dt.date]:
    """Distinct data weeks of the format in (first, last], oldest first."""
    with conn.cursor() as cur:
        cur.execute(
            "SELECT DISTINCT week FROM rollup_archetype_ts"
            " WHERE format_id = %s AND week > %s AND week <= %s ORDER BY week",
            (format_id, first, last),
        )
        return [row[0] for row in cur.fetchall()]


def weekly_shares(
    conn: psycopg.Connection, format_id: int, first: dt.date, last: dt.date
) -> dict[int, dict[dt.date, float]]:
    """archetype -> {week -> share} over (first, last]; missing weeks mean 0."""
    with conn.cursor() as cur:
        cur.execute(
            "SELECT archetype_id, week, share FROM rollup_archetype_ts"
            " WHERE format_id = %s AND week > %s AND week <= %s",
            (format_id, first, last),
        )
        out: dict[int, dict[dt.date, float]] = {}
        for arch, week, share in cur.fetchall():
            out.setdefault(int(arch), {})[week] = float(share)
    return out


def series_rows(
    conn: psycopg.Connection, format_id: int, archetype_id: int, first: dt.date, last: dt.date
) -> dict[dt.date, tuple]:
    """week -> (share, winrate, wr_ci_lo, wr_ci_hi, n_decks) for one archetype."""
    with conn.cursor() as cur:
        cur.execute(
            "SELECT week, share, winrate, wr_ci_lo, wr_ci_hi, n_decks"
            " FROM rollup_archetype_ts"
            " WHERE format_id = %s AND archetype_id = %s AND week > %s AND week <= %s",
            (format_id, archetype_id, first, last),
        )
        return {row[0]: row[1:] for row in cur.fetchall()}


def matchup_rows(conn: psycopg.Connection, format_id: int, as_of: dt.date) -> list[tuple]:
    with conn.cursor() as cur:
        cur.execute(
            "SELECT arch_a, arch_b, p_a_beats_b, ci_lo, ci_hi, n_matches"
            " FROM rollup_matchups WHERE format_id = %s AND as_of = %s"
            " ORDER BY arch_a, arch_b",
            (format_id, as_of),
        )
        return cur.fetchall()


def matchup_cell_history(
    conn: psycopg.Connection, format_id: int, arch_a: int, arch_b: int, until: dt.date
) -> list[tuple]:
    """The (a, b) cell across snapshots up to ``until``, oldest first."""
    with conn.cursor() as cur:
        cur.execute(
            "SELECT as_of, p_a_beats_b, ci_lo, ci_hi, n_matches"
            " FROM rollup_matchups"
            " WHERE format_id = %s AND arch_a = %s AND arch_b = %s AND as_of <= %s"
            " ORDER BY as_of",
            (format_id, arch_a, arch_b, until),
        )
        return cur.fetchall()


def matchup_spread_row(
    conn: psycopg.Connection, format_id: int, as_of: dt.date, arch_a: int
) -> list[tuple]:
    """One archetype's matrix row (its cells vs every universe member)."""
    with conn.cursor() as cur:
        cur.execute(
            "SELECT arch_b, p_a_beats_b, ci_lo, ci_hi, n_matches"
            " FROM rollup_matchups"
            " WHERE format_id = %s AND as_of = %s AND arch_a = %s ORDER BY arch_b",
            (format_id, as_of, arch_a),
        )
        return cur.fetchall()


def best_deck_score(
    conn: psycopg.Connection, format_id: int, as_of: dt.date, archetype_id: int
) -> float | None:
    with conn.cursor() as cur:
        cur.execute(
            "SELECT exp_winrate_vs_field FROM rollup_best_decks"
            " WHERE format_id = %s AND as_of = %s AND archetype_id = %s",
            (format_id, as_of, archetype_id),
        )
        row = cur.fetchone()
    return float(row[0]) if row else None


def best_deck_rows(conn: psycopg.Connection, format_id: int, as_of: dt.date) -> list[tuple]:
    with conn.cursor() as cur:
        cur.execute(
            "SELECT rank, archetype_id, exp_winrate_vs_field"
            " FROM rollup_best_decks WHERE format_id = %s AND as_of = %s ORDER BY rank",
            (format_id, as_of),
        )
        return cur.fetchall()


def event_rows(conn: psycopg.Connection, format_id: int, limit: int) -> list[tuple]:
    with conn.cursor() as cur:
        cur.execute(
            "SELECT event_id, date, name, source, player_count, top_archetype_id"
            " FROM rollup_events WHERE format_id = %s"
            " ORDER BY date DESC, event_id DESC LIMIT %s",
            (format_id, limit),
        )
        return cur.fetchall()
