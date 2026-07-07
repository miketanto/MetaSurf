"""CLI: python -m validation.v1_archetypes --out validation/reports/<file>.md

Runs V1.1 + V1.2 twice (V1.3 determinism check compares the serialized
metrics byte-for-byte), then writes the report. Exits non-zero if V1.3 fails;
V1.1/V1.2 target misses are written into the report for owner review, per
CLAUDE.md (never silently lowered).
"""

from __future__ import annotations

import argparse
import datetime as dt
from pathlib import Path

from archetypes.classifier.clustering import ATTACH_TAU, MIN_CLUSTER_SIZE, MIN_SAMPLES
from db.connection import connect
from validation.v1_archetypes.run import (
    AGREEMENT_TARGET,
    EMERGENCE_HORIZON_DAYS,
    ESTABLISHED_MIN_DECKS,
    HOLDOUT_END,
    HOLDOUT_START,
    MAJOR_F1_TARGET,
    format_metrics,
    run_v11,
    run_v12,
)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument(
        "--date", default=None, help="report date (YYYY-MM-DD); default: today"
    )
    args = parser.parse_args()
    report_date = args.date or dt.date.today().isoformat()

    with connect() as conn:
        v11a, v12a = run_v11(conn), run_v12(conn)
        v11b, v12b = run_v11(conn), run_v12(conn)
    a, b = format_metrics(v11a, v12a), format_metrics(v11b, v12b)
    deterministic = a == b

    v11, v12 = v11a, v12a
    failures: list[str] = []
    if v11["agreement"] < AGREEMENT_TARGET:
        failures.append(
            f"V1.1 agreement {v11['agreement']:.4f} < target {AGREEMENT_TARGET}"
        )
    weak = [(n, f1) for n, _, _, _, f1 in v11["per_archetype"] if f1 < MAJOR_F1_TARGET]
    if weak:
        failures.append(
            f"V1.1 archetypes below F1 {MAJOR_F1_TARGET}: "
            + ", ".join(f"{n}={f1:.3f}" for n, f1 in weak)
        )
    for ev in v12:
        if not ev.get("passed"):
            failures.append(f"V1.2 event failed: {ev['event']}")
    if not deterministic:
        failures.append("V1.3 determinism FAILED (metrics differ across runs)")

    s: list[str] = [f"# M1 V1 archetype-classifier validation — {report_date}", ""]
    s.append(
        "All numbers are printed output of `python -m validation.v1_archetypes` "
        "against the rebuilt database. Methodology: docstring of "
        "`validation/v1_archetypes/run.py`."
    )
    s.append(f"\nClassifier version: `{v11['classifier_version']}`")
    s.append(
        f"Rule-name resolution: fold-resolved={v11['fold_resolved']} "
        f"unresolved={v11['unresolved_rule_names']}"
    )

    s.append(f"\n## V1.1 — hold-out month {HOLDOUT_START} .. {HOLDOUT_END}\n")
    s.append(
        f"Decks: {v11['decks']} | specific-rules labeled: {v11['rules_labeled']} "
        f"(conflicts: {v11['conflicts']}, fallback-labeled: {v11['fallback_labeled']}) | "
        f"clusters: {v11['clusters']} | noise decks: {v11['noise']}"
    )
    s.append(
        f"\n**Agreement on established archetypes (>= {ESTABLISHED_MIN_DECKS} decks): "
        f"{v11['agreement']:.4f}** (target >= {AGREEMENT_TARGET}) | "
        f"**ARI: {v11['ari']:.4f}**"
    )
    s.append(
        "\nARI is computed against raw cluster ids BEFORE majority-label mapping; "
        "HDBSCAN deliberately splits archetypes into many fine-grained clusters "
        "(builds/variants), so ARI is structurally low while mapped agreement is "
        "high. The plan sets a target on agreement, not ARI; ARI is reported for "
        "reference."
    )
    s.append(
        "\nClustering-stage hyperparameters (frozen BEFORE this holdout run on the "
        "disjoint tuning month 2023-03; grid + scores in the "
        "`archetypes/classifier/clustering.py` docstring): "
        f"min_cluster_size={MIN_CLUSTER_SIZE}, min_samples={MIN_SAMPLES}, "
        f"selection=eom, noise-attachment tau={ATTACH_TAU} "
        "(noise decks join the nearest cluster centroid at cosine >= tau; "
        "below tau stays Rogue). Tuning-month score: agreement 0.9925, worst "
        "established F1 0.933. The holdout month was not used for any tuning."
    )
    s.append("\n| archetype | decks | precision | recall | F1 |")
    s.append("|---|---|---|---|---|")
    for arch, n, p, r, f1 in v11["per_archetype"]:
        s.append(f"| {arch} | {n} | {p:.4f} | {r:.4f} | {f1:.4f} |")

    s.append(f"\n## V1.2 — emergence backtest (horizon {EMERGENCE_HORIZON_DAYS} days)\n")
    s.append(
        "| event | archetype | key card | first >=5 | deadline | detected | "
        "cluster size | purity | passed |"
    )
    s.append("|---|---|---|---|---|---|---|---|---|")
    for ev in v12:
        if "error" in ev:
            s.append(f"| {ev['event']} | ERROR: {ev['error']} |||||||||")
            continue
        s.append(
            f"| {ev['event']} | {ev['archetype']} | {ev['key_card']} | "
            f"{ev['first_5_appearances']} | {ev['deadline']} | "
            f"{ev['detected_on'] or 'NOT DETECTED'} | {ev['detected_cluster_size']} | "
            f"{ev['detected_cluster_purity']} | {'PASS' if ev['passed'] else 'FAIL'} |"
        )
    s.append(
        "\nNote: the acceptance criterion's \"before/at the time community sites "
        "named it\" clause is not verifiable offline (no archived naming dates in "
        "this environment); the measurable criterion applied is detection within "
        "7 days of the first 5 appearances."
    )

    s.append("\n## V1.3 — determinism\n")
    s.append(
        "Full V1.1+V1.2 computation executed twice in-process; serialized metrics "
        + ("**byte-identical** — PASS." if deterministic else "**DIFFER** — FAIL.")
    )

    s.append("\n## Verdict\n")
    if failures:
        s.append("**TARGETS MISSED — stopped for owner review (CLAUDE.md):**\n")
        s.extend(f"- {f}" for f in failures)
    else:
        s.append("All V1.1-V1.3 acceptance criteria met.")
    s.append("")

    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text("\n".join(s), encoding="utf-8")
    print(f"wrote {args.out}")
    print("PASS" if not failures else "FAILURES:\n" + "\n".join(failures))
    if not deterministic:
        raise SystemExit(2)


if __name__ == "__main__":
    main()
