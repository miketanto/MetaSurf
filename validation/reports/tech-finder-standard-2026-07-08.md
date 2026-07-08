# Tech finder on Standard — recovery + reproducibility — 2026-07-08

Applies the tech finder (BL-1, research-log §4b) to **Standard 2024–25** — a
transfer test after the Modern proof (`tech-finder-b1b2-2026-07-08.md`, gated B2
6/7). Same code, `--format standard`; opponents' known-tech roles fixed a priori
in `run.py`. Same design and pre-registered thresholds (`min_cell=20`,
`top_k=3`; B2 PASS = known role top-3 by DiD and rank ≤ baseline; B1 PASS =
primary role positive+top-3 on both blocks 2024 / 2025+). Deterministic
(byte-identical across two runs). Role coverage was first extended with real
Standard fixtures (Sunfall "exile all creatures", Go for the Throat "destroy
target nonartifact creature", Anguished Unmaking, Sheoldred's Edict, Unlicensed
Hearse, …) so Standard answer cards are actually tagged — 50 parser tests green.

**Result: the method does NOT transfer to Standard on this data. Gated B2 0/3,
B1 0/3.** This is a boundary finding, reported not lowered — see the analysis.

Directed decided non-mirror match rows: **62458**. Roles vocabulary (9): land_destruction, mana_denial, graveyard_hate, creature_removal, board_sweeper, counter_spell, counter_ability, artifact_enchant_removal, hand_disruption.

All numbers are printed output of `python -m validation.tech_finder --format standard` against the rebuilt standard corpus (import + match_extract + rules labeling). Design: docstring of `validation/tech_finder/estimate.py`.

## B2 — recovery: does the within-archetype DiD rank the known tech role in the top 3, beating the frequency-only baseline?

### vs Reanimator  (known: ['graveyard_hate'], GATED)

| role                     | A-specific | eff_vsA | eff_field | strata | support | prev_vsA |
|---|---|---|---|---|---|---|
| counter_spell            | +0.1208 | +0.1563 | +0.0355 | 1 | 11346 | 0.563 |
| counter_ability          | +0.0539 | +0.0795 | +0.0256 | 3 | 24342 | 0.316 |
| mana_denial              | +0.0493 | +0.0437 | -0.0056 | 1 | 6188 | 0.033 |
| graveyard_hate           | +0.0145 | +0.0012 | -0.0132 | 7 | 46469 | 0.563 |
| creature_removal         | +0.0000 | +0.0000 | +0.0000 | 0 | 0 | 0.991 |
| hand_disruption          | -0.0251 | -0.0401 | -0.0150 | 3 | 25083 | 0.330 |
| board_sweeper            | -0.0666 | -0.0779 | -0.0114 | 3 | 24127 | 0.548 |
| land_destruction         | -0.0724 | -0.0795 | -0.0071 | 4 | 30871 | 0.383 |
| artifact_enchant_removal | -0.0912 | -0.0974 | -0.0062 | 3 | 25360 | 0.809 |

- known-tech best rank by **A-specific DiD**: 4
- known-tech best rank by **prevalence baseline**: 4
- **MISS** (top-3 by DiD and DiD rank <= baseline rank)

### vs Oculus  (known: ['graveyard_hate'], GATED)

| role                     | A-specific | eff_vsA | eff_field | strata | support | prev_vsA |
|---|---|---|---|---|---|---|
| board_sweeper            | +0.1648 | +0.1329 | -0.0318 | 1 | 6529 | 0.393 |
| land_destruction         | +0.0947 | +0.0770 | -0.0176 | 1 | 11346 | 0.148 |
| artifact_enchant_removal | +0.0638 | +0.0488 | -0.0150 | 2 | 17875 | 0.788 |
| mana_denial              | +0.0000 | +0.0000 | +0.0000 | 0 | 0 | 0.000 |
| creature_removal         | +0.0000 | +0.0000 | +0.0000 | 0 | 0 | 0.995 |
| hand_disruption          | +0.0000 | +0.0000 | +0.0000 | 0 | 0 | 0.379 |
| graveyard_hate           | -0.0649 | -0.0697 | -0.0048 | 1 | 6529 | 0.755 |
| counter_ability          | -0.1094 | -0.0738 | +0.0356 | 1 | 11346 | 0.224 |
| counter_spell            | -0.1511 | -0.1102 | +0.0409 | 1 | 11346 | 0.413 |

- known-tech best rank by **A-specific DiD**: 7
- known-tech best rank by **prevalence baseline**: 3
- **MISS** (top-3 by DiD and DiD rank <= baseline rank)

### vs Demons  (known: ['graveyard_hate'], reported-only)

| role                     | A-specific | eff_vsA | eff_field | strata | support | prev_vsA |
|---|---|---|---|---|---|---|
| counter_spell            | +0.0868 | +0.1249 | +0.0381 | 1 | 11346 | 0.405 |
| counter_ability          | +0.0616 | +0.0952 | +0.0336 | 1 | 11346 | 0.193 |
| mana_denial              | +0.0000 | +0.0000 | +0.0000 | 0 | 0 | 0.000 |
| creature_removal         | +0.0000 | +0.0000 | +0.0000 | 0 | 0 | 0.994 |
| hand_disruption          | +0.0000 | +0.0000 | +0.0000 | 0 | 0 | 0.356 |
| artifact_enchant_removal | -0.0655 | -0.0774 | -0.0118 | 2 | 17875 | 0.721 |
| land_destruction         | -0.1025 | -0.1188 | -0.0163 | 1 | 11346 | 0.092 |
| graveyard_hate           | -0.1222 | -0.1263 | -0.0041 | 1 | 6529 | 0.664 |
| board_sweeper            | -0.2679 | -0.2928 | -0.0248 | 1 | 6529 | 0.310 |

- known-tech best rank by **A-specific DiD**: 8
- known-tech best rank by **prevalence baseline**: 3
- **MISS** (top-3 by DiD and DiD rank <= baseline rank)

### vs Boros Convoke  (known: ['board_sweeper'], GATED)

| role                     | A-specific | eff_vsA | eff_field | strata | support | prev_vsA |
|---|---|---|---|---|---|---|
| artifact_enchant_removal | +0.0494 | +0.0371 | -0.0123 | 5 | 32947 | 0.805 |
| graveyard_hate           | +0.0374 | +0.0123 | -0.0250 | 10 | 49188 | 0.720 |
| counter_spell            | +0.0238 | +0.0620 | +0.0382 | 4 | 22368 | 0.745 |
| land_destruction         | +0.0190 | +0.0123 | -0.0066 | 6 | 33859 | 0.532 |
| counter_ability          | +0.0106 | +0.0277 | +0.0171 | 6 | 35012 | 0.472 |
| mana_denial              | +0.0000 | +0.0000 | +0.0000 | 0 | 0 | 0.011 |
| creature_removal         | +0.0000 | +0.0000 | +0.0000 | 0 | 0 | 0.995 |
| board_sweeper            | -0.0117 | -0.0106 | +0.0011 | 7 | 35697 | 0.617 |
| hand_disruption          | -0.0472 | -0.0550 | -0.0078 | 6 | 35000 | 0.375 |

- known-tech best rank by **A-specific DiD**: 8
- known-tech best rank by **prevalence baseline**: 5
- **MISS** (top-3 by DiD and DiD rank <= baseline rank)

### vs Convoke  (known: ['board_sweeper'], reported-only)

| role                     | A-specific | eff_vsA | eff_field | strata | support | prev_vsA |
|---|---|---|---|---|---|---|
| board_sweeper            | +0.0724 | +0.0437 | -0.0286 | 2 | 17875 | 0.453 |
| counter_spell            | +0.0325 | +0.0712 | +0.0387 | 1 | 11346 | 0.418 |
| counter_ability          | +0.0242 | +0.0508 | +0.0265 | 3 | 24342 | 0.232 |
| artifact_enchant_removal | +0.0171 | +0.0024 | -0.0146 | 2 | 17875 | 0.774 |
| graveyard_hate           | +0.0151 | +0.0174 | +0.0023 | 2 | 17875 | 0.672 |
| mana_denial              | +0.0000 | +0.0000 | +0.0000 | 0 | 0 | 0.000 |
| creature_removal         | +0.0000 | +0.0000 | +0.0000 | 0 | 0 | 0.998 |
| hand_disruption          | -0.1531 | -0.1508 | +0.0023 | 1 | 11346 | 0.456 |
| land_destruction         | -0.1974 | -0.1950 | +0.0024 | 2 | 18831 | 0.150 |

- known-tech best rank by **A-specific DiD**: 1
- known-tech best rank by **prevalence baseline**: 5
- **PASS** (top-3 by DiD and DiD rank <= baseline rank)

### vs Poison  (known: ['board_sweeper'], reported-only)

| role                     | A-specific | eff_vsA | eff_field | strata | support | prev_vsA |
|---|---|---|---|---|---|---|
| land_destruction         | +0.0580 | +0.0527 | -0.0053 | 5 | 30701 | 0.527 |
| artifact_enchant_removal | +0.0476 | +0.0417 | -0.0059 | 5 | 32947 | 0.838 |
| graveyard_hate           | +0.0102 | -0.0094 | -0.0196 | 8 | 44238 | 0.698 |
| creature_removal         | +0.0000 | +0.0000 | +0.0000 | 0 | 0 | 0.995 |
| mana_denial              | -0.0003 | -0.0058 | -0.0054 | 1 | 6188 | 0.039 |
| board_sweeper            | -0.0220 | -0.0225 | -0.0005 | 6 | 37392 | 0.556 |
| counter_ability          | -0.0414 | -0.0222 | +0.0192 | 4 | 28348 | 0.451 |
| hand_disruption          | -0.0464 | -0.0600 | -0.0136 | 4 | 30594 | 0.341 |
| counter_spell            | -0.1240 | -0.0890 | +0.0350 | 3 | 18869 | 0.638 |

- known-tech best rank by **A-specific DiD**: 6
- known-tech best rank by **prevalence baseline**: 5
- **MISS** (top-3 by DiD and DiD rank <= baseline rank)

### vs Artifact Aggro  (known: ['artifact_enchant_removal'], reported-only)

| role                     | A-specific | eff_vsA | eff_field | strata | support | prev_vsA |
|---|---|---|---|---|---|---|
| counter_spell            | +0.1385 | +0.1754 | +0.0369 | 1 | 11346 | 0.538 |
| counter_ability          | +0.0334 | +0.0677 | +0.0343 | 2 | 18831 | 0.312 |
| hand_disruption          | +0.0111 | -0.0138 | -0.0249 | 1 | 7485 | 0.396 |
| board_sweeper            | +0.0090 | -0.0037 | -0.0126 | 2 | 17598 | 0.478 |
| mana_denial              | +0.0000 | +0.0000 | +0.0000 | 0 | 0 | 0.027 |
| creature_removal         | +0.0000 | +0.0000 | +0.0000 | 0 | 0 | 0.983 |
| graveyard_hate           | -0.0027 | -0.0125 | -0.0099 | 4 | 30315 | 0.647 |
| land_destruction         | -0.0618 | -0.0756 | -0.0138 | 2 | 17875 | 0.357 |
| artifact_enchant_removal | -0.0765 | -0.0882 | -0.0117 | 2 | 17875 | 0.804 |

- known-tech best rank by **A-specific DiD**: 9
- known-tech best rank by **prevalence baseline**: 2
- **MISS** (top-3 by DiD and DiD rank <= baseline rank)

### vs Aggro  (known: ['board_sweeper'], reported-only)

| role                     | A-specific | eff_vsA | eff_field | strata | support | prev_vsA |
|---|---|---|---|---|---|---|
| land_destruction         | +0.0450 | +0.0295 | -0.0155 | 9 | 40396 | 0.379 |
| artifact_enchant_removal | +0.0309 | +0.0141 | -0.0167 | 4 | 26418 | 0.839 |
| board_sweeper            | +0.0265 | +0.0115 | -0.0150 | 11 | 44081 | 0.530 |
| graveyard_hate           | +0.0157 | -0.0056 | -0.0212 | 14 | 51099 | 0.709 |
| hand_disruption          | +0.0007 | -0.0076 | -0.0083 | 6 | 32548 | 0.413 |
| creature_removal         | +0.0000 | +0.0000 | +0.0000 | 0 | 0 | 0.992 |
| counter_ability          | -0.0120 | +0.0129 | +0.0249 | 7 | 41502 | 0.387 |
| counter_spell            | -0.0311 | +0.0085 | +0.0395 | 8 | 29371 | 0.640 |
| mana_denial              | -0.0554 | -0.0553 | +0.0001 | 1 | 6188 | 0.025 |

- known-tech best rank by **A-specific DiD**: 3
- known-tech best rank by **prevalence baseline**: 5
- **PASS** (top-3 by DiD and DiD rank <= baseline rank)

## B1 — temporal reproducibility (disjoint blocks): does the primary role keep a positive, top-k A-specific effect on both halves?

### vs Reanimator, primary role `graveyard_hate`  (GATED)

| block | A-specific | strata | rank |
|---|---|---|---|
| 2024-01-01..2024-12-31 | +0.0145 | 7 | 4 |
| 2025-01-01..2026-12-31 | +0.0000 | 0 | None |

- **MISS** (positive and top-k on both blocks)

### vs Oculus, primary role `graveyard_hate`  (GATED)

| block | A-specific | strata | rank |
|---|---|---|---|
| 2024-01-01..2024-12-31 | -0.0649 | 1 | 7 |
| 2025-01-01..2026-12-31 | +0.0000 | 0 | None |

- **MISS** (positive and top-k on both blocks)

### vs Demons, primary role `graveyard_hate`  (reported-only)

| block | A-specific | strata | rank |
|---|---|---|---|
| 2024-01-01..2024-12-31 | -0.1222 | 1 | 8 |
| 2025-01-01..2026-12-31 | +0.0000 | 0 | None |

- **MISS** (positive and top-k on both blocks)

### vs Boros Convoke, primary role `board_sweeper`  (GATED)

| block | A-specific | strata | rank |
|---|---|---|---|
| 2024-01-01..2024-12-31 | -0.0117 | 7 | 8 |
| 2025-01-01..2026-12-31 | +0.0000 | 0 | None |

- **MISS** (positive and top-k on both blocks)

### vs Convoke, primary role `board_sweeper`  (reported-only)

| block | A-specific | strata | rank |
|---|---|---|---|
| 2024-01-01..2024-12-31 | +0.0724 | 2 | 1 |
| 2025-01-01..2026-12-31 | +0.0000 | 0 | None |

- **MISS** (positive and top-k on both blocks)

### vs Poison, primary role `board_sweeper`  (reported-only)

| block | A-specific | strata | rank |
|---|---|---|---|
| 2024-01-01..2024-12-31 | -0.0220 | 6 | 6 |
| 2025-01-01..2026-12-31 | +0.0000 | 0 | None |

- **MISS** (positive and top-k on both blocks)

### vs Artifact Aggro, primary role `artifact_enchant_removal`  (reported-only)

| block | A-specific | strata | rank |
|---|---|---|---|
| 2024-01-01..2024-12-31 | -0.0765 | 2 | 9 |
| 2025-01-01..2026-12-31 | +0.0000 | 0 | None |

- **MISS** (positive and top-k on both blocks)

### vs Aggro, primary role `board_sweeper`  (reported-only)

| block | A-specific | strata | rank |
|---|---|---|---|
| 2024-01-01..2024-12-31 | +0.0265 | 11 | 3 |
| 2025-01-01..2026-12-31 | +0.0000 | 0 | None |

- **MISS** (positive and top-k on both blocks)

## Verdict

Gated B2: 0/3 pass. Gated B1: 0/3 pass.

**TARGETS MISSED — see above; not lowered (CLAUDE.md)**

## Failure analysis — why Standard fails where Modern passed

**Root cause 1 — too few within-archetype strata (the binding constraint).**
The DiD averages a role's effect over the *player archetypes* that carry it both
with and without the role, in all four 2×2 cells at ≥20 decided rows each. On
Modern (347,438 rows) the gated targets had **15–31** contributing strata; on
Standard (62,458 rows) they have **1–3**. When a role's estimate rests on a
single archetype (`strata=1`), it is noise, not signal — and those thin-strata
roles routinely outrank the genuine effect. Example (vs Reanimator): the top
three roles by DiD are `counter_spell` (strata **1**), `counter_ability`
(strata 3), `mana_denial` (strata **1**); the real answer `graveyard_hate` is
the **best-supported** role (strata 7, the most decided rows) but ranks 4th
because single-archetype noise beats it. Standard simply does not have the match
volume × archetype diversity the within-archetype estimator needs.

**Root cause 2 — the go-wide targets are §4d's "muddy" creature-deck case, and
the method is right to reject them.** Vs Boros Convoke the DiD does **not** rank
`board_sweeper` as A-specific (−0.012, 7 strata) — correctly: sweepers help vs
*every* creature deck, so their Convoke-specific effect (over-and-above the
field) is ~0. That is the estimator working as designed (§4c/§4d); the miss is
in our a-priori label, which treated a *generic* answer as *tech*. Go-wide aggro
has no distinctive, non-generic weakness among our roles.

**Root cause 3 — Standard's hate is genuine but weak.** Where sample allows a
read (Reanimator), `graveyard_hate` is positive (+0.0145, field −0.013) — the
right sign — but small. Standard is a lower-power format: dedicated graveyard
hate (Ghost Vacuum, Unlicensed Hearse) sees low, situational play and bites less
than Modern's Rest in Peace / Leyline, so even a clean estimate would be modest.

## What this establishes

The tech finder needs **both** (a) large match volume with many player-archetype
strata, and (b) opponents with a genuinely distinctive, non-generic weakness.
Modern (high-power, dedicated hate cards, deep data) supplies both; **Standard
2024–25 on this data supplies neither**, so the method does not transfer here.
This delineates the tool's domain: high-power eternal formats (Modern, and
likely Legacy/Vintage/Pioneer) with rich match data — not low-power Standard,
and not any format below a strata-density floor.

**Deliberately NOT changed post-hoc (CLAUDE.md):** the pre-registered thresholds,
the a-priori target/role assignments, and the block split. Two clear follow-ups
for a *future* pre-registration, not this run: (1) require a minimum `n_strata`
(e.g. ≥3) for a role to be ranked, so single-archetype noise can't top the list
— this would sharpen every format; (2) restrict Standard targets to archetypes
with a distinctive weakness and enough sample, or pool eras/sources for volume.

## Reproduce

```
python scripts/materialize_card_roles.py            # roles incl. Standard fixtures
python -m validation.tech_finder --format standard   # this report
```
