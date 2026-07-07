"""V3.1-V3.3 validation suites (plan §5 Layer 3). Every number in the emitted
report is computed here at run time; the full computation executes twice and
the serialized metrics must be byte-identical (determinism gate).

V3.1 — meta-share forecast. Weekly walk-forward over the evaluation weeks
(Saturdays 2024-01-06 .. 2025-03-29, 15 months >= the required 6): forecast
each universe archetype's next-weekend share with Holt smoothing plus the
lagged-winrate coupling term (gamma refit each week on expanding training
residuals), score MAE against the persistence baseline ("same as last
weekend"). Target: >= 10% mean-MAE improvement. The plan explicitly allows
the target to fail — "persistence is hard to beat" — in which case the
product positioning verdict is DESCRIPTIVE TRENDS, not prediction; the
verdict is decided by these numbers either way (plan §7 M3 DoD).

V3.2 — flocking hypothesis. The coupling coefficient gamma (share residual
regressed on last-weekend share x lagged latent winrate deviation) is
reported with its standard error and t-statistic on the tuning window, each
evaluation half, and the pooled window. The term is significant and stable
only if it keeps one sign and |t| >= 1.96 everywhere; otherwise the plan says
drop it.

V3.3 — tech drift. Same walk-forward for the 20 fastest-moving cards
(selected each week from training data only, >= 0.25 trailing mean mainboard
copies): forecast next weekend's format-wide mean copies per deck, MAE vs
persistence, >= 10% target.

Smoothing parameters were frozen on the disjoint, earlier tuning window (see
tune.py) before this suite ran. The suite's exit code reflects computation
integrity (determinism); forecast-target misses are reported as FAIL verdicts
in the committed report and surfaced to the owner — they are a documented
acceptable outcome for this layer, not a silent pass.
"""

from __future__ import annotations

import datetime as dt
from typing import Any

import numpy as np
import psycopg

from models.evolution import (
    DEFAULT_CARD_ALPHA,
    DEFAULT_CARD_BETA,
    DEFAULT_SHARE_ALPHA,
    DEFAULT_SHARE_BETA,
    fit_coupling,
)
from validation.v3_evolution.data import (
    latent_winrate_panel,
    load_card_copies_panel,
    load_share_panel,
)
from validation.v3_evolution.tune import (
    PANEL_FIRST_SATURDAY,
    PANEL_LAST_SATURDAY,
    TUNING_FIRST_SATURDAY,
    TUNING_LAST_SATURDAY,
    tuning_indexes,
)
from validation.v3_evolution.walkforward import (
    collect_coupling_pairs,
    run_card_walkforward,
    run_share_walkforward,
)

EVAL_FIRST_SATURDAY = dt.date(2024, 1, 6)
EVAL_LAST_SATURDAY = dt.date(2025, 3, 29)
IMPROVEMENT_TARGET = 0.10


def eval_indexes(saturdays: list[dt.date]) -> list[int]:
    return [
        i for i, s in enumerate(saturdays)
        if EVAL_FIRST_SATURDAY <= s <= EVAL_LAST_SATURDAY
    ]


def run_v31(
    shares: np.ndarray,
    counts: np.ndarray,
    strength: np.ndarray,
    saturdays: list[dt.date],
) -> dict[str, Any]:
    idx = eval_indexes(saturdays)
    tune_start = tuning_indexes(saturdays)[0]
    full = run_share_walkforward(
        shares, counts, strength, idx,
        DEFAULT_SHARE_ALPHA, DEFAULT_SHARE_BETA, coupling_train_start=tune_start,
    )
    holt_only = run_share_walkforward(
        shares, counts, None, idx, DEFAULT_SHARE_ALPHA, DEFAULT_SHARE_BETA
    )
    weeks_model_better = sum(
        1 for m, p in zip(full.mae_model, full.mae_persistence, strict=True) if m < p
    )
    return {
        "weeks": len(full.eval_idx),
        "universe_min": int(min(full.universe_sizes)),
        "universe_max": int(max(full.universe_sizes)),
        "mae_model": full.mean_mae_model(),
        "mae_holt_only": holt_only.mean_mae_model(),
        "mae_persistence": full.mean_mae_persistence(),
        "improvement": full.improvement(),
        "improvement_holt_only": holt_only.improvement(),
        "weeks_model_better": weeks_model_better,
        "gamma_first": full.gamma_used[0],
        "gamma_last": full.gamma_used[-1],
        "weekly": [
            (saturdays[j].isoformat(), u, m, p)
            for j, u, m, p in zip(
                full.eval_idx, full.universe_sizes,
                full.mae_model, full.mae_persistence, strict=True,
            )
        ],
        "pass": full.improvement() >= IMPROVEMENT_TARGET,
    }


def run_v32(
    shares: np.ndarray,
    counts: np.ndarray,
    strength: np.ndarray,
    saturdays: list[dt.date],
) -> dict[str, Any]:
    idx_eval = eval_indexes(saturdays)
    half = len(idx_eval) // 2
    windows = {
        "tuning (2022-07..2023-12)": tuning_indexes(saturdays),
        "eval first half": idx_eval[:half],
        "eval second half": idx_eval[half:],
        "pooled (tuning+eval)": tuning_indexes(saturdays) + idx_eval,
    }
    rows = {}
    for name, idx in windows.items():
        r, x = collect_coupling_pairs(
            shares, counts, strength, idx, DEFAULT_SHARE_ALPHA, DEFAULT_SHARE_BETA
        )
        fit = fit_coupling(r, x)
        rows[name] = {
            "gamma": fit.gamma,
            "stderr": fit.stderr,
            "t": fit.t_stat,
            "n": fit.n,
            "significant": fit.significant,
        }
    signs = {np.sign(v["gamma"]) for v in rows.values()}
    all_significant = all(v["significant"] for v in rows.values())
    return {
        "windows": rows,
        "same_sign": len(signs) == 1,
        "all_significant": all_significant,
        "keep_term": len(signs) == 1 and all_significant,
    }


def run_v33(card_values: np.ndarray, saturdays: list[dt.date]) -> dict[str, Any]:
    idx = eval_indexes(saturdays)
    res = run_card_walkforward(card_values, idx, DEFAULT_CARD_ALPHA, DEFAULT_CARD_BETA)
    weeks_model_better = sum(
        1 for m, p in zip(res.mae_model, res.mae_persistence, strict=True) if m < p
    )
    return {
        "weeks": len(res.eval_idx),
        "mae_model": res.mean_mae_model(),
        "mae_persistence": res.mean_mae_persistence(),
        "improvement": res.improvement(),
        "weeks_model_better": weeks_model_better,
        "pass": res.improvement() >= IMPROVEMENT_TARGET,
    }


def format_metrics(v31: dict, v32: dict, v33: dict) -> str:
    """Deterministic serialization compared byte-for-byte across two runs."""
    lines = [
        f"v31 weeks={v31['weeks']} mae={v31['mae_model']:.8f}"
        f" holt={v31['mae_holt_only']:.8f} pers={v31['mae_persistence']:.8f}"
        f" impr={v31['improvement']:.8f}",
        f"v33 weeks={v33['weeks']} mae={v33['mae_model']:.8f}"
        f" pers={v33['mae_persistence']:.8f} impr={v33['improvement']:.8f}",
    ]
    for name, v in v32["windows"].items():
        lines.append(
            f"v32 {name} gamma={v['gamma']:.8f} se={v['stderr']:.8f}"
            f" t={v['t']:.6f} n={v['n']}"
        )
    for row in v31["weekly"]:
        lines.append(str(row))
    return "\n".join(lines)


def evaluate_all(conn: psycopg.Connection) -> tuple[dict, dict, dict, dict, str]:
    share_panel, totals = load_share_panel(
        conn, "modern", PANEL_FIRST_SATURDAY, PANEL_LAST_SATURDAY
    )
    card_panel = load_card_copies_panel(
        conn, "modern", PANEL_FIRST_SATURDAY, PANEL_LAST_SATURDAY
    )
    strength = latent_winrate_panel(
        conn, "modern", share_panel.entity_ids, share_panel.saturdays
    )
    assert share_panel.counts is not None
    v31 = run_v31(share_panel.values, share_panel.counts, strength, share_panel.saturdays)
    v32 = run_v32(share_panel.values, share_panel.counts, strength, share_panel.saturdays)
    v33 = run_v33(card_panel.values, card_panel.saturdays)
    dq = {
        "panel_weeks": share_panel.n_weeks,
        "panel_first": share_panel.saturdays[0].isoformat(),
        "panel_last": share_panel.saturdays[-1].isoformat(),
        "archetype_series": len(share_panel.entity_ids),
        "card_series": len(card_panel.entity_ids),
        "weekend_decks_min": int(totals.min()),
        "weekend_decks_median": float(np.median(totals)),
        "zero_weekends": int((totals == 0).sum()),
        "tuning_window": f"{TUNING_FIRST_SATURDAY} .. {TUNING_LAST_SATURDAY}",
    }
    return v31, v32, v33, dq, format_metrics(v31, v32, v33)
