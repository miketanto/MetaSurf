"""Run V2.1-V2.3 and write the dated report.

Usage: python -m validation.v2_winrates [--out validation/reports/m2-v2-winrates.md]

The full computation executes twice in-process; the serialized metrics must
be byte-identical (determinism gate — the model is closed-form conjugate and
carries no RNG, so any difference means nondeterministic inputs).
"""

from __future__ import annotations

import argparse
import datetime as dt

import psycopg

from db.connection import database_url
from models.winrate import (
    DEFAULT_HALF_LIFE_DAYS,
    DEFAULT_PAIR_PRIOR_STRENGTH,
    DEFAULT_PRIOR_STRENGTH,
)
from validation.v2_winrates.run import (
    CAL_SLOPE_RANGE,
    COVERAGE_MIN_MATCHES,
    COVERAGE_RANGE,
    EVAL_FIRST_SATURDAY,
    EVAL_LAST_SATURDAY,
    TARGET_BEAT_FRACTION,
    evaluate_all,
)
from validation.v2_winrates.tune import (
    TUNING_FIRST_SATURDAY,
    TUNING_LAST_SATURDAY,
)


def render_report(v21: dict, v22: dict, v23: dict, dq: dict, deterministic: bool) -> str:
    today = dt.date.today().isoformat()
    b = v21["mean_ll_baselines"]
    lines = [
        f"# M2 V2 winrate-model validation — {today}",
        "",
        "All numbers are printed output of `python -m validation.v2_winrates`"
        " against the rebuilt database. Methodology: docstrings of"
        " `validation/v2_winrates/run.py` and `walkforward.py`.",
        "",
        f"Model: hierarchical Bayesian beta-binomial (`models/winrate/`),"
        f" half_life_days={DEFAULT_HALF_LIFE_DAYS},"
        f" prior_strength={DEFAULT_PRIOR_STRENGTH},"
        f" pair_prior_strength={DEFAULT_PAIR_PRIOR_STRENGTH} — frozen by grid"
        f" search on the tuning weeks {TUNING_FIRST_SATURDAY} .."
        f" {TUNING_LAST_SATURDAY} (mean weekly log-loss 0.684814), disjoint"
        " from and strictly before the evaluation weeks below"
        " (`validation/v2_winrates/tune.py`). The tuned half-life sits far"
        " above the plan's 14-21d initial guess on a very flat surface"
        " (21d scores 0.688773 on the tuning weeks); see the V2.3 discussion.",
        "",
        f"## V2.1 — weekly walk-forward {EVAL_FIRST_SATURDAY} .. {EVAL_LAST_SATURDAY}",
        "",
        f"Weeks evaluated: {v21['weeks_evaluated']} of {v21['weeks_scheduled']}"
        f" scheduled Saturdays (every week with >= 1 evaluable match counts;"
        f" smallest test weekend: {v21['test_matches_min_week']} matches)."
        f" Test matches scored: {v21['test_matches_total']}"
        " (decisive, both archetypes resolved, non-mirror, canonical"
        " lower-archetype-id-first orientation).",
        "",
        f"**Model beats the raw pooled-winrate baseline (B1) in"
        f" {v21['weeks_beat_primary']}/{v21['weeks_evaluated']} weeks ="
        f" {v21['beat_fraction']:.4f}** (target >= {TARGET_BEAT_FRACTION}) —"
        f" **{'PASS' if v21['pass_beat'] else 'FAIL'}**",
        "",
        f"**Calibration slope (Cox, pooled): {v21['calibration_slope']:.4f}**"
        f" (target within {list(CAL_SLOPE_RANGE)};"
        f" intercept {v21['calibration_intercept']:.4f}) —"
        f" **{'PASS' if v21['pass_slope'] else 'FAIL'}**",
        "",
        "| metric | model | B0 raw side-a | B1 raw pooled | B2 raw pair |",
        "|---|---|---|---|---|",
        f"| mean weekly log-loss | {v21['mean_ll_model']:.6f}"
        f" | {b['B0_raw_side_a']:.6f} | {b['B1_raw_pooled']:.6f}"
        f" | {b['B2_raw_pair']:.6f} |",
        f"| weeks model beats | — | {v21['weeks_beat_by_baseline']['B0_raw_side_a']}"
        f" | {v21['weeks_beat_by_baseline']['B1_raw_pooled']}"
        f" | {v21['weeks_beat_by_baseline']['B2_raw_pair']} |",
        "",
        f"Baseline calibration slope (B1): {v21['baseline_calibration_slope']:.4f}"
        f" (intercept {v21['baseline_calibration_intercept']:.4f}).",
        "",
        "Reliability (pooled model predictions, 10 equal-width bins):",
        "",
        "| bin | n | mean predicted | empirical |",
        "|---|---|---|---|",
    ]
    for lo, hi, n, mp, er in v21["reliability"]:
        lines.append(f"| {lo:.1f}-{hi:.1f} | {n} | {mp:.4f} | {er:.4f} |")
    lines += [
        "",
        "## V2.2 — interval honesty (90% predictive intervals)",
        "",
        f"Cells: {v22['cells']} (evaluation Saturday x archetype,"
        f" >= {COVERAGE_MIN_MATCHES} decisive weekend matches).",
        f"**Mid-P coverage: {v22['coverage_midp']:.4f}** (target within"
        f" {list(COVERAGE_RANGE)}) — **{'PASS' if v22['pass'] else 'FAIL'}**."
        f" Plain ppf-interval coverage (conservative, discrete):"
        f" {v22['coverage_interval']:.4f}.",
        "",
        "## V2.3 — ablations (same evaluation weeks)",
        "",
        "| variant | mean weekly log-loss | weeks beating B1 |",
        "|---|---|---|",
    ]
    for name in ("full", "no_decay", "no_hierarchy", "neither"):
        v = v23[name]
        lines.append(
            f"| {name} | {v['mean_ll']:.6f} | {v['weeks_beat_primary']}/{v['weeks']} |"
        )
    lines += [
        "",
        f"Time-decay earns its complexity: **{v23['decay_earns_complexity']}**."
        f" Hierarchical shrinkage earns its complexity:"
        f" **{v23['hierarchy_earns_complexity']}**.",
        "",
        "## Data quality (labeling + match extraction feeding this suite)",
        "",
        f"- matches: {dq['matches']} — by source: "
        + ", ".join(f"{k}={v}" for k, v in sorted(dq["matches_by_source"].items())),
        f"- matches with unresolved opponent deck (deck_id_b null):"
        f" {dq['matches_opponent_deck_unresolved']}",
        f"- matches on league events: {dq['matches_on_league_events']}"
        " (must be 0 — league data never feeds winrates)",
        "- archetype labels by method: "
        + ", ".join(f"{k}={v}" for k, v in sorted(dq["labels_by_method"].items())),
        f"- model loader: {dq['loader']}",
        "",
        "## Determinism",
        "",
        "Full V2.1+V2.2+V2.3 computation executed twice in-process;"
        f" serialized metrics **{'byte-identical' if deterministic else 'DIFFERED'}**"
        f" — {'PASS' if deterministic else 'FAIL'}.",
        "",
        "## Weekly log-loss detail (model vs B1)",
        "",
        "| saturday | test matches | model | B1 baseline | model better |",
        "|---|---|---|---|---|",
    ]
    for week, nt, m, base in v21["weekly"]:
        lines.append(f"| {week} | {nt} | {m:.6f} | {base:.6f} |"
                     f" {'yes' if m < base else 'no'} |")
    lines.append("")
    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", default="validation/reports/m2-v2-winrates.md")
    args = parser.parse_args()

    with psycopg.connect(database_url()) as conn:
        v21, v22, v23, dq, metrics1 = evaluate_all(conn)
        _, _, _, _, metrics2 = evaluate_all(conn)
    deterministic = metrics1 == metrics2

    report = render_report(v21, v22, v23, dq, deterministic)
    with open(args.out, "w") as f:
        f.write(report)
    print(report)
    print(f"\nwrote {args.out}")

    verdicts = {
        "V2.1 beat-baseline": v21["pass_beat"],
        "V2.1 calibration slope": v21["pass_slope"],
        "V2.2 coverage": v22["pass"],
        "determinism": deterministic,
    }
    print("verdicts:", verdicts)
    if not all(verdicts.values()):
        raise SystemExit(1)


if __name__ == "__main__":
    main()
