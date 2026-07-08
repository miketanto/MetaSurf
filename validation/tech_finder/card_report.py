"""Per-archetype card tech sheet: "what cards are good against archetype A",
from the card-level within-archetype DiD. `--format modern|standard`.

Each card is annotated with its functional role(s) (Layer A) and flagged when it
is a pure manabase/deck-identity proxy (a Land carrying no interaction role) —
those rank on deck-type correlation, not on being an answer, and the
within-archetype control is imperfect at thin strata. Redirect to
validation/reports/tech-cards-<fmt>-<date>.md.
"""

from __future__ import annotations

import argparse

import psycopg

from db.connection import database_url
from validation.tech_finder.cards import card_effects_for_opponent
from validation.tech_finder.data import load_card_rows

# how many opponents to profile and cards to show each
TOP_ARCHETYPES = 12
TOP_CARDS = 15
MIN_CARD_VS_A = 40
MIN_STRATA = 3


def _card_roles(conn: psycopg.Connection) -> dict[int, list[str]]:
    with conn.cursor() as cur:
        cur.execute("SELECT card_id, role FROM card_roles ORDER BY card_id, role")
        roles: dict[int, list[str]] = {}
        for cid, role in cur.fetchall():
            roles.setdefault(cid, []).append(role)
    return roles


def _lands(conn: psycopg.Connection) -> set[int]:
    with conn.cursor() as cur:
        cur.execute("SELECT id FROM cards WHERE attrs->>'type_line' ILIKE '%%Land%%'")
        return {r[0] for r in cur.fetchall()}


def _top_opponents(rows: list, limit: int) -> list[str]:
    counts: dict[str, int] = {}
    for r in rows:
        counts[r.opponent_arch] = counts.get(r.opponent_arch, 0) + 1
    return [a for a, _ in sorted(counts.items(), key=lambda kv: (-kv[1], kv[0]))[:limit]]


def _annotate(card_id: int, roles: dict[int, list[str]], lands: set[int]) -> str:
    rs = roles.get(card_id)
    if rs:
        return ", ".join(rs)
    return "land / deck-proxy" if card_id in lands else "—"


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--format", default="modern", choices=("modern", "standard"))
    fmt = ap.parse_args().format

    with psycopg.connect(database_url()) as conn:
        rows, names = load_card_rows(conn, fmt)
        roles = _card_roles(conn)
        lands = _lands(conn)

    opponents = _top_opponents(rows, TOP_ARCHETYPES)
    print(f"# What cards are good against each archetype — {fmt} — 2026-07-08")
    print()
    print(f"Card-level within-archetype, matchup-conditioned DiD (the §4c honest "
          f"design at card granularity). {len(rows)} directed decided non-mirror "
          f"rows. A card is scored only where it appears in >= {MIN_CARD_VS_A} "
          f"decided rows vs the archetype across >= {MIN_STRATA} player "
          f"archetypes. `A-specific` = how much more the card lifts a deck's "
          f"winrate vs this archetype than vs the field. Deterministic. Cards "
          f"tagged `land / deck-proxy` are manabase that rides deck-type "
          f"correlation, not answers — read past them.")
    print()
    print("All numbers printed by `python -m validation.tech_finder.card_report "
          f"--format {fmt}`.")

    for opp in opponents:
        eff = card_effects_for_opponent(
            rows, opp, min_card_vs_a=MIN_CARD_VS_A, min_strata=MIN_STRATA
        )
        print(f"\n## vs {opp}  ({len(eff)} scored cards)")
        print()
        print("| card | A-specific | vsA | field | strata | support | role / kind |")
        print("|---|---|---|---|---|---|---|")
        for e in eff[:TOP_CARDS]:
            print(
                f"| {names.get(e.card_id, e.card_id)} | {e.a_specific:+.4f} | "
                f"{e.effect_vs_a:+.4f} | {e.effect_vs_field:+.4f} | {e.n_strata} | "
                f"{e.support_vs_a} | {_annotate(e.card_id, roles, lands)} |"
            )


if __name__ == "__main__":
    main()
