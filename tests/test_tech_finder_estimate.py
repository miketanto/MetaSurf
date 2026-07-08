"""Layer B estimator on a constructed case with a known answer.

Property-style check (allowed IN ADDITION to the real-data run in
validation.tech_finder): a role that specifically lifts winrate vs one opponent
must get a high A-specific DiD; a role that lifts winrate vs everyone equally
must get ~0. This is the confound the whole design exists to defeat (§4c).
"""

from __future__ import annotations

from validation.tech_finder.estimate import (
    DirectedRow,
    rank_of,
    role_effects_for_opponent,
)


def _rows(arch: str, opp: str, role: str | None, n: int, wins: int) -> list[DirectedRow]:
    roles = frozenset({role}) if role else frozenset()
    return [DirectedRow(arch, opp, 1 if i < wins else 0, roles) for i in range(n)]


def _dataset() -> list[DirectedRow]:
    rows: list[DirectedRow] = []
    # Archetype X1 carries the SPECIFIC role "landkill": it lifts WR vs Tron
    # (0.8 with vs 0.4 without) but does nothing vs the field (0.5 vs 0.5).
    rows += _rows("X1", "Tron", "landkill", 40, 32)  # vs A, with R: .80
    rows += _rows("X1", "Tron", None, 40, 16)  # vs A, without R: .40
    rows += _rows("X1", "Field", "landkill", 40, 20)  # vs field, with R: .50
    rows += _rows("X1", "Field", None, 40, 20)  # vs field, without R: .50
    # Archetype X2 carries the GENERIC role "goodstuff": lifts WR vs everyone
    # equally (0.7 vs 0.4 both vs Tron and vs field) -> A-specific effect ~0.
    rows += _rows("X2", "Tron", "goodstuff", 40, 28)  # .70
    rows += _rows("X2", "Tron", None, 40, 16)  # .40
    rows += _rows("X2", "Field", "goodstuff", 40, 28)  # .70
    rows += _rows("X2", "Field", None, 40, 16)  # .40
    return rows


def test_specific_role_beats_generic_role() -> None:
    effects = role_effects_for_opponent(
        _dataset(), "Tron", ("landkill", "goodstuff"), min_cell=10
    )
    by = {e.role: e for e in effects}

    # the specific role's DiD ~ 0.4, the generic role's ~ 0.0
    assert abs(by["landkill"].a_specific - 0.40) < 1e-9
    assert abs(by["goodstuff"].a_specific - 0.0) < 1e-9

    # ranked by A-specific effect, the tech role is #1
    assert effects[0].role == "landkill"
    assert rank_of(effects, {"landkill"}, "a_specific") == 1


def test_naive_prevalence_does_not_distinguish() -> None:
    # both roles are equally present vs Tron, so the frequency-only baseline
    # cannot tell the real tech from the generic card -- the point of §4c.
    effects = role_effects_for_opponent(
        _dataset(), "Tron", ("landkill", "goodstuff"), min_cell=10
    )
    by = {e.role: e for e in effects}
    assert abs(by["landkill"].prevalence_vs_a - by["goodstuff"].prevalence_vs_a) < 1e-9


def test_min_cell_filters_thin_strata() -> None:
    thin = _rows("X1", "Tron", "landkill", 3, 3) + _rows("X1", "Tron", None, 3, 0)
    thin += _rows("X1", "Field", "landkill", 3, 2) + _rows("X1", "Field", None, 3, 1)
    effects = role_effects_for_opponent(thin, "Tron", ("landkill",), min_cell=20)
    assert effects[0].n_strata == 0  # nothing meets the cell floor
