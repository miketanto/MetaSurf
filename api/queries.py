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
_SNAPSHOT_TABLES = frozenset(
    {"rollup_meta", "rollup_matchups", "rollup_best_decks", "rollup_emerging"}
)


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


def last_data_weeks(conn: psycopg.Connection, format_id: int, n: int) -> list[dt.date]:
    """The format's most recent n data weeks, oldest first."""
    with conn.cursor() as cur:
        cur.execute(
            "SELECT DISTINCT week FROM rollup_archetype_ts"
            " WHERE format_id = %s ORDER BY week DESC LIMIT %s",
            (format_id, n),
        )
        return sorted(row[0] for row in cur.fetchall())


def week_shares(
    conn: psycopg.Connection, format_id: int, week: dt.date
) -> dict[int, tuple[float, int]]:
    """archetype -> (share, n_decks) for one data week."""
    with conn.cursor() as cur:
        cur.execute(
            "SELECT archetype_id, share, n_decks FROM rollup_archetype_ts"
            " WHERE format_id = %s AND week = %s",
            (format_id, week),
        )
        return {int(a): (float(s), int(n)) for a, s, n in cur.fetchall()}


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


def emerging_clusters(conn: psycopg.Connection, format_id: int, as_of: dt.date) -> list[tuple]:
    """One row per candidate emerging cluster in the snapshot, biggest/newest
    first (the writer's stored order: size desc, first_seen, cluster_key)."""
    with conn.cursor() as cur:
        cur.execute(
            "SELECT cluster_key, provisional_descriptor, color, n_decks, first_seen,"
            " recent_decks, winrate, n_match_games FROM rollup_emerging"
            " WHERE format_id = %s AND as_of = %s"
            " ORDER BY n_decks DESC, first_seen, cluster_key",
            (format_id, as_of),
        )
        return cur.fetchall()


def emerging_signatures(
    conn: psycopg.Connection, format_id: int, as_of: dt.date
) -> dict[int, list[tuple]]:
    """cluster_key -> ranked [(card_id, name, in_freq, out_freq, lift)]."""
    with conn.cursor() as cur:
        cur.execute(
            "SELECT s.cluster_key, s.card_id, c.name, s.in_cluster_freq,"
            " s.out_cluster_freq, s.lift FROM rollup_emerging_signature s"
            " JOIN cards c ON c.id = s.card_id"
            " WHERE s.format_id = %s AND s.as_of = %s ORDER BY s.cluster_key, s.rank",
            (format_id, as_of),
        )
        out: dict[int, list[tuple]] = {}
        for key, card_id, name, in_freq, out_freq, lift in cur.fetchall():
            out.setdefault(key, []).append((card_id, name, in_freq, out_freq, lift))
    return out


def archetype_decks(
    conn: psycopg.Connection, format_id: int, archetype_id: int, limit: int
) -> list[tuple]:
    """Recent stored decks of an archetype: newest first, best finish first."""
    with conn.cursor() as cur:
        cur.execute(
            "SELECT d.id, e.date, e.name, e.source, d.player, d.finish_rank,"
            " d.wins, d.losses"
            " FROM decks d JOIN events e ON e.id = d.event_id"
            " WHERE e.format_id = %s AND d.archetype_id = %s"
            " ORDER BY e.date DESC, d.finish_rank ASC NULLS LAST, d.id"
            " LIMIT %s",
            (format_id, archetype_id, limit),
        )
        return cur.fetchall()


def deck_header(
    conn: psycopg.Connection, format_id: int, deck_id: int
) -> tuple | None:
    """A deck's metadata (scoped to the format), or None if it isn't there."""
    with conn.cursor() as cur:
        cur.execute(
            "SELECT d.id, d.archetype_id, a.name, e.date, e.name, e.source,"
            " d.player, d.finish_rank, d.wins, d.losses"
            " FROM decks d JOIN events e ON e.id = d.event_id"
            " LEFT JOIN archetypes a ON a.id = d.archetype_id"
            " WHERE e.format_id = %s AND d.id = %s",
            (format_id, deck_id),
        )
        return cur.fetchone()


def deck_card_rows(conn: psycopg.Connection, deck_id: int) -> list[tuple]:
    """(name, count, board) for a deck's whole 75, board then name."""
    with conn.cursor() as cur:
        cur.execute(
            "SELECT c.name, dc.count, dc.board FROM deck_cards dc"
            " JOIN cards c ON c.id = dc.card_id"
            " WHERE dc.deck_id = %s ORDER BY dc.board, c.name",
            (deck_id,),
        )
        return cur.fetchall()


def deck_colors(
    conn: psycopg.Connection, deck_ids: list[int], min_copies: int = 4
) -> dict[int, list[str]]:
    """Per-deck colour codes: a colour counts when >= ``min_copies`` copies in
    the deck carry it in card data (filters single-card splashes). Empty list =
    colourless. Codes are whatever the card data stores; the client orders them."""
    if not deck_ids:
        return {}
    out: dict[int, list[str]] = {}
    with conn.cursor() as cur:
        cur.execute(
            "SELECT dc.deck_id, ci FROM deck_cards dc JOIN cards c ON c.id = dc.card_id"
            " CROSS JOIN LATERAL jsonb_array_elements_text(c.attrs->'color_identity') ci"
            " WHERE dc.deck_id = ANY(%s)"
            " GROUP BY dc.deck_id, ci HAVING sum(dc.count) >= %s"
            " ORDER BY dc.deck_id, ci",
            (deck_ids, min_copies),
        )
        for did, code in cur.fetchall():
            out.setdefault(did, []).append(code)
    return out
