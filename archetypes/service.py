"""MTG implementation of the read API's ClassifierService Protocol.

Wraps the exact stack the batch labeler uses — CardResolver for name
resolution, the ported rule definitions, and the deterministic rules/fallback
engine — so an on-demand classification of a pasted list reproduces the label
the corpus pipeline would assign (same classifier_version, same identity
mapping: rule Name, or Rogue when nothing matches).

Definitions and the resolver are loaded once per process on first use and
cached; they are immutable per classifier_version.
"""

from __future__ import annotations

from collections.abc import Sequence

import psycopg

from api.classifier import CardLine, DeckClassification
from archetypes.classifier.corpus import load_definitions
from archetypes.classifier.definitions import FormatDefinitions
from archetypes.classifier.engine import Deck, classify
from archetypes.labeler import METHOD_FALLBACK, METHOD_ROGUE, METHOD_RULES, ROGUE_NAME
from ingest.normalize.resolver import CardResolver

_BOARD_ZONES = ("main", "side")


class MtgClassifierService:
    def __init__(self) -> None:
        self._defs: dict[str, FormatDefinitions] = {}
        self._resolver: CardResolver | None = None

    def _definitions(self, conn: psycopg.Connection, format_name: str) -> FormatDefinitions:
        if format_name not in self._defs:
            self._defs[format_name], _report = load_definitions(conn, format_name=format_name)
        return self._defs[format_name]

    def _resolve(self, conn: psycopg.Connection, name: str) -> int | None:
        if self._resolver is None:
            self._resolver = CardResolver.from_db(conn, "mtg")
        return self._resolver.resolve(name)

    def classify_deck(
        self, conn: psycopg.Connection, format_name: str, cards: Sequence[CardLine]
    ) -> DeckClassification:
        main: dict[int, int] = {}
        side: dict[int, int] = {}
        unresolved: list[str] = []
        for line in cards:
            if line.board not in _BOARD_ZONES:
                raise ValueError(
                    f"unknown board zone {line.board!r}; expected one of {_BOARD_ZONES}"
                )
            card_id = self._resolve(conn, line.name)
            if card_id is None:
                unresolved.append(line.name)
                continue
            zone = main if line.board == "main" else side
            zone[card_id] = zone.get(card_id, 0) + line.count

        result = classify(Deck(main=main, side=side), self._definitions(conn, format_name))
        if result.match is None:
            return DeckClassification(ROGUE_NAME, METHOD_ROGUE, None, tuple(unresolved))
        if result.match.method == METHOD_RULES:
            return DeckClassification(
                result.match.archetype, METHOD_RULES, 1.0, tuple(unresolved)
            )
        return DeckClassification(
            result.match.archetype, METHOD_FALLBACK, result.match.similarity, tuple(unresolved)
        )
