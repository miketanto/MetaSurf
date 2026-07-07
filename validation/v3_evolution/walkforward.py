"""Weekly walk-forward machinery for the V3 evolution suites.

Protocol (fixed before any evaluation ran, identical for model and baseline):

- Forecast week j uses only panel columns [0, j) plus the lagged-strength
  regressor whose week-j value is itself computed from data strictly before
  Saturday j (Layer-2 fit cutoff), so nothing leaks by construction.
- Scored universe at week j (V3.1): archetypes holding >= 1% pooled share
  over the 8 weekends strictly before j — the entities a metagame page would
  actually list (~17-22 per week on the evaluation window). The universe is
  recomputed every week from training data only.
- Baseline: persistence — next weekend's value equals last weekend's.
- Card selection at week j (V3.3): among cards averaging >= 0.25 mainboard
  copies per deck over the 4 trailing weekends, the 20 with the largest
  absolute change between the trailing 4 and the 4 before that ("fastest
  moving", training data only). Selection travels with the walk-forward.
- Share forecasts are clamped to [0, 1] and copy forecasts to >= 0 for both
  model and baseline (persistence never violates either).
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from models.evolution import (
    coupling_regressor,
    fit_coupling,
    holt_forecast_path,
)

UNIVERSE_TRAILING_WEEKS = 8
UNIVERSE_MIN_SHARE = 0.01
CARD_TOP_K = 20
CARD_MIN_MEAN_COPIES = 0.25
CARD_TRAILING_WEEKS = 4


def universe_mask(counts: np.ndarray, j: int) -> np.ndarray:
    """Archetypes with >= UNIVERSE_MIN_SHARE pooled share over the trailing
    window strictly before column j."""
    lo = max(0, j - UNIVERSE_TRAILING_WEEKS)
    pooled = counts[:, lo:j].sum(axis=1)
    total = pooled.sum()
    if total <= 0:
        return np.zeros(counts.shape[0], dtype=bool)
    return pooled / total >= UNIVERSE_MIN_SHARE


@dataclass
class ShareWalkForward:
    eval_idx: list[int]
    universe_sizes: list[int]
    mae_model: list[float]
    mae_persistence: list[float]
    gamma_used: list[float]  # 0.0 when coupling disabled

    def mean_mae_model(self) -> float:
        return float(np.mean(self.mae_model))

    def mean_mae_persistence(self) -> float:
        return float(np.mean(self.mae_persistence))

    def improvement(self) -> float:
        """Relative MAE improvement of the model over persistence."""
        return 1.0 - self.mean_mae_model() / self.mean_mae_persistence()


def run_share_walkforward(
    shares: np.ndarray,
    counts: np.ndarray,
    strength: np.ndarray | None,
    eval_idx: list[int],
    alpha: float,
    beta: float,
    coupling_train_start: int = 0,
) -> ShareWalkForward:
    """Walk the evaluation week indexes. strength=None disables the coupling
    term (pure Holt); otherwise gamma is refit each week by expanding-window
    OLS on residual pairs from weeks [coupling_train_start, j)."""
    path = holt_forecast_path(shares, alpha, beta)
    residuals = shares - path  # residual[:, t] is defined where path is
    if strength is not None:
        x = np.full_like(shares, np.nan)
        x[:, 1:] = coupling_regressor(shares[:, :-1], strength[:, 1:])
    out = ShareWalkForward(
        eval_idx=[], universe_sizes=[], mae_model=[], mae_persistence=[], gamma_used=[]
    )
    for j in eval_idx:
        uni = universe_mask(counts, j)
        if not uni.any() or j < 1:
            continue
        holt_j = path[:, j]
        gamma = 0.0
        if strength is not None:
            pairs_r: list[np.ndarray] = []
            pairs_x: list[np.ndarray] = []
            for t in range(max(coupling_train_start, 1), j):
                uni_t = universe_mask(counts, t)
                if not uni_t.any():
                    continue
                pairs_r.append(residuals[uni_t, t])
                pairs_x.append(x[uni_t, t])
            if pairs_r:
                fit = fit_coupling(np.concatenate(pairs_r), np.concatenate(pairs_x))
                gamma = fit.gamma
            adj = gamma * x[:, j]
            forecast = holt_j + np.where(np.isfinite(adj), adj, 0.0)
        else:
            forecast = holt_j
        forecast = np.clip(forecast, 0.0, 1.0)
        persistence = shares[:, j - 1]
        actual = shares[:, j]
        out.eval_idx.append(j)
        out.universe_sizes.append(int(uni.sum()))
        out.mae_model.append(float(np.mean(np.abs(forecast[uni] - actual[uni]))))
        out.mae_persistence.append(float(np.mean(np.abs(persistence[uni] - actual[uni]))))
        out.gamma_used.append(gamma)
    return out


def collect_coupling_pairs(
    shares: np.ndarray,
    counts: np.ndarray,
    strength: np.ndarray,
    idx: list[int],
    alpha: float,
    beta: float,
) -> tuple[np.ndarray, np.ndarray]:
    """(residual, regressor) pairs over the given week indexes, universe-
    restricted per week — the V3.2 significance/stability input."""
    path = holt_forecast_path(shares, alpha, beta)
    residuals = shares - path
    x = np.full_like(shares, np.nan)
    x[:, 1:] = coupling_regressor(shares[:, :-1], strength[:, 1:])
    rs: list[np.ndarray] = []
    xs: list[np.ndarray] = []
    for t in idx:
        if t < 1:
            continue
        uni = universe_mask(counts, t)
        if not uni.any():
            continue
        rs.append(residuals[uni, t])
        xs.append(x[uni, t])
    if not rs:
        return np.empty(0), np.empty(0)
    return np.concatenate(rs), np.concatenate(xs)


@dataclass
class CardWalkForward:
    eval_idx: list[int]
    mae_model: list[float]
    mae_persistence: list[float]

    def mean_mae_model(self) -> float:
        return float(np.mean(self.mae_model))

    def mean_mae_persistence(self) -> float:
        return float(np.mean(self.mae_persistence))

    def improvement(self) -> float:
        return 1.0 - self.mean_mae_model() / self.mean_mae_persistence()


def fastest_moving_cards(values: np.ndarray, j: int) -> np.ndarray:
    """Indexes of the CARD_TOP_K fastest-moving eligible cards at week j,
    from training data only. Deterministic tie-break by row order."""
    w = CARD_TRAILING_WEEKS
    if j < 2 * w:
        return np.empty(0, dtype=int)
    recent = values[:, j - w : j].mean(axis=1)
    prev = values[:, j - 2 * w : j - w].mean(axis=1)
    eligible = recent >= CARD_MIN_MEAN_COPIES
    if not eligible.any():
        return np.empty(0, dtype=int)
    movement = np.where(eligible, np.abs(recent - prev), -1.0)
    order = np.argsort(-movement, kind="stable")
    top = order[: CARD_TOP_K]
    return top[movement[top] > -1.0]


def run_card_walkforward(
    values: np.ndarray, eval_idx: list[int], alpha: float, beta: float
) -> CardWalkForward:
    path = holt_forecast_path(values, alpha, beta)
    out = CardWalkForward(eval_idx=[], mae_model=[], mae_persistence=[])
    for j in eval_idx:
        sel = fastest_moving_cards(values, j)
        if len(sel) == 0 or j < 1:
            continue
        forecast = np.clip(path[sel, j], 0.0, None)
        persistence = values[sel, j - 1]
        actual = values[sel, j]
        out.eval_idx.append(j)
        out.mae_model.append(float(np.mean(np.abs(forecast - actual))))
        out.mae_persistence.append(float(np.mean(np.abs(persistence - actual))))
    return out
