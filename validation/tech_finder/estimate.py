"""Layer B — within-archetype, matchup-conditioned role-effect estimator.

The honest design from research-log §4c: neither raw share-correlation (§4c
confounds with meta board-wipes) nor matchup difference-in-differences (§4c
confounds with archetype identity — Storm's own cards score high vs Eldrazi)
isolates tech. The fix is to estimate *within a fixed player archetype*: among
decks of the same archetype X, does packing a card of functional role R
improve X's realized winrate vs opponent A **more than** it improves X's
winrate vs the rest of the field?

For each player archetype X we form the 2x2:

                          plays a role-R card    plays no role-R card
    vs opponent A            wr_aT (n_aT)            wr_a0 (n_a0)
    vs the field (~A)        wr_fT (n_fT)            wr_f0 (n_f0)

and the per-archetype difference-in-differences

    did_X = (wr_aT - wr_a0) - (wr_fT - wr_f0)

controls BOTH confounds: the field row removes "R is just generically good",
and estimating within X removes "X structurally beats A". The A-specific effect
of role R is the sample-weighted pool of did_X over the archetypes X that have
enough decks in all four cells. Pooling by *role* (not card) is what buys the
sample the per-card version of §4c could not support.

This module is card-agnostic on purpose (it sees archetype strings, role
strings, and win/loss ints — no card identity), which is also the game-neutral
seam: the same estimator serves any game whose Layer A emits roles.
"""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass


@dataclass(frozen=True)
class DirectedRow:
    """One decided match from the player's side (mirrors excluded upstream)."""

    player_arch: str
    opponent_arch: str
    win: int  # 1 player won, 0 player lost
    roles: frozenset[str]


@dataclass(frozen=True)
class RoleEffect:
    role: str
    opponent: str
    a_specific: float  # within-archetype DiD, pooled
    effect_vs_a: float  # pooled within-X (wr_aT - wr_a0)
    effect_vs_field: float  # pooled within-X (wr_fT - wr_f0)
    n_strata: int  # player archetypes contributing (all four cells >= min_cell)
    support: int  # total decided player-rows across contributing cells
    prevalence_vs_a: float  # BASELINE: P(player packs R | opp == A), no control


def _wr(w: int, n: int) -> float:
    return w / n if n else 0.0


def role_effects_for_opponent(
    rows: list[DirectedRow],
    opponent: str,
    roles: tuple[str, ...],
    min_cell: int = 20,
) -> list[RoleEffect]:
    """A-specific effect of every role vs ``opponent``, biggest first.

    ``min_cell``: an archetype X must have >= this many decided rows in EACH of
    the four cells to contribute (guards against 1-deck strata). Set a priori.
    """
    # per (role, player_arch, target, treat) -> [wins, n]
    Cell = dict[tuple[str, int, int], list[int]]
    cells: dict[str, Cell] = {r: defaultdict(lambda: [0, 0]) for r in roles}
    # baseline prevalence vs A
    prev_hit = {r: 0 for r in roles}
    prev_tot = 0

    for row in rows:
        target = 1 if row.opponent_arch == opponent else 0
        if target:
            prev_tot += 1
        for r in roles:
            treat = 1 if r in row.roles else 0
            cell = cells[r][(row.player_arch, target, treat)]
            cell[0] += row.win
            cell[1] += 1
            if target and treat:
                prev_hit[r] += 1

    out: list[RoleEffect] = []
    for r in roles:
        c = cells[r]
        strata = sorted({x for (x, _t, _tr) in c})  # sorted -> deterministic pooling
        num_a = den_a = 0.0
        num_f = den_f = 0.0
        num_did = den_did = 0.0
        n_strata = 0
        support = 0
        for x in strata:
            aT, a0 = c.get((x, 1, 1)), c.get((x, 1, 0))
            fT, f0 = c.get((x, 0, 1)), c.get((x, 0, 0))
            if not (aT and a0 and fT and f0):
                continue
            if min(aT[1], a0[1], fT[1], f0[1]) < min_cell:
                continue
            eff_a = _wr(*aT) - _wr(*a0)
            eff_f = _wr(*fT) - _wr(*f0)
            w = min(aT[1], a0[1], fT[1], f0[1])
            num_a += w * eff_a
            den_a += w
            num_f += w * eff_f
            den_f += w
            num_did += w * (eff_a - eff_f)
            den_did += w
            n_strata += 1
            support += aT[1] + a0[1] + fT[1] + f0[1]
        out.append(
            RoleEffect(
                role=r,
                opponent=opponent,
                a_specific=(num_did / den_did) if den_did else 0.0,
                effect_vs_a=(num_a / den_a) if den_a else 0.0,
                effect_vs_field=(num_f / den_f) if den_f else 0.0,
                n_strata=n_strata,
                support=support,
                prevalence_vs_a=(prev_hit[r] / prev_tot) if prev_tot else 0.0,
            )
        )
    out.sort(key=lambda e: e.a_specific, reverse=True)
    return out


def rank_of(effects: list[RoleEffect], target_roles: set[str], key: str) -> int | None:
    """1-based best rank achieved by any role in ``target_roles`` when the list
    is ordered by ``key`` descending. None if no target role has support."""
    ordered = sorted(effects, key=lambda e: getattr(e, key), reverse=True)
    for i, e in enumerate(ordered, start=1):
        if e.role in target_roles and e.n_strata > 0:
            return i
    return None
