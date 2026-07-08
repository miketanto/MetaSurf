"""B2 known-tech recovery + B1 temporal reproducibility for the tech finder.

Pre-registered (set BEFORE seeing per-role numbers; do not tune to results):
- Proof targets & their community-known tech roles are fixed below.
- min_cell = 20 (a stratum needs >=20 decided rows in each of the 2x2 cells).
- top_k = 3 (recovery = the known role lands in the top 3 of the 9 roles).
- B2 PASS: the known-tech role ranks in the top_k by A-specific DiD AND does so
  at a rank <= its rank by the frequency-only baseline (beats/ties the naive
  method §4c showed fails).
- B1 PASS: on two disjoint time blocks (2022-2023, 2024-2025) the target's
  primary role keeps a POSITIVE A-specific effect and stays in the top_k in both.
A miss is reported, not lowered (CLAUDE.md).
"""

from __future__ import annotations

import datetime as dt
from dataclasses import dataclass

import psycopg

from validation.tech_finder.data import load_directed_rows
from validation.tech_finder.estimate import (
    RoleEffect,
    rank_of,
    role_effects_for_opponent,
)

MIN_CELL = 20
TOP_K = 3
# Two disjoint temporal blocks per format for B1 (a-priori calendar splits at a
# format's data density; chosen before per-block results).
B1_BLOCKS_BY_FORMAT = {
    "modern": (
        (dt.date(2022, 1, 1), dt.date(2023, 12, 31)),
        (dt.date(2024, 1, 1), dt.date(2025, 12, 31)),
    ),
    "standard": (  # corpus is 2024-01..2026-07, so split at the year boundary
        (dt.date(2024, 1, 1), dt.date(2024, 12, 31)),
        (dt.date(2025, 1, 1), dt.date(2026, 12, 31)),
    ),
}


@dataclass(frozen=True)
class ProofTarget:
    opponent: str  # archetype label as classified
    known: frozenset[str]  # community-known tech roles vs this opponent
    primary: str  # the single role used for the B1 reproducibility gate
    gated: bool  # counts toward the overall verdict (False = reported only)


# Known tech roles are fixed A PRIORI from community consensus on each deck's
# structural weakness, BEFORE running (see docstring / report). `primary` (the
# single role B1 reproducibility is checked on) is the most iconic answer.
# `gated` = the weakness maps cleanly to one of our 9 roles -> counts toward the
# verdict; `reported-only` = muddy/generic/thin-sample, shown for context.
_MODERN_TARGETS = (
    # ramp / greedy-manabase decks -> attack the lands/mana
    ProofTarget("GenericTron", frozenset({"land_destruction", "mana_denial"}),
                "land_destruction", True),
    ProofTarget("Titan", frozenset({"land_destruction", "mana_denial"}),
                "land_destruction", True),
    ProofTarget("Eldrazi", frozenset({"land_destruction", "mana_denial"}),
                "land_destruction", False),
    # graveyard decks -> graveyard hate
    ProofTarget("LivingEnd", frozenset({"graveyard_hate"}), "graveyard_hate", True),
    ProofTarget("GoryoReanimator", frozenset({"graveyard_hate"}), "graveyard_hate", True),
    ProofTarget("Yawgmoth", frozenset({"graveyard_hate"}), "graveyard_hate", False),
    ProofTarget("Dredge", frozenset({"graveyard_hate"}), "graveyard_hate", False),
    # artifact/equipment decks -> artifact removal
    ProofTarget("HammerTime", frozenset({"artifact_enchant_removal"}),
                "artifact_enchant_removal", True),
    ProofTarget("Affinity", frozenset({"artifact_enchant_removal"}),
                "artifact_enchant_removal", True),
    ProofTarget("HardenedScales", frozenset({"artifact_enchant_removal"}),
                "artifact_enchant_removal", False),
    # ritual/combo -> hand disruption
    ProofTarget("RubyStorm", frozenset({"hand_disruption", "counter_spell"}),
                "hand_disruption", True),
    # cascade -> counter the free spell
    ProofTarget("Footfalls", frozenset({"counter_spell"}), "counter_spell", False),
    # creature aggro -> board sweeper (expected MUDDY per §4d: generic answers
    # help vs every creature deck; the honest boundary of the method)
    ProofTarget("Aggro", frozenset({"board_sweeper"}), "board_sweeper", False),
)

# Standard 2024-25 (labels as classified). Fewer textbook structural weaknesses
# than Modern; the clean cases are graveyard decks and go-wide aggro.
_STANDARD_TARGETS = (
    # reanimator / graveyard-threat decks -> graveyard hate
    ProofTarget("Reanimator", frozenset({"graveyard_hate"}), "graveyard_hate", True),
    ProofTarget("Oculus", frozenset({"graveyard_hate"}), "graveyard_hate", True),
    ProofTarget("Demons", frozenset({"graveyard_hate"}), "graveyard_hate", False),
    # go-wide creature aggro -> board sweeper
    ProofTarget("Boros Convoke", frozenset({"board_sweeper"}), "board_sweeper", True),
    ProofTarget("Convoke", frozenset({"board_sweeper"}), "board_sweeper", False),
    ProofTarget("Poison", frozenset({"board_sweeper"}), "board_sweeper", False),
    # artifact aggro -> artifact removal
    ProofTarget("Artifact Aggro", frozenset({"artifact_enchant_removal"}),
                "artifact_enchant_removal", False),
    # midrange/creature decks -> board sweeper (muddy boundary, reported)
    ProofTarget("Aggro", frozenset({"board_sweeper"}), "board_sweeper", False),
)

TARGETS_BY_FORMAT = {
    "modern": _MODERN_TARGETS,
    "standard": _STANDARD_TARGETS,
}


@dataclass(frozen=True)
class B2Result:
    target: ProofTarget
    effects: list[RoleEffect]
    rank_did: int | None
    rank_prev: int | None

    @property
    def passed(self) -> bool:
        return (
            self.rank_did is not None
            and self.rank_did <= TOP_K
            and (self.rank_prev is None or self.rank_did <= self.rank_prev)
        )


@dataclass(frozen=True)
class B1Result:
    target: ProofTarget
    block_effects: list[tuple[tuple[dt.date, dt.date], RoleEffect | None, int | None]]

    @property
    def passed(self) -> bool:
        ok = True
        for _blk, eff, rk in self.block_effects:
            if eff is None or eff.n_strata == 0 or eff.a_specific <= 0:
                ok = False
            if rk is None or rk > TOP_K:
                ok = False
        return ok


def run_b2(
    rows: list, roles: tuple[str, ...], targets: tuple[ProofTarget, ...]
) -> list[B2Result]:
    results = []
    for t in targets:
        eff = role_effects_for_opponent(rows, t.opponent, roles, min_cell=MIN_CELL)
        results.append(
            B2Result(
                target=t,
                effects=eff,
                rank_did=rank_of(eff, set(t.known), "a_specific"),
                rank_prev=rank_of(eff, set(t.known), "prevalence_vs_a"),
            )
        )
    return results


def run_b1(
    conn: psycopg.Connection,
    roles: tuple[str, ...],
    targets: tuple[ProofTarget, ...],
    format_name: str,
) -> list[B1Result]:
    blocks = B1_BLOCKS_BY_FORMAT[format_name]
    block_rows = [
        load_directed_rows(conn, format_name, date_from=lo, date_to=hi)
        for lo, hi in blocks
    ]
    results = []
    for t in targets:
        per_block = []
        for blk, rows in zip(blocks, block_rows, strict=True):
            eff = role_effects_for_opponent(rows, t.opponent, roles, min_cell=MIN_CELL)
            primary = next((e for e in eff if e.role == t.primary), None)
            rk = rank_of(eff, {t.primary}, "a_specific")
            per_block.append((blk, primary, rk))
        results.append(B1Result(target=t, block_effects=per_block))
    return results
