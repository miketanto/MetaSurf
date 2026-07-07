"""EXPLORATORY M3.5 prototype — replicator-dynamics share forecast.

NOT a validated V3.1 result. Purpose: a cheap go/no-go on whether evolving
shares through the Layer-2 matchup matrix beats persistence at all, before
committing to a formal M3.5 milestone with a fresh pre-registered split.

Holdout hygiene (documented, imperfect on purpose): the single hyperparameter
eta is tuned ONLY on the tuning window (2022-07-02 .. 2023-12-30, disjoint
from and before the evaluation window), then run once on the evaluation window
(2024-01-06 .. 2025-03-29) — the SAME window V3.1 used. The eval window is
therefore no longer pristine (Holt V3.1 already saw it), so this number is a
directional signal, not an acceptance-gate result. If it is promising, the
proposal asks for a clean pre-registered evaluation on withheld data.

Protocol matches V3.1 exactly so the numbers are directly comparable:
forecast week j's share-of-total from week j-1's shares and the matchup matrix
fitted on matches strictly before Saturday j; score MAE on the trailing-1%
universe(j) (training-only). eta=0 is identically persistence.

Run: python -m validation.v3_evolution.replicator_explore
"""

from __future__ import annotations

import datetime as dt

import numpy as np
import psycopg

from db.connection import database_url
from models.evolution import replicator_step
from models.evolution.model import DEFAULT_SHARE_ALPHA, DEFAULT_SHARE_BETA
from models.winrate import WinrateModel
from validation.v2_winrates.data import load_match_data, n_archetype_slots
from validation.v3_evolution.data import load_share_panel
from validation.v3_evolution.run import EVAL_FIRST_SATURDAY, EVAL_LAST_SATURDAY
from validation.v3_evolution.tune import (
    PANEL_FIRST_SATURDAY,
    PANEL_LAST_SATURDAY,
    TUNING_FIRST_SATURDAY,
    TUNING_LAST_SATURDAY,
)
from validation.v3_evolution.walkforward import (
    run_share_walkforward,
    universe_mask,
)

ETA_GRID = (0.0, 0.5, 1.0, 2.0, 4.0, 6.0, 8.0, 12.0, 16.0, 24.0)


def build_matchup_tensor(
    conn: psycopg.Connection, entity_ids: np.ndarray, saturdays: list[dt.date]
) -> np.ndarray:
    """(n_weeks, n, n) matchup matrices; week j fitted on matches strictly
    before saturdays[j] (no leakage). W[j, a, b] = P(a beats b)."""
    data, names, _stats = load_match_data(conn, "modern")
    slots = n_archetype_slots(names)
    model = WinrateModel()
    n = len(entity_ids)
    ai = np.repeat(entity_ids, n)
    bi = np.tile(entity_ids, n)
    tensor = np.empty((len(saturdays), n, n))
    for j, sat in enumerate(saturdays):
        post = model.fit(data, sat.toordinal(), slots)
        tensor[j] = post.match_prob(ai, bi).reshape(n, n)
    return tensor


def eval_eta(
    shares: np.ndarray,
    counts: np.ndarray,
    tensor: np.ndarray,
    idx: list[int],
    eta: float,
) -> tuple[float, float, int]:
    """Mean weekly MAE of the replicator forecast and of persistence over the
    given week indexes; plus weeks the model wins."""
    maes_model: list[float] = []
    maes_pers: list[float] = []
    wins = 0
    for j in idx:
        uni = universe_mask(counts, j)
        if not uni.any() or j < 1:
            continue
        x_prev = shares[:, j - 1]
        forecast = replicator_step(x_prev, tensor[j], eta)
        actual = shares[:, j]
        m = float(np.mean(np.abs(forecast[uni] - actual[uni])))
        p = float(np.mean(np.abs(x_prev[uni] - actual[uni])))
        maes_model.append(m)
        maes_pers.append(p)
        wins += int(m < p)
    return float(np.mean(maes_model)), float(np.mean(maes_pers)), wins


def main() -> None:
    with psycopg.connect(database_url()) as conn:
        panel, _totals = load_share_panel(
            conn, "modern", PANEL_FIRST_SATURDAY, PANEL_LAST_SATURDAY
        )
        tensor = build_matchup_tensor(conn, panel.entity_ids, panel.saturdays)
    assert panel.counts is not None
    sats = panel.saturdays
    tune_idx = [i for i, s in enumerate(sats)
                if TUNING_FIRST_SATURDAY <= s <= TUNING_LAST_SATURDAY]
    eval_idx = [i for i, s in enumerate(sats)
                if EVAL_FIRST_SATURDAY <= s <= EVAL_LAST_SATURDAY]

    print(f"panel {panel.values.shape}; tune weeks {len(tune_idx)},"
          f" eval weeks {len(eval_idx)}")
    print("\n== tuning window (eta selected HERE only) ==")
    tuning_scores = []
    for eta in ETA_GRID:
        mae, pers, wins = eval_eta(panel.values, panel.counts, tensor, tune_idx, eta)
        tuning_scores.append((mae, eta))
        print(f"  eta={eta:5.1f}  MAE {mae:.6f}  (persistence {pers:.6f},"
              f" impr {1 - mae / pers:+.2%}, model wins {wins}/{len(tune_idx)})")
    tuning_scores.sort()
    best_eta = tuning_scores[0][1]
    print(f"  -> frozen eta = {best_eta}")

    print("\n== evaluation window (single run at frozen eta) ==")
    mae, pers, wins = eval_eta(panel.values, panel.counts, tensor, eval_idx, best_eta)
    print(f"  replicator (eta={best_eta}): MAE {mae:.6f}"
          f"  impr vs persistence {1 - mae / pers:+.2%}"
          f"  wins {wins}/{len(eval_idx)}")

    holt = run_share_walkforward(
        panel.values, panel.counts, None, eval_idx,
        DEFAULT_SHARE_ALPHA, DEFAULT_SHARE_BETA,
    )
    print(f"  Holt V3.1 baseline:       MAE {holt.mean_mae_model():.6f}"
          f"  impr vs persistence {holt.improvement():+.2%}")
    print(f"  persistence:              MAE {pers:.6f}")

    print("\n== full eta curve on eval (diagnostic, NOT used for selection) ==")
    for eta in ETA_GRID:
        m, p, w = eval_eta(panel.values, panel.counts, tensor, eval_idx, eta)
        print(f"  eta={eta:5.1f}  MAE {m:.6f}  impr {1 - m / p:+.2%}"
              f"  wins {w}/{len(eval_idx)}")


if __name__ == "__main__":
    main()
