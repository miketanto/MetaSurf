"""Print the tech-finder B2/B1 report (real Modern corpus). Redirect to
validation/reports/tech-finder-b1b2-<date>.md."""

from __future__ import annotations

import psycopg

from archetypes.roles import all_roles
from db.connection import database_url
from validation.tech_finder.data import load_directed_rows
from validation.tech_finder.run import TOP_K, run_b1, run_b2


def _fmt_effects_table(effects: list) -> list[str]:
    out = [
        f"| {'role':24} | A-specific | eff_vsA | eff_field | strata | support | prev_vsA |",
        "|" + "---|" * 7,
    ]
    for e in effects:
        out.append(
            f"| {e.role:24} | {e.a_specific:+.4f} | {e.effect_vs_a:+.4f} | "
            f"{e.effect_vs_field:+.4f} | {e.n_strata} | {e.support} | {e.prevalence_vs_a:.3f} |"
        )
    return out


def main() -> None:
    roles = all_roles()
    with psycopg.connect(database_url()) as conn:
        rows = load_directed_rows(conn, "modern")
        b2 = run_b2(rows, roles)
        b1 = run_b1(conn, roles)

    print("# Tech finder — B2 known-tech recovery + B1 reproducibility (Modern)")
    print()
    print(f"Directed decided non-mirror match rows: **{len(rows)}**. "
          f"Roles vocabulary ({len(roles)}): {', '.join(roles)}.")
    print()
    print("All numbers are printed output of `python -m validation.tech_finder` "
          "against the rebuilt Modern corpus (import + match_extract + rules "
          "labeling). Design: docstring of `validation/tech_finder/estimate.py`.")
    print()
    print("## B2 — recovery: does the within-archetype DiD rank the known tech "
          f"role in the top {TOP_K}, beating the frequency-only baseline?")
    for b2r in b2:
        t = b2r.target
        tag = "GATED" if t.gated else "reported-only"
        print(f"\n### vs {t.opponent}  (known: {sorted(t.known)}, {tag})")
        print()
        print("\n".join(_fmt_effects_table(b2r.effects)))
        print()
        verdict = "PASS" if b2r.passed else "MISS"
        print(f"- known-tech best rank by **A-specific DiD**: {b2r.rank_did}")
        print(f"- known-tech best rank by **prevalence baseline**: {b2r.rank_prev}")
        print(f"- **{verdict}** (top-{TOP_K} by DiD and DiD rank <= baseline rank)")

    print("\n## B1 — temporal reproducibility (disjoint blocks): does the "
          "primary role keep a positive, top-k A-specific effect on both halves?")
    for b1r in b1:
        t = b1r.target
        tag = "GATED" if t.gated else "reported-only"
        print(f"\n### vs {t.opponent}, primary role `{t.primary}`  ({tag})")
        print()
        print("| block | A-specific | strata | rank |")
        print("|---|---|---|---|")
        for (lo, hi), eff, rk in b1r.block_effects:
            if eff is None:
                print(f"| {lo}..{hi} | (no support) | 0 | - |")
            else:
                print(f"| {lo}..{hi} | {eff.a_specific:+.4f} | {eff.n_strata} | {rk} |")
        print()
        print(f"- **{'PASS' if b1r.passed else 'MISS'}** "
              "(positive and top-k on both blocks)")

    gated = [x for x in b2 if x.target.gated]
    gated_b1 = [x for x in b1 if x.target.gated]
    all_pass = all(x.passed for x in gated) and all(x.passed for x in gated_b1)
    n_b2 = sum(x.passed for x in gated)
    n_b1 = sum(x.passed for x in gated_b1)
    print("\n## Verdict")
    print()
    print(f"Gated B2: {n_b2}/{len(gated)} pass. Gated B1: {n_b1}/{len(gated_b1)} pass.")
    verdict = (
        "ALL GATED CRITERIA MET"
        if all_pass
        else "TARGETS MISSED — see above; not lowered (CLAUDE.md)"
    )
    print(f"\n**{verdict}**")


if __name__ == "__main__":
    main()
