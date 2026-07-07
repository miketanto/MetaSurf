"""Hierarchical Bayesian beta-binomial winrate model (plan §5 Layer 2).

Game-neutral by construction (plan §4.1 rule 2): consumes integer archetype
ids, integer day indexes, and match outcomes — nothing else. All estimation
is conjugate/closed-form; the model contains no random number generation, so
determinism reduces to deterministic inputs (asserted by the V2 suite).

Structure:

- Format level: pooled decayed winrate ``format_mean`` (the mean of the
  format-level prior).
- Archetype level: winrate of archetype ``a`` has prior
  ``Beta(format_mean * k0, (1 - format_mean) * k0)`` (``k0`` =
  ``prior_strength``, in pseudo-matches) updated with exponentially
  time-decayed match evidence: weight ``0.5 ** (age_days / half_life)``.
- Pair level (matchup matrix), one hierarchy level deeper: the prior mean for
  ``P(a beats b)`` combines the two *shrunk* archetype winrates on the
  log-odds scale, ``sigmoid(logit(m_a) - logit(m_b))`` — this centering is
  coherent under transposition (``prior(b,a) = 1 - prior(a,b)``) and reduces
  to each archetype's overall strength against an average opponent. Pair
  evidence (both sides resolved) updates a ``Beta(prior_mean * k1, ...)``
  cell; thin pair samples therefore shrink toward the archetype-level
  winrates exactly as the plan specifies.

Outcome encoding: a stored match contributes ``win_frac`` = 1.0 (side-a match
win), 0.0 (loss), or 0.5 (drawn match, split as half win / half loss so the
evidence keeps its weight). Matches with an unresolved opponent update only
side a's archetype total (their opponent's archetype is unknown, the result
is still real evidence against the field); pair cells use only both-resolved
matches. Mirror pair cells are exactly 0.5 by construction.

``half_life_days=None`` disables decay and ``hierarchical=False`` replaces
both hierarchical priors with flat ``Beta(1, 1)`` — these are the V2.3
ablation switches, kept in the model so ablations exercise the same code
path.

Default hyperparameters are frozen from the M2 tuning run (see
``validation/v2_winrates/tune.py``): tuned by grid search on walk-forward
log-loss over tuning weeks 2022-07-02 .. 2023-12-30, a period disjoint from
and strictly before the V2.1 evaluation weeks.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
from scipy import stats

UNKNOWN = -1

# Frozen by validation/v2_winrates/tune.py on the tuning window (Saturdays
# 2022-07-02 .. 2023-12-30, disjoint from and before the evaluation weeks).
# Grid: half_life {7,10,14,21,28,42,63,91,126,182,365,730} x prior_strength
# {5,10,20,50} x pair_prior_strength {5,10,20,50}; best mean weekly log-loss
# 0.684814 at (182, 10, 20) — an interior optimum (126d: 0.685068, 365d:
# 0.684846). The plan's 14-21d initial guess sits on a very flat surface
# (21d: 0.688773); archetype winrates decay far slower than expected.
DEFAULT_HALF_LIFE_DAYS = 182.0
DEFAULT_PRIOR_STRENGTH = 10.0
DEFAULT_PAIR_PRIOR_STRENGTH = 20.0


@dataclass(frozen=True)
class MatchData:
    """Column arrays, one row per stored match.

    day: integer day index (e.g. ``date.toordinal()``);
    side_a / side_b: archetype ids, ``UNKNOWN`` when the side's deck or
    archetype is unresolved (side_a is never UNKNOWN);
    win_frac: side a's match outcome (1.0 / 0.5 / 0.0).
    """

    day: np.ndarray
    side_a: np.ndarray
    side_b: np.ndarray
    win_frac: np.ndarray

    def __post_init__(self) -> None:
        n = len(self.day)
        if not (len(self.side_a) == len(self.side_b) == len(self.win_frac) == n):
            raise ValueError("MatchData arrays must have equal length")
        if n and int(self.side_a.min()) < 0:
            raise ValueError("side_a must always be a resolved archetype id")

    @property
    def n(self) -> int:
        return len(self.day)


def _logit(p: np.ndarray) -> np.ndarray:
    return np.log(p) - np.log1p(-p)


@dataclass(frozen=True)
class Posterior:
    """Fitted state as of a cutoff day; all queries are closed-form."""

    n_archetypes: int
    format_mean: float
    arch_alpha: np.ndarray  # per-archetype posterior Beta parameters
    arch_beta: np.ndarray
    pair_wins: np.ndarray  # (n, n) decayed evidence for P(row beats col)
    pair_losses: np.ndarray
    pair_prior_strength: float
    hierarchical: bool

    def archetype_mean(self) -> np.ndarray:
        return self.arch_alpha / (self.arch_alpha + self.arch_beta)

    def archetype_interval(self, level: float = 0.90) -> tuple[np.ndarray, np.ndarray]:
        """Central credible interval for each archetype's latent winrate."""
        tail = (1.0 - level) / 2.0
        lo = stats.beta.ppf(tail, self.arch_alpha, self.arch_beta)
        hi = stats.beta.ppf(1.0 - tail, self.arch_alpha, self.arch_beta)
        return lo, hi

    def _pair_prior_mean(self, a: np.ndarray, b: np.ndarray) -> np.ndarray:
        if not self.hierarchical:
            return np.full(len(a), 0.5)
        m = self.archetype_mean()
        z = _logit(m[a]) - _logit(m[b])
        return 1.0 / (1.0 + np.exp(-z))

    def pair_posterior(self, a: np.ndarray, b: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
        prior_mean = self._pair_prior_mean(a, b)
        k1 = self.pair_prior_strength
        alpha = prior_mean * k1 + self.pair_wins[a, b]
        beta = (1.0 - prior_mean) * k1 + self.pair_losses[a, b]
        return alpha, beta

    def match_prob(self, a: np.ndarray, b: np.ndarray) -> np.ndarray:
        """P(archetype a beats archetype b); b may be UNKNOWN (vs the field)."""
        a = np.asarray(a)
        b = np.asarray(b)
        out = np.empty(len(a))
        known = b != UNKNOWN
        if known.any():
            alpha, beta = self.pair_posterior(a[known], b[known])
            out[known] = alpha / (alpha + beta)
        if (~known).any():
            out[~known] = self.archetype_mean()[a[~known]]
        return out

    def matchup_interval(
        self, a: np.ndarray, b: np.ndarray, level: float = 0.90
    ) -> tuple[np.ndarray, np.ndarray]:
        alpha, beta = self.pair_posterior(np.asarray(a), np.asarray(b))
        tail = (1.0 - level) / 2.0
        return stats.beta.ppf(tail, alpha, beta), stats.beta.ppf(1.0 - tail, alpha, beta)

    def predictive_win_interval(
        self, a: int, n_future: int, level: float = 0.90
    ) -> tuple[int, int]:
        """Beta-binomial central predictive interval for the number of wins in
        ``n_future`` future matches of archetype ``a`` against the field —
        the observable-quantity form of the archetype interval (V2.2)."""
        tail = (1.0 - level) / 2.0
        lo = stats.betabinom.ppf(tail, n_future, self.arch_alpha[a], self.arch_beta[a])
        hi = stats.betabinom.ppf(1.0 - tail, n_future, self.arch_alpha[a], self.arch_beta[a])
        return int(lo), int(hi)


class WinrateModel:
    def __init__(
        self,
        half_life_days: float | None = DEFAULT_HALF_LIFE_DAYS,
        prior_strength: float = DEFAULT_PRIOR_STRENGTH,
        pair_prior_strength: float = DEFAULT_PAIR_PRIOR_STRENGTH,
        hierarchical: bool = True,
    ) -> None:
        if half_life_days is not None and half_life_days <= 0:
            raise ValueError("half_life_days must be positive (or None to disable decay)")
        self.half_life_days = half_life_days
        self.prior_strength = prior_strength
        self.pair_prior_strength = pair_prior_strength
        self.hierarchical = hierarchical

    def fit(self, data: MatchData, as_of_day: int, n_archetypes: int) -> Posterior:
        """Fit on matches strictly before ``as_of_day`` (later rows in ``data``
        are ignored, so walk-forward evaluation cannot leak by construction)."""
        past = data.day < as_of_day
        day = data.day[past]
        side_a = data.side_a[past]
        side_b = data.side_b[past]
        win_frac = data.win_frac[past]

        if self.half_life_days is None:
            w = np.ones(len(day))
        else:
            w = np.power(0.5, (as_of_day - day) / self.half_life_days)

        n = n_archetypes
        wins = np.bincount(side_a, weights=w * win_frac, minlength=n)
        losses = np.bincount(side_a, weights=w * (1.0 - win_frac), minlength=n)
        known = side_b != UNKNOWN
        wins += np.bincount(
            side_b[known], weights=(w * (1.0 - win_frac))[known], minlength=n
        )
        losses += np.bincount(side_b[known], weights=(w * win_frac)[known], minlength=n)

        key = side_a[known] * n + side_b[known]
        pw = np.bincount(key, weights=(w * win_frac)[known], minlength=n * n).reshape(n, n)
        pl = np.bincount(
            key, weights=(w * (1.0 - win_frac))[known], minlength=n * n
        ).reshape(n, n)
        # each stored match is evidence for both orientations of its pair cell
        pair_wins = pw + pl.T
        pair_losses = pl + pw.T

        total_w = float(wins.sum())
        total_l = float(losses.sum())
        format_mean = total_w / (total_w + total_l) if total_w + total_l > 0 else 0.5

        if self.hierarchical:
            alpha0 = format_mean * self.prior_strength
            beta0 = (1.0 - format_mean) * self.prior_strength
        else:
            alpha0 = beta0 = 1.0  # flat Beta(1,1): minimal smoothing, no hierarchy
        return Posterior(
            n_archetypes=n,
            format_mean=format_mean,
            arch_alpha=alpha0 + wins,
            arch_beta=beta0 + losses,
            pair_wins=pair_wins,
            pair_losses=pair_losses,
            pair_prior_strength=(self.pair_prior_strength if self.hierarchical else 2.0),
            hierarchical=self.hierarchical,
        )
