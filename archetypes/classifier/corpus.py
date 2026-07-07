"""Corpus + definitions loaders shared by the batch labeler and the V1 suites.

Everything is deterministic: decks are loaded ordered by decks.id, rule
definitions come from the committed port, and the engine/clusterer carry no
randomness.
"""

from __future__ import annotations

import datetime as dt
from dataclasses import dataclass

import psycopg

from archetypes.classifier.definitions import (
    FormatDefinitions,
    LoadReport,
    build_fold_index,
    load_format,
)
from archetypes.classifier.engine import ENGINE_SEMANTICS, Classification, Deck, classify
from ingest.formats_config import load_formats
from ingest.normalize.resolver import CardResolver


@dataclass(frozen=True)
class LoadedDeck:
    deck_id: int
    event_date: dt.date
    deck: Deck


def load_definitions(
    conn: psycopg.Connection,
    exclude_archetype_files: frozenset[str] = frozenset(),
    format_name: str = "modern",
) -> tuple[FormatDefinitions, LoadReport]:
    resolver = CardResolver.from_db(conn, "mtg")
    with conn.cursor() as cur:
        cur.execute(
            "SELECT c.name, c.id FROM cards c JOIN games g ON g.id = c.game_id"
            " WHERE g.name = 'mtg' ORDER BY c.id"
        )
        fold_index = build_fold_index(cur.fetchall())
    report = LoadReport()
    defs = load_format(
        format_name,
        resolver.resolve,
        fold_index,
        ENGINE_SEMANTICS,
        report=report,
        exclude_file_stems=exclude_archetype_files,
    )
    return defs, report


def load_decks(
    conn: psycopg.Connection,
    start: dt.date,
    end: dt.date,
    format_name: str = "modern",
) -> list[LoadedDeck]:
    """All decks of the format with event date in [start, end], ordered by deck
    id. Zones come from deck_cards (board 'main'/'side'); empty decks excluded."""
    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT d.id, e.date, dc.board, dc.card_id, dc.count
            FROM decks d
            JOIN events e ON e.id = d.event_id
            JOIN formats f ON f.id = e.format_id AND f.name = %s
            JOIN deck_cards dc ON dc.deck_id = d.id
            WHERE e.date BETWEEN %s AND %s
            ORDER BY d.id, dc.board, dc.card_id
            """,
            (format_name, start, end),
        )
        out: list[LoadedDeck] = []
        cur_id: int | None = None
        cur_date: dt.date | None = None
        main: dict[int, int] = {}
        side: dict[int, int] = {}

        def flush() -> None:
            if cur_id is not None and (main or side):
                assert cur_date is not None
                out.append(
                    LoadedDeck(cur_id, cur_date, Deck(main=dict(main), side=dict(side)))
                )

        for deck_id, date, board, card_id, count in cur:
            if deck_id != cur_id:
                flush()
                cur_id, cur_date = deck_id, date
                main, side = {}, {}
            (main if board == "main" else side)[card_id] = count
        flush()
    return out


def rules_label(decks: list[LoadedDeck], defs: FormatDefinitions) -> list[Classification]:
    return [classify(d.deck, defs) for d in decks]


def basic_land_ids(conn: psycopg.Connection) -> frozenset[int]:
    """Vector-exclusion set from formats.config (config over code)."""
    fmt = next(f for f in load_formats() if f.game == "mtg" and f.name == "modern")
    prefixes = fmt.vector_exclude_type_line_prefixes
    if not prefixes:
        return frozenset()
    with conn.cursor() as cur:
        cur.execute(
            "SELECT id FROM cards WHERE "
            + " OR ".join("attrs->>'type_line' LIKE %s" for _ in prefixes),
            tuple(f"{p}%" for p in prefixes),
        )
        return frozenset(r[0] for r in cur.fetchall())
