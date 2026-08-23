"""Beta sweep for the semantic channel, on the TUNING month only.

The M1 hyperparameters were frozen on 2023-03, disjoint from the 2024-01
holdout (see `archetypes/classifier/clustering.py`). This sweep keeps that
discipline: beta is chosen here, on 2023-03, and the holdout is run exactly
once afterwards at the frozen value. Running the sweep on the holdout would
spend the only clean evaluation the project has.

Usage:
    python -m validation.v1_archetypes.sweep [--out <path>] [--betas 0,0.25,...]
"""

from __future__ import annotations

import argparse
import datetime as dt
from pathlib import Path
from typing import Any

from db.connection import connect
from ingest.cardsem.db import load_card_features
from validation.v1_archetypes.run import (
    AGREEMENT_TARGET,
    ESTABLISHED_MIN_DECKS,
    MAJOR_F1_TARGET,
    run_v11,
    run_v12,
)

TUNING_START = dt.date(2023, 3, 1)
TUNING_END = dt.date(2023, 3, 31)
DEFAULT_BETAS = (0.0, 0.15, 0.25, 0.35, 0.5, 0.75, 1.0)

# The archetype the design note predicts should improve if the mechanism is
# real: a control deck whose lists differ mainly by interchangeable answers.
PREDICTED_BENEFICIARY = "Azorius Control"


def _as_date(value: Any) -> dt.date:
    """run_v12 serializes dates for the report; accept either form."""
    return value if isinstance(value, dt.date) else dt.date.fromisoformat(str(value))


def _weakest(per_archetype: list[tuple[str, int, float, float, float]]) -> tuple[str, float]:
    name, _, _, _, f1 = min(per_archetype, key=lambda row: (row[4], row[0]))
    return name, f1


def sweep(betas: tuple[float, ...] = DEFAULT_BETAS) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    with connect() as conn:
        features, join = load_card_features(conn)
        print(
            f"card features: {len(features)} cards "
            f"(joined {join.matched}, unmatched {len(join.unmatched_cards)}, "
            f"zero-vector dropped {len(join.zero_vector_keys)})"
        )
        for beta in betas:
            result = run_v11(
                conn,
                start=TUNING_START,
                end=TUNING_END,
                card_features=features if beta > 0 else None,
                feature_weight=beta,
            )
            by_arch = {name: f1 for name, _, _, _, f1 in result["per_archetype"]}
            weak_name, weak_f1 = _weakest(result["per_archetype"])
            row = {
                "beta": beta,
                "agreement": result["agreement"],
                "ari": result["ari"],
                "clusters": result["clusters"],
                "noise": result["noise"],
                "weakest": weak_name,
                "weakest_f1": weak_f1,
                "predicted_f1": by_arch.get(PREDICTED_BENEFICIARY),
                "n_established": len(result["per_archetype"]),
            }
            rows.append(row)
            print(
                f"beta={beta:<5} agreement={row['agreement']:.4f} "
                f"clusters={row['clusters']:<5} noise={row['noise']:<5} "
                f"weakest={weak_name}={weak_f1:.4f}"
            )
    return rows


def emergence_ablation(betas: tuple[float, ...] = DEFAULT_BETAS) -> list[dict[str, Any]]:
    """V1.2 across the same beta grid.

    Unlike V1.1 this is run on the real emergence events, because V1.2 has no
    tuning/holdout split to spend — it is a pass/fail backtest on two fixed
    historical events, and detection date and cluster purity are the outputs
    that matter.
    """
    rows: list[dict[str, Any]] = []
    with connect() as conn:
        features, _ = load_card_features(conn)
        for beta in betas:
            for ev in run_v12(
                conn,
                card_features=features if beta > 0 else None,
                feature_weight=beta,
            ):
                if "error" in ev:
                    rows.append({"beta": beta, "event": ev["event"], "error": ev["error"]})
                    continue
                lag = (
                    (_as_date(ev["detected_on"]) - _as_date(ev["first_5_appearances"])).days
                    if ev["detected_on"]
                    else None
                )
                rows.append(
                    {
                        "beta": beta,
                        "event": ev["event"],
                        "first5": ev["first_5_appearances"],
                        "detected_on": ev["detected_on"],
                        "lag_days": lag,
                        "size": ev["detected_cluster_size"],
                        "purity": ev["detected_cluster_purity"],
                        "passed": ev["passed"],
                    }
                )
                print(
                    f"beta={beta:<5} {ev['event'][:34]:35} lag={lag} "
                    f"purity={ev['detected_cluster_purity']:.3f} "
                    f"{'PASS' if ev['passed'] else 'FAIL'}"
                )
    return rows


def render_emergence(rows: list[dict[str, Any]]) -> list[str]:
    lines = [
        "| beta | event | first >=5 | detected | lag (days) | cluster size | purity | result |",
        "|---:|---|---|---|---:|---:|---:|---|",
    ]
    for r in rows:
        if "error" in r:
            lines.append(f"| {r['beta']} | {r['event']} | ERROR: {r['error']} ||||||")
            continue
        lines.append(
            f"| {r['beta']} | {r['event']} | {r['first5']} | {r['detected_on']} | "
            f"{r['lag_days']} | {r['size']} | {r['purity']:.3f} | "
            f"{'PASS' if r['passed'] else 'FAIL'} |"
        )
    return lines


def render(rows: list[dict[str, Any]], today: str, emergence: list[dict[str, Any]]) -> str:
    base = next(r for r in rows if r["beta"] == 0.0)
    best = max(rows, key=lambda r: (r["agreement"], -r["beta"]))
    lines = [f"# Semantic-channel ablation (V1.1 sweep + V1.2) — {today}", ""]
    lines.append(
        "Ablation of the CardGuru feature channel in the clustering-stage "
        "vectorizer (design: `docs/notes/card-semantics-integration.md`). Every "
        "number is printed output of `python -m validation.v1_archetypes.sweep`."
    )
    lines.append("")

    lines.append("## V1.1 — beta sweep on the TUNING month")
    lines.append("")
    lines.append(
        f"Tuning month {TUNING_START} .. {TUNING_END}, disjoint from the M1 holdout "
        "(2024-01), which is deliberately NOT touched: beta is chosen here or not "
        "at all."
    )
    lines.append("")
    lines.append(
        f"Established archetypes = rule labels with >= {ESTABLISHED_MIN_DECKS} decks. "
        f"Agreement target >= {AGREEMENT_TARGET}; per-archetype F1 target >= "
        f"{MAJOR_F1_TARGET}."
    )
    lines.append("")
    lines.append(
        "| beta | agreement | ARI | clusters | noise | weakest archetype | weakest F1 |"
        f" {PREDICTED_BENEFICIARY} F1 |"
    )
    lines.append("|---:|---:|---:|---:|---:|---|---:|---:|")
    for r in rows:
        predicted = "n/a" if r["predicted_f1"] is None else f"{r['predicted_f1']:.4f}"
        lines.append(
            f"| {r['beta']} | {r['agreement']:.4f} | {r['ari']:.4f} | {r['clusters']} | "
            f"{r['noise']} | {r['weakest']} | {r['weakest_f1']:.4f} | {predicted} |"
        )
    lines.append("")

    lines.append("## V1.2 — emergence backtest across beta")
    lines.append("")
    lines.extend(render_emergence(emergence))
    lines.append("")

    lines.append("## Verdict")
    lines.append("")
    delta = best["agreement"] - base["agreement"]
    lines.append(
        f"- Baseline (beta=0) agreement **{base['agreement']:.4f}**; best swept beta "
        f"{best['beta']} at **{best['agreement']:.4f}** (delta "
        f"{delta:+.4f})."
    )
    lines.append(
        f"- Weakest established F1: baseline **{base['weakest_f1']:.4f}** "
        f"({base['weakest']}); at best beta **{best['weakest_f1']:.4f}** "
        f"({best['weakest']})."
    )
    if base["predicted_f1"] is not None and best["predicted_f1"] is not None:
        lines.append(
            f"- Pre-committed prediction ({PREDICTED_BENEFICIARY} improves): baseline "
            f"**{base['predicted_f1']:.4f}** -> **{best['predicted_f1']:.4f}** at best "
            f"beta — **"
            + ("CONFIRMED" if best["predicted_f1"] > base["predicted_f1"] else "FALSIFIED")
            + "**."
        )
    ok = [r for r in emergence if not r.get("error")]
    base_purity = [r["purity"] for r in ok if r["beta"] == 0.0]
    worst_purity = min((r["purity"] for r in ok if r["beta"] > 0), default=None)
    max_lag = max((r["lag_days"] or 0 for r in ok if r["beta"] > 0), default=None)
    base_lag = max((r["lag_days"] or 0 for r in ok if r["beta"] == 0.0), default=None)
    if base_purity and worst_purity is not None:
        lines.append(
            f"- V1.2 cluster purity: baseline min **{min(base_purity):.3f}**, worst "
            f"across beta>0 **{worst_purity:.3f}**. Detection lag: baseline max "
            f"**{base_lag}** days, worst across beta>0 **{max_lag}** days."
        )
    lines.append("")
    return "\n".join(lines) + "\n"


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", type=Path, default=None)
    parser.add_argument("--betas", default=None, help="comma-separated beta grid")
    parser.add_argument(
        "--emergence-betas",
        default="0.0,0.25,0.5,1.0",
        help="beta grid for the V1.2 ablation (coarser: each run is a 60-day window)",
    )
    parser.add_argument("--today", default=dt.date.today().isoformat())
    args = parser.parse_args()
    betas = (
        tuple(float(b) for b in args.betas.split(",")) if args.betas else DEFAULT_BETAS
    )
    rows = sweep(betas)
    emergence = emergence_ablation(
        tuple(float(b) for b in args.emergence_betas.split(","))
    )
    text = render(rows, args.today, emergence)
    if args.out:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(text, encoding="utf-8")
        print(f"wrote {args.out}")
    print(text)


if __name__ == "__main__":
    main()
