"""Card-level tech estimator on a constructed case with a known answer."""

from __future__ import annotations

from validation.tech_finder.cards import CardRow, card_effects_for_opponent

FILLER = 999  # a card in every deck -> no with/without contrast -> unscorable
TECH = 100  # specifically lifts WR vs Tron within X1


def _rows(opp: str, cards: frozenset, n: int, wins: int) -> list[CardRow]:
    return [CardRow("X1", opp, 1 if i < wins else 0, cards) for i in range(n)]


def _dataset() -> list[CardRow]:
    both = frozenset({TECH, FILLER})
    only = frozenset({FILLER})
    rows = []
    rows += _rows("Tron", both, 40, 32)  # with TECH vs Tron: .80
    rows += _rows("Tron", only, 40, 16)  # without TECH vs Tron: .40
    rows += _rows("Field", both, 40, 20)  # with TECH vs field: .50
    rows += _rows("Field", only, 40, 20)  # without TECH vs field: .50
    return rows


def test_specific_card_scores_its_did() -> None:
    eff = card_effects_for_opponent(
        _dataset(), "Tron", min_cell=10, min_card_vs_a=10, min_strata=1
    )
    by = {e.card_id: e for e in eff}
    assert TECH in by
    assert abs(by[TECH].a_specific - 0.40) < 1e-9
    assert eff[0].card_id == TECH


def test_ubiquitous_card_is_unscorable() -> None:
    # FILLER is in every deck, so the "without" cell is always empty -> no
    # contributing strata -> it must not appear in the results.
    eff = card_effects_for_opponent(
        _dataset(), "Tron", min_cell=10, min_card_vs_a=10, min_strata=1
    )
    assert FILLER not in {e.card_id for e in eff}


def test_support_floor_excludes_thin_cards() -> None:
    eff = card_effects_for_opponent(
        _dataset(), "Tron", min_cell=10, min_card_vs_a=1000, min_strata=1
    )
    assert eff == []
