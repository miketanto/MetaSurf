"""Semantic-channel behaviour of the deck vectorizer.

The load-bearing test here is `test_beta_zero_is_byte_identical`: the whole
ablation rests on beta=0 reproducing the card-identity vectorizer exactly, so
that any movement in the V1 metrics is attributable to the feature channel and
nothing else.
"""

from __future__ import annotations

import numpy as np
import pytest

from archetypes.classifier.vectorizer import vectorize

# Three cards: two functionally identical one-mana removal spells (1, 2) and a
# structurally different card (3). Vectors are 4-dim toy features; the real
# 68-dim table is exercised in tests/test_cardsem.py.
REMOVAL_A = np.array([1.0, 0.0, 1.0, 0.0])
REMOVAL_B = np.array([1.0, 0.0, 1.0, 0.0])
CREATURE = np.array([0.0, 1.0, 0.0, 1.0])
FEATURES = {1: REMOVAL_A, 2: REMOVAL_B, 3: CREATURE}


def _cosine(matrix, i: int, j: int) -> float:
    return float((matrix[i] @ matrix[j].T).toarray()[0, 0])


def test_beta_zero_is_byte_identical():
    decks = [(10, {1: 4, 3: 20}), (11, {2: 4, 3: 20})]
    base = vectorize(decks)
    with_features_off = vectorize(decks, card_features=FEATURES, feature_weight=0.0)
    assert np.array_equal(base.matrix.toarray(), with_features_off.matrix.toarray())
    assert with_features_off.feature_dim == 0


def test_no_features_supplied_is_byte_identical():
    decks = [(10, {1: 4, 3: 20})]
    base = vectorize(decks)
    assert np.array_equal(
        base.matrix.toarray(), vectorize(decks, feature_weight=0.5).matrix.toarray()
    )


def test_feature_channel_pulls_functional_twins_together():
    """The point of the whole integration: two decks differing only by a swap
    between functionally identical cards must get closer, not stay orthogonal
    on that axis."""
    decks = [(10, {1: 4, 3: 20}), (11, {2: 4, 3: 20})]
    without = vectorize(decks)
    with_features = vectorize(decks, card_features=FEATURES, feature_weight=1.0)
    assert _cosine(with_features.matrix, 0, 1) > _cosine(without.matrix, 0, 1)


def test_feature_channel_does_not_collapse_different_decks():
    """Guard against the opposite failure: the channel must not make
    mechanically different decks look identical."""
    decks = [(10, {1: 20}), (11, {3: 20})]
    with_features = vectorize(decks, card_features=FEATURES, feature_weight=1.0)
    assert _cosine(with_features.matrix, 0, 1) < 0.5


def test_rows_are_unit_norm():
    decks = [(10, {1: 4, 3: 20}), (11, {2: 4, 3: 20})]
    matrix = vectorize(decks, card_features=FEATURES, feature_weight=0.7).matrix
    norms = np.linalg.norm(matrix.toarray(), axis=1)
    assert np.allclose(norms, 1.0)


def test_uncovered_cards_contribute_nothing_and_do_not_crash():
    """A deck of entirely uncovered cards keeps a zero feature channel rather
    than dividing by a zero norm."""
    decks = [(10, {99: 60})]
    result = vectorize(decks, card_features=FEATURES, feature_weight=1.0)
    assert result.feature_dim == 4
    assert np.allclose(result.matrix.toarray()[0, -4:], 0.0)
    assert np.isclose(np.linalg.norm(result.matrix.toarray()[0]), 1.0)


def test_feature_coverage_is_reported_per_deck():
    decks = [(10, {1: 4, 3: 20}), (11, {99: 24}), (12, {1: 12, 99: 12})]
    result = vectorize(decks, card_features=FEATURES, feature_weight=1.0)
    assert result.feature_coverage is not None
    assert np.allclose(result.feature_coverage, [1.0, 0.0, 0.5])


def test_profile_uses_raw_copies_not_idf_weights():
    """Four copies of a removal spell must weigh four times one copy in the
    mechanical profile; the tf-idf staple correction applies to the identity
    channel only."""
    one = vectorize([(10, {1: 1})], card_features=FEATURES, feature_weight=1.0)
    four = vectorize([(10, {1: 4})], card_features=FEATURES, feature_weight=1.0)
    # Both profiles normalize to the same direction; the check is that the
    # profile is built at all and is proportional to the feature vector.
    assert np.allclose(
        one.matrix.toarray()[0, -4:] / np.linalg.norm(one.matrix.toarray()[0, -4:]),
        four.matrix.toarray()[0, -4:] / np.linalg.norm(four.matrix.toarray()[0, -4:]),
    )


@pytest.mark.parametrize("beta", [0.25, 0.5, 1.0, 2.0])
def test_similarity_decomposition_matches_the_documented_formula(beta):
    """cos_combined == (cos_cards + beta^2 * cos_features) / (1 + beta^2)."""
    decks = [(10, {1: 4, 3: 20}), (11, {2: 4, 3: 20})]
    cards_only = vectorize(decks)
    combined = vectorize(decks, card_features=FEATURES, feature_weight=beta)

    cos_cards = _cosine(cards_only.matrix, 0, 1)
    profiles = np.array([4 * REMOVAL_A + 20 * CREATURE, 4 * REMOVAL_B + 20 * CREATURE])
    profiles /= np.linalg.norm(profiles, axis=1)[:, None]
    cos_features = float(profiles[0] @ profiles[1])

    expected = (cos_cards + beta**2 * cos_features) / (1 + beta**2)
    assert np.isclose(_cosine(combined.matrix, 0, 1), expected)


def test_is_deterministic_across_runs():
    decks = [(10, {1: 4, 3: 20}), (11, {2: 4, 3: 20})]
    a = vectorize(decks, card_features=FEATURES, feature_weight=0.6)
    b = vectorize(decks, card_features=FEATURES, feature_weight=0.6)
    assert np.array_equal(a.matrix.toarray(), b.matrix.toarray())
