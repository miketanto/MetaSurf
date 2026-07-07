"""Property tests for the game-neutral recommender decision rules."""

from __future__ import annotations

import numpy as np

from models.recommender import (
    best_response_index,
    field_response_scores,
    most_popular_index,
    rank_by_best_response,
    strongest_index,
)

# rock-paper-scissors: 0 beats 1 beats 2 beats 0
RPS = np.array([[0.5, 0.8, 0.2], [0.2, 0.5, 0.8], [0.8, 0.2, 0.5]])


def test_best_response_picks_the_counter_to_the_field():
    # field is mostly strategy 1; 0 beats 1, so 0 is the best response
    shares = np.array([0.1, 0.8, 0.1])
    assert best_response_index(shares, RPS) == 0
    # field mostly 2; 1 beats 2
    assert best_response_index(np.array([0.1, 0.1, 0.8]), RPS) == 1


def test_field_scores_average_half_against_uniform_field():
    shares = np.full(3, 1 / 3)
    assert np.allclose(field_response_scores(shares, RPS), 0.5)


def test_rank_is_full_permutation_stable():
    shares = np.array([0.2, 0.7, 0.1])
    order = rank_by_best_response(shares, RPS)
    assert sorted(order.tolist()) == [0, 1, 2]
    # top of the ranking is the best-response pick
    assert order[0] == best_response_index(shares, RPS)


def test_ties_break_to_lowest_index():
    # symmetric field + symmetric payoff -> all scores equal -> pick index 0
    flat = np.full((3, 3), 0.5)
    assert best_response_index(np.full(3, 1 / 3), flat) == 0


def test_baselines():
    assert most_popular_index(np.array([0.2, 0.5, 0.3])) == 1
    assert strongest_index(np.array([0.48, 0.55, 0.51])) == 1


def test_deterministic():
    shares = np.array([0.2, 0.5, 0.3])
    assert best_response_index(shares, RPS) == best_response_index(shares, RPS)
    assert np.array_equal(
        rank_by_best_response(shares, RPS), rank_by_best_response(shares, RPS)
    )
