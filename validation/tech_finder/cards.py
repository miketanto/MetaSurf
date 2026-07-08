"""Card-level tech: which specific cards are good against an archetype.

Same honest design as the role estimator (research-log §4c) but the "treatment"
is *a single card* in the deck's 75, not a functional role: for opponent A, does
adding card C to a deck of archetype X lift X's winrate vs A **more than** it
lifts X's winrate vs the field, averaged over the archetypes X that play C?

    A_specific(C) = pooled_X [ (wr_aT - wr_a0) - (wr_fT - wr_f0) ]

- within X controls the archetype-identity confound (X structurally beating A);
- minus the field row controls the "C is just generically good" confound.

Card granularity is sample-hungry (why the role layer pools) — so a card is only
scored where it clears an a-priori support floor, and the rest are honestly
omitted. Card-agnostic on the estimator side (it sees ids, archetypes, wins).
"""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass


@dataclass(frozen=True)
class CardRow:
    player_arch: str
    opponent_arch: str
    win: int
    cards: frozenset[int]  # card ids across the whole 75 (main + side)


@dataclass(frozen=True)
class CardEffect:
    card_id: int
    a_specific: float
    effect_vs_a: float  # pooled within-X (wr with C - wr without C) vs A
    effect_vs_field: float
    n_strata: int  # player archetypes contributing (all four cells >= min_cell)
    support_vs_a: int  # decided rows carrying C vs A across contributing strata
    prevalence_vs_a: float  # P(player packs C | opp == A) -- the naive baseline


def _wr(cell: list[int]) -> float:
    return cell[0] / cell[1] if cell[1] else 0.0


def card_effects_for_opponent(
    rows: list[CardRow],
    opponent: str,
    min_cell: int = 20,
    min_card_vs_a: int = 30,
    min_strata: int = 3,
) -> list[CardEffect]:
    """A-specific effect of every sufficiently-played card vs ``opponent``.

    ``min_cell``: floor on each of the four 2x2 cells per stratum.
    ``min_card_vs_a``: a card must appear in >= this many decided rows vs A.
    ``min_strata``: >= this many player archetypes must contribute.
    """
    # totals per (player_arch, target)  -- target = 1 iff opp == A
    totals: dict[tuple[str, int], list[int]] = defaultdict(lambda: [0, 0])
    # candidate screen: how often each card is seen vs A
    seen_vs_a: dict[int, int] = defaultdict(int)
    n_vs_a = 0
    for r in rows:
        t = 1 if r.opponent_arch == opponent else 0
        cell = totals[(r.player_arch, t)]
        cell[0] += r.win
        cell[1] += 1
        if t:
            n_vs_a += 1
            for c in r.cards:
                seen_vs_a[c] += 1

    candidates = {c for c, n in seen_vs_a.items() if n >= min_card_vs_a}
    if not candidates:
        return []

    # per candidate card: cells for "deck carries C" per (X, target); the
    # "without C" cell is totals - with.
    withc: dict[int, dict[tuple[str, int], list[int]]] = {
        c: defaultdict(lambda: [0, 0]) for c in candidates
    }
    for r in rows:
        t = 1 if r.opponent_arch == opponent else 0
        hit = r.cards & candidates
        for c in hit:
            cell = withc[c][(r.player_arch, t)]
            cell[0] += r.win
            cell[1] += 1

    strata = {x for (x, _t) in totals}
    out: list[CardEffect] = []
    for c in candidates:
        num_a = den_a = num_f = den_f = num_d = den_d = 0.0
        n_str = 0
        support = 0
        for x in sorted(strata):
            tot_a, tot_f = totals.get((x, 1)), totals.get((x, 0))
            if not tot_a or not tot_f:
                continue
            aT = withc[c].get((x, 1), [0, 0])
            fT = withc[c].get((x, 0), [0, 0])
            a0 = [tot_a[0] - aT[0], tot_a[1] - aT[1]]
            f0 = [tot_f[0] - fT[0], tot_f[1] - fT[1]]
            if min(aT[1], a0[1], fT[1], f0[1]) < min_cell:
                continue
            eff_a = _wr(aT) - _wr(a0)
            eff_f = _wr(fT) - _wr(f0)
            w = min(aT[1], a0[1], fT[1], f0[1])
            num_a += w * eff_a
            den_a += w
            num_f += w * eff_f
            den_f += w
            num_d += w * (eff_a - eff_f)
            den_d += w
            n_str += 1
            support += aT[1]
        if n_str < min_strata:
            continue
        out.append(
            CardEffect(
                card_id=c,
                a_specific=(num_d / den_d) if den_d else 0.0,
                effect_vs_a=(num_a / den_a) if den_a else 0.0,
                effect_vs_field=(num_f / den_f) if den_f else 0.0,
                n_strata=n_str,
                support_vs_a=support,
                prevalence_vs_a=(seen_vs_a[c] / n_vs_a) if n_vs_a else 0.0,
            )
        )
    out.sort(key=lambda e: (-e.a_specific, e.card_id))  # deterministic tiebreak
    return out
