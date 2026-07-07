"""Game-neutral classification boundary (the handoff's one architecture wrinkle).

Classifying a user-pasted list needs the game's rules engine and card
resolver, which the API may not import (game-neutrality gate). This module
is the boundary: a Protocol plus plain DTOs. Game adapters (e.g.
``archetypes/service.py``) implement the Protocol and are injected into the
app at startup by the serving entrypoint (``serve.py``, outside the gated
packages). Route code depends on this Protocol only.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from typing import Protocol

import psycopg


@dataclass(frozen=True)
class CardLine:
    """One pasted-list line; ``board`` is a per-game zone name from the
    format config (adapters reject zones their game doesn't have)."""

    name: str
    count: int
    board: str


@dataclass(frozen=True)
class DeckClassification:
    archetype_name: str
    method: str  # adapter vocabulary, e.g. 'rules' | 'fallback' | 'rogue'
    confidence: float | None
    # card names that did not resolve — reported, never guessed (CLAUDE.md)
    unresolved_cards: tuple[str, ...]


class ClassifierService(Protocol):
    def classify_deck(
        self, conn: psycopg.Connection, format_name: str, cards: Sequence[CardLine]
    ) -> DeckClassification:
        """Classify one deck. Raises ValueError on malformed input (e.g. an
        unknown board zone); unresolved card names are returned, not raised."""
        ...
