"""Evolution model (plan §5 Layer 3): Holt's linear exponential smoothing per
series plus one behavioral coupling term (series level regressed on a lagged
external strength signal).

Game-neutral by construction (plan §4.1 rule 2): consumes float arrays
indexed by opaque series ids — shares, mean-copy counts, and strength values
arrive as plain numbers. No randomness anywhere; determinism reduces to
deterministic inputs.

Holt's linear method (standard formulation, deterministic initialization):

    l_0 = y_0,  b_0 = y_1 - y_0  (b_0 = 0 for a 1-point series)
    l_t = alpha * y_t + (1 - alpha) * (l_{t-1} + b_{t-1})
    b_t = beta * (l_t - l_{t-1}) + (1 - beta) * b_{t-1}
    one-step forecast: l_T + b_T

The coupling term implements the plan's flocking hypothesis ("players flock
to last weekend's winners"): the one-step share forecast is adjusted by
``gamma * s_last * (strength - 0.5)`` where ``s_last`` is the series' last
observed level and ``strength`` is the lagged latent winrate from Layer 2.
``gamma`` is fit by ordinary least squares on the training residuals
(observed - Holt forecast), closed form, no intercept — the Holt forecast is
already the level. V3.2 tests whether gamma is significant and stable; if it
is not, the term is dropped (the plan demands each component earn its place).

Default smoothing parameters are frozen from the M3 tuning run (see
``validation/v3_evolution/tune.py``) on a window disjoint from and strictly
before the V3 evaluation weeks.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

# Frozen by validation/v3_evolution/tune.py on the tuning window (Saturdays
# 2022-07-02 .. 2023-12-30, disjoint from and before the V3 evaluation weeks).
# Grid: alpha {0.1..0.9} x beta {0.0..0.5}. Share series: best mean weekly MAE
# 0.010089 at (0.6, 0.1) vs persistence 0.010508. Card series: best 0.081551
# at (0.6, 0.1) vs persistence 0.082756. Both optima are interior.
DEFAULT_SHARE_ALPHA = 0.6
DEFAULT_SHARE_BETA = 0.1
DEFAULT_CARD_ALPHA = 0.6
DEFAULT_CARD_BETA = 0.1


def holt_forecast(y: np.ndarray, alpha: float, beta: float) -> float:
    """One-step-ahead Holt forecast for a single series (1-D array, oldest
    first). Returns y_0 for a 1-point series; NaN for an empty one."""
    n = len(y)
    if n == 0:
        return float("nan")
    if n == 1:
        return float(y[0])
    level = float(y[0])
    trend = float(y[1]) - float(y[0])
    for t in range(1, n):
        prev_level = level
        level = alpha * float(y[t]) + (1.0 - alpha) * (level + trend)
        trend = beta * (level - prev_level) + (1.0 - beta) * trend
    return level + trend


def holt_forecast_panel(panel: np.ndarray, alpha: float, beta: float) -> np.ndarray:
    """One-step forecasts for a panel (n_series x n_steps), vectorized across
    series. Columns are time steps, oldest first; every series must be fully
    observed (absent entities carry literal zeros, which is their true level)."""
    n_series, n_steps = panel.shape
    if n_steps == 0:
        return np.full(n_series, np.nan)
    if n_steps == 1:
        return panel[:, 0].astype(float)
    level = panel[:, 0].astype(float)
    trend = panel[:, 1].astype(float) - level
    for t in range(1, n_steps):
        prev_level = level
        level = alpha * panel[:, t] + (1.0 - alpha) * (level + trend)
        trend = beta * (level - prev_level) + (1.0 - beta) * trend
    return level + trend


def holt_forecast_path(panel: np.ndarray, alpha: float, beta: float) -> np.ndarray:
    """One-step forecast made at every step, for a panel (n_series x n_steps):
    out[:, t] is the forecast of column t computed from columns [0, t) — the
    walk-forward residual machinery in one recursive pass. out[:, 0] is NaN
    (nothing to forecast from) and out[:, 1] is the 1-point forecast y_0."""
    n_series, n_steps = panel.shape
    out = np.full((n_series, n_steps), np.nan)
    if n_steps < 2:
        return out
    out[:, 1] = panel[:, 0]
    level = panel[:, 0].astype(float)
    trend = panel[:, 1].astype(float) - level
    for t in range(1, n_steps):
        prev_level = level
        level = alpha * panel[:, t] + (1.0 - alpha) * (level + trend)
        trend = beta * (level - prev_level) + (1.0 - beta) * trend
        if t + 1 < n_steps:
            out[:, t + 1] = level + trend
    return out


@dataclass(frozen=True)
class CouplingFit:
    """OLS fit of residual = gamma * x + eps (no intercept), with the
    frequentist diagnostics V3.2 reports."""

    gamma: float
    stderr: float
    t_stat: float
    n: int

    @property
    def significant(self) -> bool:
        """|t| >= 1.96 — the conventional 5% two-sided threshold."""
        return abs(self.t_stat) >= 1.96


def fit_coupling(residuals: np.ndarray, x: np.ndarray) -> CouplingFit:
    """Closed-form no-intercept OLS of Holt residuals on the lagged strength
    regressor. Returns gamma=0 (t=0) when there is no usable variation."""
    mask = np.isfinite(residuals) & np.isfinite(x)
    r = residuals[mask]
    xx = x[mask]
    sxx = float(np.dot(xx, xx))
    n = len(r)
    if n < 3 or sxx <= 0.0:
        return CouplingFit(gamma=0.0, stderr=float("inf"), t_stat=0.0, n=n)
    gamma = float(np.dot(xx, r)) / sxx
    resid = r - gamma * xx
    dof = n - 1
    sigma2 = float(np.dot(resid, resid)) / dof
    stderr = (sigma2 / sxx) ** 0.5
    t_stat = gamma / stderr if stderr > 0 else 0.0
    return CouplingFit(gamma=gamma, stderr=stderr, t_stat=t_stat, n=n)


def coupled_forecast(
    holt: np.ndarray, last_level: np.ndarray, strength: np.ndarray, gamma: float
) -> np.ndarray:
    """Holt forecast adjusted by the flocking term; series with no strength
    signal (NaN) fall back to the pure Holt forecast."""
    adj = gamma * last_level * (strength - 0.5)
    return holt + np.where(np.isfinite(adj), adj, 0.0)


def coupling_regressor(last_level: np.ndarray, strength: np.ndarray) -> np.ndarray:
    """The x used both in fitting and forecasting: s_last * (strength - 0.5).
    NaN where the strength signal is missing."""
    return last_level * (strength - 0.5)
