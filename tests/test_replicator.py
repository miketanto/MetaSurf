"""Property tests for the game-neutral replicator step (M3.5 prototype).

Pure-function property tests on hand-built payoff matrices; no DB needed.
"""

from __future__ import annotations

import numpy as np

from models.evolution import field_fitness, replicator_step

# A symmetric rock-paper-scissors payoff: 0 beats 1 beats 2 beats 0.
RPS = np.array(
    [
        [0.5, 0.8, 0.2],
        [0.2, 0.5, 0.8],
        [0.8, 0.2, 0.5],
    ]
)


def test_eta_zero_is_persistence():
    x = np.array([0.5, 0.3, 0.2])
    out = replicator_step(x, RPS, 0.0)
    assert np.allclose(out, x)


def test_step_preserves_simplex_mass():
    x = np.array([0.5, 0.3, 0.2])
    out = replicator_step(x, RPS, 4.0)
    assert np.isclose(out.sum(), 1.0)
    assert np.all(out >= 0)


def test_zero_share_strategies_stay_zero():
    x = np.array([0.6, 0.4, 0.0])
    out = replicator_step(x, RPS, 8.0)
    assert out[2] == 0.0
    assert np.isclose(out.sum(), 1.0)


def test_field_fitness_pivots_at_half():
    # against a uniform field, an antisymmetric payoff gives every strategy
    # fitness exactly 0.5 (no strategy beats a perfectly balanced field)
    x = np.full(3, 1 / 3)
    f = field_fitness(x, RPS)
    assert np.allclose(f, 0.5)
    # so the replicator leaves the uniform mixture fixed
    assert np.allclose(replicator_step(x, RPS, 6.0), x)


def test_growth_favors_beating_the_current_field():
    # field is heavy on strategy 1; strategy 0 beats 1, so 0 should gain share
    x = np.array([0.2, 0.7, 0.1])
    out = replicator_step(x, RPS, 4.0)
    assert out[0] > x[0]
    assert out[1] < x[1]


def test_rps_cycles_over_iterations():
    # iterate from a 0-heavy field; the argmax share should rotate 0 -> 1 -> 2
    # (predators overtake the prey), the signature non-transitive behavior
    x = np.array([0.8, 0.1, 0.1])
    payoff = RPS
    leaders = []
    for _ in range(60):
        x = replicator_step(x, payoff, 6.0)
        leaders.append(int(np.argmax(x)))
    assert set(leaders) == {0, 1, 2}  # all three lead at some point


def test_deterministic():
    x = np.array([0.5, 0.3, 0.2])
    a = replicator_step(x, RPS, 3.0)
    b = replicator_step(x, RPS, 3.0)
    assert np.array_equal(a, b)
