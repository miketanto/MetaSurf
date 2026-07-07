"""Weekly walk-forward machinery shared by the V2 tuner and the V2.1-V2.3
suites (plan §5 Layer 2): train on matches strictly before each Saturday,
test on that weekend's (Sat+Sun) matches.

Evaluation protocol (fixed before any evaluation ran, applied identically to
model and baselines):

- Evaluable test matches: both archetypes resolved, non-mirror, decisive
  (drawn matches carry no win/loss signal to score). Every week with at
  least one evaluable match counts — no volume-based week filtering.
- Canonical orientation: each test match is flipped so the lower archetype
  id is side a. Stored orientation is outcome-correlated (mtgo brackets list
  the winner first), so scoring in stored orientation would reward encoding
  a listing artifact; archetype-id order is fixed and outcome-independent.
- Baselines, all computed from the same training window with no decay and
  no shrinkage beyond a Laplace(+1) smoother (the "raw pooled" family):
    B0 raw-side-a:   P = side a's pooled winrate (opponent ignored);
    B1 raw-pooled:   P = sigmoid(logit(p_a) - logit(p_b)) from the two
                     pooled archetype winrates — the primary baseline;
    B2 raw-pair:     P = the raw pair cell (Laplace-smoothed).
  B1 is primary: B0 degenerates under canonical orientation and B2 is a
  matchup-level table dump rather than a pooled winrate.
"""

from __future__ import annotations

import datetime as dt
from dataclasses import dataclass

import numpy as np

from models.winrate import MatchData, Posterior, WinrateModel


def saturdays(first: dt.date, last: dt.date) -> list[dt.date]:
    assert first.isoweekday() == 6, "walk-forward cutoffs are Saturdays"
    out = []
    day = first
    while day <= last:
        out.append(day)
        day += dt.timedelta(days=7)
    return out


@dataclass(frozen=True)
class WeekEval:
    saturday: dt.date
    n_test: int
    y: np.ndarray  # canonical-orientation outcomes (1.0 side-a win)
    a: np.ndarray  # canonical side-a archetype ids
    b: np.ndarray


def evaluable_weekend(data: MatchData, saturday: dt.date) -> WeekEval:
    """Decisive, both-resolved, non-mirror matches of the Sat+Sun weekend,
    flipped to canonical (lower archetype id first) orientation."""
    sat = saturday.toordinal()
    in_weekend = (data.day == sat) | (data.day == sat + 1)
    decisive = data.win_frac != 0.5
    resolved = data.side_b >= 0
    non_mirror = data.side_a != data.side_b
    mask = in_weekend & decisive & resolved & non_mirror
    a = data.side_a[mask]
    b = data.side_b[mask]
    y = data.win_frac[mask]
    flip = a > b
    a2 = np.where(flip, b, a)
    b2 = np.where(flip, a, b)
    y2 = np.where(flip, 1.0 - y, y)
    return WeekEval(saturday=saturday, n_test=int(mask.sum()), y=y2, a=a2, b=b2)


def log_loss(y: np.ndarray, p: np.ndarray, eps: float = 1e-9) -> float:
    p = np.clip(p, eps, 1.0 - eps)
    return float(-np.mean(y * np.log(p) + (1.0 - y) * np.log(1.0 - p)))


def _logit(p: np.ndarray) -> np.ndarray:
    return np.log(p) - np.log1p(-p)


def baseline_probs(raw: Posterior, week: WeekEval) -> dict[str, np.ndarray]:
    """B0/B1/B2 from a no-decay, non-hierarchical (Laplace) posterior."""
    mean = raw.archetype_mean()
    p_a, p_b = mean[week.a], mean[week.b]
    b1 = 1.0 / (1.0 + np.exp(-(_logit(p_a) - _logit(p_b))))
    b2 = raw.match_prob(week.a, week.b)  # flat pair prior = Laplace pair cell
    return {"B0_raw_side_a": p_a, "B1_raw_pooled": b1, "B2_raw_pair": b2}


@dataclass
class WalkForwardResult:
    weeks: list[dt.date]
    n_test: list[int]
    model_ll: list[float]
    baseline_ll: dict[str, list[float]]
    # pooled across all weeks, for calibration analysis
    pooled_y: np.ndarray
    pooled_p_model: np.ndarray
    pooled_p_baseline: np.ndarray  # primary baseline (B1)

    def weeks_beating(self, baseline: str = "B1_raw_pooled") -> int:
        return sum(
            1 for m, b in zip(self.model_ll, self.baseline_ll[baseline], strict=True) if m < b
        )


def run_walkforward(
    data: MatchData,
    n_archetypes: int,
    cutoffs: list[dt.date],
    model: WinrateModel,
) -> WalkForwardResult:
    raw_model = WinrateModel(half_life_days=None, hierarchical=False)
    weeks: list[dt.date] = []
    n_test: list[int] = []
    model_ll: list[float] = []
    baseline_ll: dict[str, list[float]] = {}
    ys: list[np.ndarray] = []
    ps_model: list[np.ndarray] = []
    ps_base: list[np.ndarray] = []
    for saturday in cutoffs:
        week = evaluable_weekend(data, saturday)
        if week.n_test == 0:
            continue
        as_of = saturday.toordinal()
        post = model.fit(data, as_of, n_archetypes)
        raw = raw_model.fit(data, as_of, n_archetypes)
        p_model = post.match_prob(week.a, week.b)
        bases = baseline_probs(raw, week)
        weeks.append(saturday)
        n_test.append(week.n_test)
        model_ll.append(log_loss(week.y, p_model))
        for name, p in bases.items():
            baseline_ll.setdefault(name, []).append(log_loss(week.y, p))
        ys.append(week.y)
        ps_model.append(p_model)
        ps_base.append(bases["B1_raw_pooled"])
    return WalkForwardResult(
        weeks=weeks,
        n_test=n_test,
        model_ll=model_ll,
        baseline_ll=baseline_ll,
        pooled_y=np.concatenate(ys) if ys else np.empty(0),
        pooled_p_model=np.concatenate(ps_model) if ps_model else np.empty(0),
        pooled_p_baseline=np.concatenate(ps_base) if ps_base else np.empty(0),
    )


def calibration_slope(y: np.ndarray, p: np.ndarray) -> tuple[float, float]:
    """Cox calibration: logistic regression of outcomes on logit(p̂); returns
    (slope, intercept). Newton-Raphson, fixed start, deterministic."""
    x = _logit(np.clip(p, 1e-9, 1.0 - 1e-9))
    beta = np.array([0.0, 1.0])  # intercept, slope
    X = np.column_stack([np.ones_like(x), x])
    for _ in range(50):
        eta = X @ beta
        mu = 1.0 / (1.0 + np.exp(-eta))
        w = mu * (1.0 - mu)
        grad = X.T @ (y - mu)
        hess = (X * w[:, None]).T @ X
        step = np.linalg.solve(hess, grad)
        beta = beta + step
        if float(np.max(np.abs(step))) < 1e-10:
            break
    return float(beta[1]), float(beta[0])


def reliability_table(
    y: np.ndarray, p: np.ndarray, n_bins: int = 10
) -> list[tuple[float, float, int, float, float]]:
    """(bin_lo, bin_hi, n, mean_predicted, empirical_rate) per non-empty bin."""
    edges = np.linspace(0.0, 1.0, n_bins + 1)
    rows = []
    for i in range(n_bins):
        lo, hi = edges[i], edges[i + 1]
        m = (p >= lo) & (p < hi) if i < n_bins - 1 else (p >= lo) & (p <= hi)
        if not m.any():
            continue
        rows.append((float(lo), float(hi), int(m.sum()), float(p[m].mean()), float(y[m].mean())))
    return rows
