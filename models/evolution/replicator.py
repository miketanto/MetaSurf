"""Replicator-dynamics share forecaster (M3.5 prototype).

Motivation (see docs/notes/m35-replicator-proposal.md): the V3 Holt model
treats each archetype's share as an independent trend, but the metagame is a
coupled non-transitive (rock-paper-scissors) system — a proven structural
fact for real competitive games (Czarnecki et al. 2020, "Real World Games
Look Like Spinning Tops"; Omidshafiei et al. 2019, alpha-Rank). The V3.2
finding (winners lose share next week: negative-frequency-dependent
selection) is the signature of that structure. Replicator dynamics model it
directly: shares flow toward strategies that beat the *current field*, which
in turn creates the counter-adaptation cycle.

Game-neutral by construction (plan §4.1 rule 2): consumes a share vector and
a payoff (matchup) matrix of plain floats — no game-specific ids, names, or
modules. No randomness; determinism reduces to deterministic inputs.

One-step forecast (log-linear / exponential replicator):

    f_a  = sum_b W[a, b] * x_b          # a's expected win prob vs the field
    x'_a = x_a * exp(eta * (f_a - 0.5)) # grow above-average, shrink below
    x'   = x' / sum(x')                 # renormalize onto the simplex

W[a, b] = P(a beats b) is antisymmetric about 0.5 (W[a,b] + W[b,a] = 1), so
the field-mean fitness sum_a x_a f_a is identically 0.5 and 0.5 is the honest
"average opponent" pivot. ``eta`` is the sole hyperparameter, a responsiveness
/ temperature: **eta = 0 reproduces persistence exactly** (x' = x), so a tuner
that selects eta ≈ 0 is itself the verdict that the dynamics add nothing.
Zero-share strategies stay zero (a one-step share forecast cannot conjure an
archetype from nothing); emergence is Layer 1's job, not this model's.
"""

from __future__ import annotations

import numpy as np


def field_fitness(shares: np.ndarray, payoff: np.ndarray) -> np.ndarray:
    """f_a = sum_b W[a, b] * x_b — each strategy's expected win probability
    against the current mixture. ``payoff`` is (n, n) with payoff[a, b] =
    P(a beats b); ``shares`` is length n and should sum to ~1 over its
    support."""
    return payoff @ shares


def replicator_step(
    shares: np.ndarray, payoff: np.ndarray, eta: float
) -> np.ndarray:
    """One exponential-replicator update. Preserves the support (zero stays
    zero) and returns a renormalized share vector. eta=0 -> identity
    (persistence)."""
    x = np.asarray(shares, dtype=np.float64)
    total = x.sum()
    if total <= 0:
        return x.copy()
    f = field_fitness(x, payoff)
    growth = np.exp(eta * (f - 0.5))
    updated = x * growth
    s = updated.sum()
    if s <= 0:
        return x.copy()
    return updated / s * total
