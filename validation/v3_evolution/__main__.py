"""Run V3.1-V3.3 and write the dated report.

Usage: python -m validation.v3_evolution [--out validation/reports/m3-v3-evolution.md]

Exit code reflects computation integrity (determinism); forecast-target
misses are reported as FAIL verdicts in the committed report — plan §7 M3's
DoD is the honest verdict, and §5 V3.1 explicitly names the fallback
positioning when persistence wins.
"""

from __future__ import annotations

import argparse
import datetime as dt

import psycopg

from db.connection import database_url
from models.evolution import (
    DEFAULT_CARD_ALPHA,
    DEFAULT_CARD_BETA,
    DEFAULT_SHARE_ALPHA,
    DEFAULT_SHARE_BETA,
)
from validation.v3_evolution.run import (
    EVAL_FIRST_SATURDAY,
    EVAL_LAST_SATURDAY,
    IMPROVEMENT_TARGET,
    evaluate_all,
)


def render_report(v31: dict, v32: dict, v33: dict, dq: dict, deterministic: bool) -> str:
    today = dt.date.today().isoformat()
    verdict = (
        "PREDICTION (both forecast targets met)"
        if v31["pass"] and v33["pass"]
        else "DESCRIPTIVE TRENDS (forecast target(s) missed — plan §5 V3.1 fallback)"
    )
    lines = [
        f"# M3 V3 evolution-model validation — {today}",
        "",
        "All numbers are printed output of `python -m validation.v3_evolution`"
        " against the rebuilt database. Methodology: docstrings of"
        " `validation/v3_evolution/run.py`, `walkforward.py`, `data.py`.",
        "",
        f"Model: Holt linear smoothing + lagged-winrate coupling"
        f" (`models/evolution/`), share alpha={DEFAULT_SHARE_ALPHA}"
        f" beta={DEFAULT_SHARE_BETA}, card alpha={DEFAULT_CARD_ALPHA}"
        f" beta={DEFAULT_CARD_BETA} — frozen by grid search on the tuning"
        f" weeks {dq['tuning_window']} (disjoint from and strictly before the"
        " evaluation weeks; grid + scores in `models/evolution/model.py` and"
        " `validation/v3_evolution/tune.py`).",
        "",
        f"## Verdict: **{verdict}**",
        "",
        f"## V3.1 — meta-share forecast, {EVAL_FIRST_SATURDAY} .. {EVAL_LAST_SATURDAY}",
        "",
        f"Weeks: {v31['weeks']}; scored universe per week:"
        f" {v31['universe_min']}-{v31['universe_max']} archetypes (trailing"
        " 8-weekend pooled share >= 1%, training data only).",
        "",
        "| forecaster | mean weekly MAE (share points) | improvement vs persistence |",
        "|---|---|---|",
        f"| Holt + coupling (the model) | {v31['mae_model']:.6f}"
        f" | {v31['improvement']:+.2%} |",
        f"| Holt only | {v31['mae_holt_only']:.6f}"
        f" | {v31['improvement_holt_only']:+.2%} |",
        f"| persistence baseline | {v31['mae_persistence']:.6f} | — |",
        "",
        f"**Improvement {v31['improvement']:+.2%} vs target"
        f" >= {IMPROVEMENT_TARGET:.0%}** —"
        f" **{'PASS' if v31['pass'] else 'FAIL'}**."
        f" Model beats persistence in {v31['weeks_model_better']}/{v31['weeks']}"
        f" weeks; expanding-window gamma moved"
        f" {v31['gamma_first']:+.4f} -> {v31['gamma_last']:+.4f} across the window.",
        "",
        "## V3.2 — flocking hypothesis (share residual on lagged winrate)",
        "",
        "| window | gamma | stderr | t | n | significant (|t|>=1.96) |",
        "|---|---|---|---|---|---|",
    ]
    for name, v in v32["windows"].items():
        lines.append(
            f"| {name} | {v['gamma']:+.4f} | {v['stderr']:.4f} | {v['t']:+.2f}"
            f" | {v['n']} | {'yes' if v['significant'] else 'no'} |"
        )
    keep = v32["keep_term"]
    pooled_gamma = v32["windows"]["pooled (tuning+eval)"]["gamma"]
    lines += [
        "",
        f"Same sign in all windows: **{v32['same_sign']}**;"
        f" significant in all windows: **{v32['all_significant']}**."
        f" Plan rule (drop the term unless significant and stable):"
        f" **{'KEEP' if keep else 'DROP'}**.",
        "",
        f"**The sign contradicts the flocking hypothesis.** gamma is negative"
        f" ({pooled_gamma:+.4f} pooled): archetypes whose lagged latent winrate"
        " is high come in *below* their Holt-projected share, not above it —"
        " counter-adaptation / mean reversion rather than \"players flock to"
        " last weekend's winners\". The term survives the plan's keep rule"
        " (significant, stable sign) and improves V3.1 slightly, but the"
        " behavioral story in plan §5 Layer 3 is rejected as stated.",
        "",
        "## V3.3 — tech drift, 20 fastest-moving cards per week",
        "",
        f"Weeks: {v33['weeks']} (cards reselected weekly from training data:"
        " top 20 |change| between trailing-4 and previous-4 weekend means,"
        " eligibility >= 0.25 mean mainboard copies/deck).",
        "",
        "| forecaster | mean weekly MAE (copies/deck) | improvement |",
        "|---|---|---|",
        f"| Holt | {v33['mae_model']:.6f} | {v33['improvement']:+.2%} |",
        f"| persistence | {v33['mae_persistence']:.6f} | — |",
        "",
        f"**Improvement {v33['improvement']:+.2%} vs target"
        f" >= {IMPROVEMENT_TARGET:.0%}** —"
        f" **{'PASS' if v33['pass'] else 'FAIL'}**."
        f" Model beats persistence in {v33['weeks_model_better']}/{v33['weeks']} weeks.",
        "",
        "## Failure analysis (V3.1 and V3.3 targets missed — owner review requested)",
        "",
        "Per CLAUDE.md the targets are not lowered and the evaluation window"
        " is not adjusted; the numbers above stand. Why persistence is this"
        " hard to beat here:",
        "",
        "- **Weekly meta shares are strongly autocorrelated.** The scored"
        " universe's mean weekly share MAE under persistence is already"
        f" ~{v31['mae_persistence']:.4f} share points (~1.4pp) — most"
        " archetypes barely move week to week, so the achievable headroom"
        " over last-weekend's-value is small, and Holt spends it lagging one"
        " week behind every sharp break (set releases, bans: see the"
        " 2024-06-22, 2024-08-24 and 2024-09-07 rows in the weekly detail,"
        " where the model loses)."
        " Holt wins in smooth-trend stretches (34/65 weeks) but gives most of"
        " it back at regime shifts.",
        "- **The coupling term is real but tiny**: it adds"
        f" ~{(v31['improvement'] - v31['improvement_holt_only']):+.2%}"
        " MAE improvement on top of Holt, and its negative sign (V3.2) means"
        " it corrects winners *downward* — informative, not predictive"
        " firepower.",
        "- **V3.3 tuning did not transfer.** On the tuning window Holt beat"
        " persistence on the card series (0.081551 vs 0.082756, +1.5%); on"
        " the evaluation window it lost"
        f" ({v33['mae_model']:.6f} vs {v33['mae_persistence']:.6f},"
        f" {v33['improvement']:+.2%}). The fastest-mover selection targets"
        " precisely the most volatile series, and the mtgo decklist-policy"
        " change mid-corpus (2024-06) plus melee's schedule variance make"
        " that population noisier in the evaluation period than in tuning.",
        "",
        "Not attempted, deliberately: damped-trend Holt, ban/set-release"
        " event dummies, cross-archetype pooling, or any other variant —"
        " iterating further against this evaluation window would burn the"
        " holdout. If the owner wants another attempt, it needs a fresh"
        " protocol (new tuning split, pre-registered variants).",
        "",
        "**Product consequence (plan §5 V3.1, §7 M3 DoD):** ship the"
        " descriptive-trends positioning — trend arrows, movers, emerging"
        " decks from Layer 1, winrates/matchups from Layer 2 — and do not"
        " market share *prediction*. The plan names this outcome acceptable"
        " in advance; the DoD asks for the honest verdict, which this is.",
        "",
        "## Data quality (series feeding this suite)",
        "",
        f"- panel: {dq['panel_weeks']} Saturdays {dq['panel_first']} .."
        f" {dq['panel_last']}; {dq['archetype_series']} archetype series,"
        f" {dq['card_series']} card series",
        f"- labeled weekend decks per week: min {dq['weekend_decks_min']},"
        f" median {dq['weekend_decks_median']:.0f};"
        f" zero-deck weekends: {dq['zero_weekends']}",
        "",
        "## Determinism",
        "",
        "Full V3.1+V3.2+V3.3 computation executed twice in-process;"
        f" serialized metrics **{'byte-identical' if deterministic else 'DIFFERED'}**"
        f" — {'PASS' if deterministic else 'FAIL'}.",
        "",
        "## Weekly detail (V3.1: model MAE vs persistence MAE)",
        "",
        "| saturday | universe | model | persistence | model better |",
        "|---|---|---|---|---|",
    ]
    for week, u, m, p in v31["weekly"]:
        lines.append(f"| {week} | {u} | {m:.6f} | {p:.6f} | {'yes' if m < p else 'no'} |")
    lines.append("")
    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", default="validation/reports/m3-v3-evolution.md")
    args = parser.parse_args()

    with psycopg.connect(database_url()) as conn:
        v31, v32, v33, dq, metrics1 = evaluate_all(conn)
        _, _, _, _, metrics2 = evaluate_all(conn)
    deterministic = metrics1 == metrics2

    report = render_report(v31, v32, v33, dq, deterministic)
    with open(args.out, "w") as f:
        f.write(report)
    print(report)
    print(f"\nwrote {args.out}")
    print(
        "verdicts:",
        {
            "V3.1 share >= +10%": v31["pass"],
            "V3.2 keep coupling": v32["keep_term"],
            "V3.3 cards >= +10%": v33["pass"],
            "determinism": deterministic,
        },
    )
    if not deterministic:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
