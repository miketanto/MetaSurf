"""Load the real Modern corpus into the estimator's card-agnostic inputs.

Deck roles = the union of functional roles over the deck's whole 75 (main and
side — tech lives in the sideboard). Each decided, non-mirror match becomes two
DirectedRows (one per player side). Results are ``W-L-D`` from deck_id_a's
perspective; a side wins iff it took more games; ties are dropped.
"""

from __future__ import annotations

import datetime as dt

import psycopg

from validation.tech_finder.estimate import DirectedRow


def _parse_wl(result: str) -> tuple[int, int] | None:
    parts = result.split("-")
    if len(parts) != 3:
        return None
    try:
        return int(parts[0]), int(parts[1])
    except ValueError:
        return None


def load_directed_rows(
    conn: psycopg.Connection,
    format_name: str = "modern",
    date_from: dt.date | None = None,
    date_to: dt.date | None = None,
) -> list[DirectedRow]:
    with conn.cursor() as cur:
        # deck -> role set over the whole 75 (any board)
        cur.execute(
            """
            SELECT dc.deck_id, array_agg(DISTINCT cr.role)
            FROM matches m
            JOIN deck_cards dc ON dc.deck_id IN (m.deck_id_a, m.deck_id_b)
            JOIN card_roles cr ON cr.card_id = dc.card_id
            GROUP BY dc.deck_id
            """
        )
        roles: dict[int, frozenset[str]] = {
            did: frozenset(rs) for did, rs in cur.fetchall()
        }

        # deck -> (archetype name, event date), for labeled decks of the format
        cur.execute(
            """
            SELECT d.id, a.name, e.date
            FROM decks d
            JOIN archetypes a ON a.id = d.archetype_id
            JOIN events e ON e.id = d.event_id
            JOIN formats f ON f.id = e.format_id AND f.name = %s
            """,
            (format_name,),
        )
        meta: dict[int, tuple[str, dt.date]] = {
            did: (name, date) for did, name, date in cur.fetchall()
        }

        cur.execute(
            "SELECT deck_id_a, deck_id_b, result FROM matches WHERE deck_id_b IS NOT NULL"
        )
        raw = cur.fetchall()

    ROGUE = "Rogue"
    rows: list[DirectedRow] = []
    for a, b, result in raw:
        ma, mb = meta.get(a), meta.get(b)
        if ma is None or mb is None:
            continue
        arch_a, date_a = ma
        arch_b, date_b = mb
        if arch_a in (arch_b, ROGUE) or arch_b == ROGUE:
            continue  # mirrors and Rogue carry no archetype signal
        wl = _parse_wl(result)
        if wl is None:
            continue
        wa, la = wl
        if wa == la:
            continue  # undecided
        ra = roles.get(a, frozenset())
        rb = roles.get(b, frozenset())
        # player = a (uses a's event date for windowing)
        if _in_window(date_a, date_from, date_to):
            rows.append(DirectedRow(arch_a, arch_b, 1 if wa > la else 0, ra))
        if _in_window(date_b, date_from, date_to):
            rows.append(DirectedRow(arch_b, arch_a, 1 if la > wa else 0, rb))
    return rows


def _in_window(d: dt.date, lo: dt.date | None, hi: dt.date | None) -> bool:
    return (lo is None or d >= lo) and (hi is None or d <= hi)
