"""Functional-role layer for the tech finder (BL-1, research-log §4b).

Maps a card to a set of interaction *roles* (what it does — remove creatures,
destroy lands, hate graveyards, …) from its real Scryfall oracle text, using
rules in ``config/card_roles.json``. This is the "card understanding" layer:
the tech finder correlates *roles* with matchup outcomes, not raw card
presence, so that pooling by function buys sample size and role-level
A-specificity discounts generic answers (research-log §4b).

Deliberately interaction-only: engine/identity text (ramp, recursion, draw)
carries no role, so archetype-identity cards never enter the tech search.

Rules are authored against real oracle text saved in
``tests/fixtures/card_roles/labeled_cards.json`` — never from memory of a card.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

_CONFIG_PATH = Path(__file__).resolve().parents[2] / "config" / "card_roles.json"


@dataclass(frozen=True)
class RoleRule:
    role: str
    patterns: tuple[re.Pattern[str], ...]


@lru_cache(maxsize=1)
def load_rules(config_path: str | None = None) -> tuple[RoleRule, ...]:
    path = Path(config_path) if config_path else _CONFIG_PATH
    data = json.loads(path.read_text())
    rules: list[RoleRule] = []
    for entry in data["roles"]:
        pats = tuple(re.compile(p, re.IGNORECASE) for p in entry["any"])
        rules.append(RoleRule(role=entry["role"], patterns=pats))
    return tuple(rules)


def roles_for_text(
    oracle_text: str | None, rules: tuple[RoleRule, ...] | None = None
) -> frozenset[str]:
    """Return the set of roles whose rules match this oracle text.

    ``None``/empty text yields the empty set (never raises).
    """
    if not oracle_text:
        return frozenset()
    rules = rules or load_rules()
    text = oracle_text.lower()
    return frozenset(
        rule.role for rule in rules if any(p.search(text) for p in rule.patterns)
    )


def all_roles(rules: tuple[RoleRule, ...] | None = None) -> tuple[str, ...]:
    """The declared role vocabulary, in config order."""
    return tuple(r.role for r in (rules or load_rules()))
