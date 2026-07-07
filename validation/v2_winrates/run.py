"""V2.1-V2.3 validation suites (plan §5 Layer 2). Every number in the emitted
report is computed here at run time; the full computation executes twice and
the serialized metrics must be byte-identical (determinism gate).

V2.1 — calibration backtest. Weekly walk-forward over the evaluation weeks
(Saturdays 2024-01-06 .. 2025-03-29, 15 months; every week with at least one
evaluable match counts). Train on all matches strictly before each Saturday,
test on that weekend's decisive, both-resolved, non-mirror matches in
canonical (lower-archetype-id-first) orientation. Metrics: per-week log-loss
vs the raw pooled-winrate baseline (B1, see walkforward.py; B0/B2 reported
for reference) and the Cox calibration slope + reliability table over all
pooled predictions. Targets: beat B1 in >= 80% of weeks; slope in [0.9, 1.1].

V2.2 — interval honesty. For every (evaluation Saturday, archetype) cell with
>= 10 decisive weekend matches (counted from both sides of each match), the
model's beta-binomial 90% predictive interval for the cell's win count is
checked against the observed win count. Discrete intervals cannot carry
exactly 90% mass, so coverage is scored with the mid-P probability integral
transform (covered iff 0.05 <= CDF(x-1) + 0.5*pmf(x) <= 0.95); the plain
ppf-interval coverage is reported alongside. Target: 85-95%.

V2.3 — ablations. Mean weekly log-loss of the full model vs no-decay
(half_life=None), no-hierarchy (flat Beta(1,1) priors at both levels), and
neither, over the same evaluation weeks. Shrinkage and decay must each earn
their complexity (full model strictly best on mean log-loss) or be removed.

Drawn matches train the model (half win / half loss) but are never scored.
Hyperparameters were frozen on the disjoint, earlier tuning window (see
tune.py) before this suite ran on the evaluation weeks.
"""

from __future__ import annotations

import datetime as dt
from collections import defaultdict
from typing import Any

import numpy as np
import psycopg
from scipy import stats as sps

from models.winrate import MatchData, WinrateModel
from validation.v2_winrates.data import LoadStats, load_match_data, n_archetype_slots
from validation.v2_winrates.walkforward import (
    calibration_slope,
    reliability_table,
    run_walkforward,
    saturdays,
)

EVAL_FIRST_SATURDAY = dt.date(2024, 1, 6)
EVAL_LAST_SATURDAY = dt.date(2025, 3, 29)
PRIMARY_BASELINE = "B1_raw_pooled"
TARGET_BEAT_FRACTION = 0.80
CAL_SLOPE_RANGE = (0.9, 1.1)
COVERAGE_RANGE = (0.85, 0.95)
COVERAGE_MIN_MATCHES = 10


def run_v21(data: MatchData, n: int) -> dict[str, Any]:
    cutoffs = saturdays(EVAL_FIRST_SATURDAY, EVAL_LAST_SATURDAY)
    res = run_walkforward(data, n, cutoffs, WinrateModel())
    n_weeks = len(res.weeks)
    beat = res.weeks_beating(PRIMARY_BASELINE)
    slope, intercept = calibration_slope(res.pooled_y, res.pooled_p_model)
    b_slope, b_intercept = calibration_slope(res.pooled_y, res.pooled_p_baseline)
    return {
        "weeks_scheduled": len(cutoffs),
        "weeks_evaluated": n_weeks,
        "test_matches_total": int(sum(res.n_test)),
        "test_matches_min_week": int(min(res.n_test)),
        "weeks_beat_primary": beat,
        "beat_fraction": beat / n_weeks,
        "weeks_beat_by_baseline": {
            name: res.weeks_beating(name) for name in sorted(res.baseline_ll)
        },
        "mean_ll_model": float(np.mean(res.model_ll)),
        "mean_ll_baselines": {
            name: float(np.mean(ll)) for name, ll in sorted(res.baseline_ll.items())
        },
        "calibration_slope": slope,
        "calibration_intercept": intercept,
        "baseline_calibration_slope": b_slope,
        "baseline_calibration_intercept": b_intercept,
        "reliability": reliability_table(res.pooled_y, res.pooled_p_model),
        "weekly": [
            (w.isoformat(), nt, m, res.baseline_ll[PRIMARY_BASELINE][i])
            for i, (w, nt, m) in enumerate(
                zip(res.weeks, res.n_test, res.model_ll, strict=True)
            )
        ],
        "pass_beat": beat / n_weeks >= TARGET_BEAT_FRACTION,
        "pass_slope": CAL_SLOPE_RANGE[0] <= slope <= CAL_SLOPE_RANGE[1],
    }


def run_v22(data: MatchData, n: int) -> dict[str, Any]:
    model = WinrateModel()
    cells = 0
    covered_midp = 0
    covered_interval = 0
    for saturday in saturdays(EVAL_FIRST_SATURDAY, EVAL_LAST_SATURDAY):
        sat = saturday.toordinal()
        in_weekend = (data.day == sat) | (data.day == sat + 1)
        decisive = data.win_frac != 0.5
        mask = in_weekend & decisive
        if not mask.any():
            continue
        post = model.fit(data, sat, n)
        # per-archetype weekend record, counted from both sides of each match
        wins: dict[int, int] = defaultdict(int)
        total: dict[int, int] = defaultdict(int)
        for a, b, y in zip(data.side_a[mask], data.side_b[mask], data.win_frac[mask],
                           strict=True):
            total[int(a)] += 1
            wins[int(a)] += int(y == 1.0)
            if b >= 0:
                total[int(b)] += 1
                wins[int(b)] += int(y == 0.0)
        for arch in sorted(total):
            n_i = total[arch]
            if n_i < COVERAGE_MIN_MATCHES:
                continue
            x = wins[arch]
            alpha = float(post.arch_alpha[arch])
            beta = float(post.arch_beta[arch])
            u = sps.betabinom.cdf(x - 1, n_i, alpha, beta) + 0.5 * sps.betabinom.pmf(
                x, n_i, alpha, beta
            )
            cells += 1
            covered_midp += int(0.05 <= u <= 0.95)
            lo, hi = post.predictive_win_interval(arch, n_i, 0.90)
            covered_interval += int(lo <= x <= hi)
    return {
        "cells": cells,
        "coverage_midp": covered_midp / cells if cells else float("nan"),
        "coverage_interval": covered_interval / cells if cells else float("nan"),
        "pass": cells > 0
        and COVERAGE_RANGE[0] <= covered_midp / cells <= COVERAGE_RANGE[1],
    }


def run_v23(data: MatchData, n: int) -> dict[str, Any]:
    cutoffs = saturdays(EVAL_FIRST_SATURDAY, EVAL_LAST_SATURDAY)
    variants = {
        "full": WinrateModel(),
        "no_decay": WinrateModel(half_life_days=None),
        "no_hierarchy": WinrateModel(hierarchical=False),
        "neither": WinrateModel(half_life_days=None, hierarchical=False),
    }
    out: dict[str, Any] = {}
    for name, model in variants.items():
        res = run_walkforward(data, n, cutoffs, model)
        out[name] = {
            "mean_ll": float(np.mean(res.model_ll)),
            "weeks_beat_primary": res.weeks_beating(PRIMARY_BASELINE),
            "weeks": len(res.weeks),
        }
    full = out["full"]["mean_ll"]
    out["decay_earns_complexity"] = full < out["no_decay"]["mean_ll"]
    out["hierarchy_earns_complexity"] = full < out["no_hierarchy"]["mean_ll"]
    return out


def dq_counts(conn: psycopg.Connection, load_stats: LoadStats) -> dict[str, Any]:
    with conn.cursor() as cur:
        cur.execute("SELECT count(*) FROM matches")
        (n_matches,) = cur.fetchone()  # type: ignore[misc]
        cur.execute(
            """
            SELECT e.source, count(*) FROM matches m
            JOIN events e ON e.id = m.event_id GROUP BY 1 ORDER BY 1
            """
        )
        by_source: dict[str, int] = dict(cur.fetchall())
        cur.execute("SELECT count(*) FROM matches WHERE deck_id_b IS NULL")
        (n_null_b,) = cur.fetchone()  # type: ignore[misc]
        cur.execute(
            """
            SELECT al.method, count(*) FROM archetype_labels al GROUP BY 1 ORDER BY 1
            """
        )
        labels_by_method: dict[str, int] = dict(cur.fetchall())
        cur.execute(
            """
            SELECT count(*) FROM matches m JOIN events e ON e.id = m.event_id
            WHERE e.event_type LIKE '%%league%%'
            """
        )
        (n_league,) = cur.fetchone()  # type: ignore[misc]
    return {
        "matches": n_matches,
        "matches_by_source": by_source,
        "matches_opponent_deck_unresolved": n_null_b,
        "matches_on_league_events": n_league,
        "labels_by_method": labels_by_method,
        "loader": load_stats.summary(),
    }


def format_metrics(v21: dict, v22: dict, v23: dict) -> str:
    """Deterministic serialization compared byte-for-byte across two runs."""
    lines = [
        f"weeks={v21['weeks_evaluated']}/{v21['weeks_scheduled']}"
        f" test_matches={v21['test_matches_total']}",
        f"beat={v21['weeks_beat_primary']} frac={v21['beat_fraction']:.6f}"
        f" mean_ll={v21['mean_ll_model']:.6f}",
        " ".join(f"{k}={v:.6f}" for k, v in sorted(v21["mean_ll_baselines"].items())),
        f"slope={v21['calibration_slope']:.6f}"
        f" intercept={v21['calibration_intercept']:.6f}",
        f"coverage_midp={v22['coverage_midp']:.6f}"
        f" coverage_interval={v22['coverage_interval']:.6f} cells={v22['cells']}",
    ]
    for name in ("full", "no_decay", "no_hierarchy", "neither"):
        lines.append(f"{name} mean_ll={v23[name]['mean_ll']:.6f}"
                     f" beat={v23[name]['weeks_beat_primary']}/{v23[name]['weeks']}")
    for week_row in v21["weekly"]:
        lines.append(str(week_row))
    return "\n".join(lines)


def evaluate_all(conn: psycopg.Connection) -> tuple[dict, dict, dict, dict, str]:
    data, names, load_stats = load_match_data(conn, "modern")
    n = n_archetype_slots(names)
    v21 = run_v21(data, n)
    v22 = run_v22(data, n)
    v23 = run_v23(data, n)
    dq = dq_counts(conn, load_stats)
    return v21, v22, v23, dq, format_metrics(v21, v22, v23)
