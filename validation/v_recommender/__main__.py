"""Run V-REC and write the dated report.

Usage: python -m validation.v_recommender [--out validation/reports/m35b-recommender.md]

Full computation runs twice in-process; serialized metrics must be
byte-identical (determinism gate). Exit code reflects the pre-registered
acceptance verdicts (V-REC.1-3).
"""

from __future__ import annotations

import argparse
import datetime as dt

import psycopg

from db.connection import database_url
from validation.v_recommender.run import (
    EVAL_FIRST,
    EVAL_LAST,
    MIN_MATCHES,
    STABILITY_TARGET,
    STRATEGIES,
    evaluate,
    serialize,
)


def render(result: dict, deterministic: bool) -> str:
    today = dt.date.today().isoformat()
    p = result["pooled"]
    v = result["verdicts"]

    def wr(s: str) -> str:
        d = p[s]
        return (f"{d['mean_wr']:.4f} (95% CI {d['ci_lo']:.4f}-{d['ci_hi']:.4f},"
                f" {d['weeks']} wks, t={d['t_vs_half']:+.2f})")

    lines = [
        f"# Deck-recommender validation (V-REC, hardens M3.5b) — {today}",
        "",
        "Printed output of `python -m validation.v_recommender`. Pre-registered"
        " protocol + acceptance in the `validation/v_recommender/run.py`"
        " docstring; nothing here was tuned against the result.",
        "",
        f"Blocked weekly walk-forward, {EVAL_FIRST} .. {EVAL_LAST} (all quarters,"
        " not the single M3.5b window). Each Saturday one deck is picked from"
        " the trailing-1% universe using past data only, then scored by its"
        f" REALIZED match winrate that weekend (>= {MIN_MATCHES} matches to"
        " count; no leakage, no circularity). Field mean is 0.500 by"
        " construction.",
        "",
        "## Pooled result",
        "",
        "| strategy | mean realized winrate | match-weighted |",
        "|---|---|---|",
        f"| **MODEL** (best response to field) | **{wr('MODEL')}**"
        f" | {p['MODEL']['match_weighted_wr']:.4f} |",
        f"| STRONGEST (bring a strong deck) | {wr('STRONGEST')}"
        f" | {p['STRONGEST']['match_weighted_wr']:.4f} |",
        f"| POPULAR (most played) | {wr('POPULAR')}"
        f" | {p['POPULAR']['match_weighted_wr']:.4f} |",
        "",
        "## Acceptance verdicts (pre-registered)",
        "",
        f"- **V-REC.1** edge is real (MODEL 95% CI lower bound > 0.500):"
        f" **{'PASS' if v['V-REC.1 edge real (CI>0.5)'] else 'FAIL'}**"
        f" (CI lo {p['MODEL']['ci_lo']:.4f})",
        f"- **V-REC.2** MODEL >= POPULAR pooled:"
        f" **{'PASS' if v['V-REC.2 beats POPULAR'] else 'FAIL'}**",
        f"- **V-REC.3** MODEL > 0.500 in >= {STABILITY_TARGET:.0%} of quarters"
        f" (>=4 scored weeks): **{'PASS' if v['V-REC.3 stable (>=75% quarters)'] else 'FAIL'}**"
        f" ({result['stability_frac']:.0%} of {result['stability_quarters']} quarters)",
        "",
        "## Positioning bonus and robustness",
        "",
        f"- MODEL vs STRONGEST (the field-positioning bonus over pure deck"
        f" strength): mean per-week winrate diff"
        f" {result['model_vs_strongest']['mean_diff']:+.4f}"
        f" over {result['model_vs_strongest']['weeks']} shared weeks"
        f" (p={result['model_vs_strongest']['p']:.3f}). Most of the edge is deck"
        " strength; positioning adds a little.",
        f"- MODEL vs POPULAR: mean diff"
        f" {result['model_vs_popular']['mean_diff']:+.4f},"
        f" MODEL better in {result['model_vs_popular'].get('a_better_weeks','?')}/"
        f"{result['model_vs_popular']['weeks']} weeks"
        f" (p={result['model_vs_popular']['p']:.3g}).",
        f"- **Winrate-model tuning-overlap check:** MODEL realized winrate is"
        f" {result['overlap_wr']:.4f} in quarters overlapping the winrate"
        f" model's tuning window (2022-07..2023-12) vs"
        f" {result['nonoverlap_wr']:.4f} outside it — the recommender adds no"
        " parameters, so similar values indicate the edge is not a tuning"
        " artifact.",
        "",
        "## Per-quarter detail (mean realized winrate; n scored weeks)",
        "",
        "| quarter | tuning-overlap | MODEL | STRONGEST | POPULAR |",
        "|---|---|---|---|---|",
    ]
    for r in result["per_quarter"]:
        cells = " | ".join(
            f"{r[s][1]:.3f} (n={r[s][0]})" if r[s][0] else "—" for s in STRATEGIES
        )
        lines.append(f"| {r['quarter']} | {'yes' if r['tuning_overlap'] else ''} | {cells} |")
    lines += [
        "",
        "## Determinism",
        "",
        "Full computation executed twice in-process; serialized metrics"
        f" **{'byte-identical' if deterministic else 'DIFFERED'}** —"
        f" {'PASS' if deterministic else 'FAIL'}.",
        "",
    ]
    return "\n".join(lines)


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--out", default="validation/reports/m35b-recommender.md")
    args = ap.parse_args()
    with psycopg.connect(database_url()) as conn:
        r1 = evaluate(conn)
        r2 = evaluate(conn)
    deterministic = serialize(r1) == serialize(r2)
    report = render(r1, deterministic)
    with open(args.out, "w") as f:
        f.write(report)
    print(report)
    print(f"\nwrote {args.out}")
    verdicts = dict(r1["verdicts"])
    verdicts["determinism"] = deterministic
    print("verdicts:", verdicts)
    if not all(verdicts.values()):
        raise SystemExit(1)


if __name__ == "__main__":
    main()
