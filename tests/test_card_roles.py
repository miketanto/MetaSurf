"""Layer A role parser vs real Scryfall oracle text.

Fixtures in tests/fixtures/card_roles/labeled_cards.json hold the real
oracle_text of 32 cards (pulled from the Scryfall bulk) plus their expected
functional roles, and one edge fixture with null text. The parser must
reproduce every label exactly — including the negative case (Kolaghan's
Command says "from your graveyard" = recursion, and must NOT be graveyard_hate).
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from archetypes.roles import all_roles, load_rules, roles_for_text

_FIXTURES = json.loads(
    (Path(__file__).parent / "fixtures" / "card_roles" / "labeled_cards.json").read_text()
)


@pytest.mark.parametrize("card", _FIXTURES, ids=[c["name"] for c in _FIXTURES])
def test_roles_match_fixture(card: dict) -> None:
    got = roles_for_text(card["oracle_text"])
    assert got == frozenset(card["expected_roles"]), (
        f"{card['name']}: got {sorted(got)}, expected {card['expected_roles']}"
    )


def test_null_text_is_empty_not_error() -> None:
    assert roles_for_text(None) == frozenset()
    assert roles_for_text("") == frozenset()


def test_graveyard_recursion_is_not_graveyard_hate() -> None:
    # the load-bearing negative: using your own graveyard != hating graveyards
    txt = "Return target creature card from your graveyard to your hand."
    assert "graveyard_hate" not in roles_for_text(txt)


def test_every_expected_role_is_in_vocabulary() -> None:
    vocab = set(all_roles())
    for card in _FIXTURES:
        assert set(card["expected_roles"]) <= vocab


def test_rules_compile() -> None:
    assert len(load_rules()) >= 1
