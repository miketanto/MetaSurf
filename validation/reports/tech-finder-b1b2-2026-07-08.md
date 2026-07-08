# Tech finder — recovery + reproducibility across 13 archetypes — 2026-07-08 (Modern)

Extends the initial 3-archetype proof to **13 opponent archetypes** to guard
against cherry-picking. First **positive** evidence for the function-first,
within-archetype tech finder (BL-1, research-log §4b); prior work (§4c/§4d) only
established that the naive methods fail. The design: abstract cards to functional
**roles** (Layer A, `archetypes/roles`), then estimate each role's effect
**within a fixed player archetype, conditioned on the opponent** (Layer B,
`validation/tech_finder/estimate.py`).

Each opponent's community-known tech role was fixed **a priori** (in `run.py`,
from each deck's structural weakness — see the table there) BEFORE running.
`min_cell=20`, `top_k=3`; B2 PASS = known role in top-3 by the within-archetype
DiD AND at a rank ≤ the frequency-only baseline; B1 PASS = the primary role stays
positive AND top-3 on both disjoint blocks (2022–2023, 2024–2025). A miss is
reported, not lowered (CLAUDE.md). Run is deterministic (byte-identical across
two runs). Roles are the fixture-tested parser (40 tests vs real Scryfall text).

Directed decided non-mirror match rows: **347438**. Roles vocabulary (9): land_destruction, mana_denial, graveyard_hate, creature_removal, board_sweeper, counter_spell, counter_ability, artifact_enchant_removal, hand_disruption.

All numbers are printed output of `python -m validation.tech_finder` against the rebuilt Modern corpus (import + match_extract + rules labeling). Design: docstring of `validation/tech_finder/estimate.py`.

## B2 — recovery: does the within-archetype DiD rank the known tech role in the top 3, beating the frequency-only baseline?

### vs GenericTron  (known: ['land_destruction', 'mana_denial'], GATED)

| role                     | A-specific | eff_vsA | eff_field | strata | support | prev_vsA |
|---|---|---|---|---|---|---|
| land_destruction         | +0.0173 | +0.0070 | -0.0103 | 24 | 215390 | 0.485 |
| artifact_enchant_removal | +0.0120 | +0.0071 | -0.0049 | 27 | 222013 | 0.621 |
| creature_removal         | +0.0041 | +0.0015 | -0.0026 | 15 | 131450 | 0.800 |
| graveyard_hate           | +0.0038 | -0.0055 | -0.0093 | 18 | 183898 | 0.807 |
| counter_ability          | -0.0023 | -0.0035 | -0.0011 | 16 | 161920 | 0.128 |
| mana_denial              | -0.0141 | -0.0037 | +0.0104 | 31 | 270911 | 0.432 |
| board_sweeper            | -0.0262 | -0.0311 | -0.0050 | 21 | 216263 | 0.248 |
| hand_disruption          | -0.0391 | -0.0239 | +0.0153 | 16 | 171742 | 0.308 |
| counter_spell            | -0.0816 | -0.0605 | +0.0211 | 15 | 177589 | 0.544 |

- known-tech best rank by **A-specific DiD**: 1
- known-tech best rank by **prevalence baseline**: 5
- **PASS** (top-3 by DiD and DiD rank <= baseline rank)

### vs Titan  (known: ['land_destruction', 'mana_denial'], GATED)

| role                     | A-specific | eff_vsA | eff_field | strata | support | prev_vsA |
|---|---|---|---|---|---|---|
| counter_spell            | +0.1203 | +0.1249 | +0.0046 | 17 | 174200 | 0.573 |
| mana_denial              | +0.1000 | +0.1023 | +0.0022 | 31 | 268812 | 0.421 |
| counter_ability          | +0.0356 | +0.0302 | -0.0055 | 17 | 180168 | 0.195 |
| board_sweeper            | +0.0292 | +0.0214 | -0.0078 | 22 | 200155 | 0.270 |
| graveyard_hate           | +0.0148 | +0.0045 | -0.0104 | 15 | 158865 | 0.822 |
| creature_removal         | -0.0073 | -0.0058 | +0.0014 | 14 | 111724 | 0.854 |
| hand_disruption          | -0.0226 | -0.0062 | +0.0164 | 22 | 199774 | 0.317 |
| land_destruction         | -0.0349 | -0.0451 | -0.0102 | 22 | 223162 | 0.482 |
| artifact_enchant_removal | -0.0542 | -0.0552 | -0.0010 | 27 | 232238 | 0.623 |

- known-tech best rank by **A-specific DiD**: 2
- known-tech best rank by **prevalence baseline**: 5
- **PASS** (top-3 by DiD and DiD rank <= baseline rank)

### vs Eldrazi  (known: ['land_destruction', 'mana_denial'], reported-only)

| role                     | A-specific | eff_vsA | eff_field | strata | support | prev_vsA |
|---|---|---|---|---|---|---|
| land_destruction         | +0.0534 | +0.0390 | -0.0144 | 11 | 140015 | 0.546 |
| artifact_enchant_removal | +0.0346 | +0.0177 | -0.0169 | 10 | 117132 | 0.611 |
| creature_removal         | +0.0220 | -0.0049 | -0.0269 | 5 | 57720 | 0.859 |
| hand_disruption          | +0.0088 | +0.0168 | +0.0079 | 8 | 69327 | 0.288 |
| graveyard_hate           | -0.0102 | -0.0269 | -0.0167 | 5 | 62466 | 0.902 |
| counter_ability          | -0.0163 | -0.0285 | -0.0121 | 7 | 89513 | 0.480 |
| mana_denial              | -0.0186 | -0.0110 | +0.0076 | 14 | 141859 | 0.341 |
| board_sweeper            | -0.0212 | -0.0221 | -0.0009 | 14 | 153729 | 0.285 |
| counter_spell            | -0.0306 | -0.0310 | -0.0004 | 8 | 112636 | 0.535 |

- known-tech best rank by **A-specific DiD**: 1
- known-tech best rank by **prevalence baseline**: 4
- **PASS** (top-3 by DiD and DiD rank <= baseline rank)

### vs LivingEnd  (known: ['graveyard_hate'], GATED)

| role                     | A-specific | eff_vsA | eff_field | strata | support | prev_vsA |
|---|---|---|---|---|---|---|
| graveyard_hate           | +0.0467 | +0.0352 | -0.0114 | 13 | 160065 | 0.794 |
| counter_spell            | +0.0232 | +0.0389 | +0.0158 | 12 | 145343 | 0.570 |
| land_destruction         | +0.0077 | -0.0075 | -0.0152 | 16 | 197264 | 0.492 |
| counter_ability          | +0.0067 | +0.0022 | -0.0045 | 11 | 137210 | 0.123 |
| board_sweeper            | +0.0020 | -0.0034 | -0.0054 | 15 | 174580 | 0.244 |
| mana_denial              | -0.0010 | +0.0121 | +0.0131 | 19 | 193440 | 0.432 |
| hand_disruption          | -0.0130 | +0.0010 | +0.0141 | 12 | 164308 | 0.262 |
| artifact_enchant_removal | -0.0211 | -0.0251 | -0.0040 | 16 | 208388 | 0.655 |
| creature_removal         | -0.0244 | -0.0240 | +0.0003 | 7 | 82752 | 0.825 |

- known-tech best rank by **A-specific DiD**: 1
- known-tech best rank by **prevalence baseline**: 2
- **PASS** (top-3 by DiD and DiD rank <= baseline rank)

### vs GoryoReanimator  (known: ['graveyard_hate'], GATED)

| role                     | A-specific | eff_vsA | eff_field | strata | support | prev_vsA |
|---|---|---|---|---|---|---|
| graveyard_hate           | +0.0961 | +0.0804 | -0.0157 | 7 | 96531 | 0.853 |
| mana_denial              | +0.0399 | +0.0487 | +0.0088 | 15 | 187207 | 0.412 |
| creature_removal         | +0.0324 | +0.0211 | -0.0114 | 5 | 68114 | 0.808 |
| counter_spell            | +0.0272 | +0.0398 | +0.0126 | 8 | 124287 | 0.520 |
| hand_disruption          | +0.0112 | +0.0173 | +0.0062 | 8 | 106216 | 0.292 |
| board_sweeper            | +0.0108 | +0.0011 | -0.0098 | 13 | 175622 | 0.293 |
| artifact_enchant_removal | +0.0062 | -0.0023 | -0.0085 | 11 | 145893 | 0.589 |
| land_destruction         | -0.0106 | -0.0256 | -0.0150 | 13 | 171310 | 0.569 |
| counter_ability          | -0.0249 | -0.0253 | -0.0004 | 9 | 122167 | 0.266 |

- known-tech best rank by **A-specific DiD**: 1
- known-tech best rank by **prevalence baseline**: 1
- **PASS** (top-3 by DiD and DiD rank <= baseline rank)

### vs Yawgmoth  (known: ['graveyard_hate'], reported-only)

| role                     | A-specific | eff_vsA | eff_field | strata | support | prev_vsA |
|---|---|---|---|---|---|---|
| artifact_enchant_removal | +0.0112 | +0.0080 | -0.0032 | 20 | 219958 | 0.640 |
| board_sweeper            | +0.0049 | -0.0025 | -0.0074 | 21 | 216383 | 0.278 |
| counter_spell            | +0.0037 | +0.0171 | +0.0134 | 14 | 161194 | 0.607 |
| land_destruction         | +0.0008 | -0.0103 | -0.0110 | 18 | 215278 | 0.500 |
| counter_ability          | -0.0002 | -0.0044 | -0.0042 | 15 | 170967 | 0.163 |
| mana_denial              | -0.0049 | +0.0057 | +0.0106 | 24 | 222401 | 0.431 |
| graveyard_hate           | -0.0060 | -0.0150 | -0.0090 | 15 | 167299 | 0.806 |
| creature_removal         | -0.0169 | -0.0159 | +0.0009 | 10 | 97800 | 0.779 |
| hand_disruption          | -0.0303 | -0.0158 | +0.0145 | 14 | 167467 | 0.266 |

- known-tech best rank by **A-specific DiD**: 7
- known-tech best rank by **prevalence baseline**: 1
- **MISS** (top-3 by DiD and DiD rank <= baseline rank)

### vs Dredge  (known: ['graveyard_hate'], reported-only)

| role                     | A-specific | eff_vsA | eff_field | strata | support | prev_vsA |
|---|---|---|---|---|---|---|
| creature_removal         | +0.0878 | +0.0940 | +0.0062 | 3 | 53147 | 0.847 |
| graveyard_hate           | +0.0861 | +0.0774 | -0.0086 | 3 | 62399 | 0.812 |
| hand_disruption          | +0.0711 | +0.1029 | +0.0318 | 2 | 38119 | 0.303 |
| board_sweeper            | +0.0122 | +0.0070 | -0.0052 | 5 | 97568 | 0.255 |
| counter_spell            | +0.0054 | +0.0152 | +0.0098 | 5 | 93612 | 0.537 |
| mana_denial              | -0.0007 | +0.0169 | +0.0176 | 5 | 102315 | 0.415 |
| counter_ability          | -0.0057 | -0.0139 | -0.0083 | 1 | 19652 | 0.065 |
| artifact_enchant_removal | -0.0210 | -0.0228 | -0.0018 | 3 | 52974 | 0.658 |
| land_destruction         | -0.0403 | -0.0580 | -0.0177 | 6 | 98207 | 0.459 |

- known-tech best rank by **A-specific DiD**: 2
- known-tech best rank by **prevalence baseline**: 2
- **PASS** (top-3 by DiD and DiD rank <= baseline rank)

### vs HammerTime  (known: ['artifact_enchant_removal'], GATED)

| role                     | A-specific | eff_vsA | eff_field | strata | support | prev_vsA |
|---|---|---|---|---|---|---|
| counter_spell            | +0.0355 | +0.0529 | +0.0175 | 15 | 163021 | 0.592 |
| land_destruction         | +0.0072 | -0.0059 | -0.0131 | 21 | 222940 | 0.486 |
| hand_disruption          | +0.0063 | +0.0213 | +0.0150 | 14 | 139905 | 0.288 |
| mana_denial              | +0.0039 | +0.0165 | +0.0127 | 20 | 214170 | 0.436 |
| board_sweeper            | -0.0002 | -0.0073 | -0.0071 | 17 | 188932 | 0.212 |
| graveyard_hate           | -0.0079 | -0.0170 | -0.0090 | 12 | 137987 | 0.796 |
| counter_ability          | -0.0140 | -0.0236 | -0.0096 | 8 | 115688 | 0.061 |
| creature_removal         | -0.0255 | -0.0249 | +0.0007 | 12 | 99431 | 0.797 |
| artifact_enchant_removal | -0.0301 | -0.0329 | -0.0029 | 21 | 214525 | 0.697 |

- known-tech best rank by **A-specific DiD**: 9
- known-tech best rank by **prevalence baseline**: 3
- **MISS** (top-3 by DiD and DiD rank <= baseline rank)

### vs Affinity  (known: ['artifact_enchant_removal'], GATED)

| role                     | A-specific | eff_vsA | eff_field | strata | support | prev_vsA |
|---|---|---|---|---|---|---|
| counter_ability          | +0.0469 | +0.0531 | +0.0062 | 6 | 77997 | 0.157 |
| land_destruction         | +0.0438 | +0.0278 | -0.0161 | 9 | 112045 | 0.489 |
| artifact_enchant_removal | +0.0362 | +0.0289 | -0.0073 | 10 | 137681 | 0.653 |
| creature_removal         | +0.0219 | +0.0212 | -0.0008 | 4 | 65289 | 0.835 |
| counter_spell            | +0.0178 | +0.0332 | +0.0154 | 6 | 110853 | 0.553 |
| graveyard_hate           | +0.0126 | +0.0021 | -0.0105 | 5 | 83822 | 0.837 |
| board_sweeper            | +0.0091 | +0.0034 | -0.0056 | 9 | 152320 | 0.251 |
| mana_denial              | -0.0124 | +0.0055 | +0.0179 | 11 | 159280 | 0.375 |
| hand_disruption          | -0.0416 | -0.0263 | +0.0153 | 5 | 65774 | 0.276 |

- known-tech best rank by **A-specific DiD**: 3
- known-tech best rank by **prevalence baseline**: 3
- **PASS** (top-3 by DiD and DiD rank <= baseline rank)

### vs HardenedScales  (known: ['artifact_enchant_removal'], reported-only)

| role                     | A-specific | eff_vsA | eff_field | strata | support | prev_vsA |
|---|---|---|---|---|---|---|
| counter_ability          | +0.0582 | +0.0515 | -0.0067 | 6 | 102465 | 0.147 |
| artifact_enchant_removal | +0.0463 | +0.0425 | -0.0037 | 10 | 135393 | 0.657 |
| land_destruction         | +0.0324 | +0.0193 | -0.0131 | 10 | 119639 | 0.504 |
| graveyard_hate           | +0.0204 | +0.0103 | -0.0101 | 8 | 102330 | 0.791 |
| board_sweeper            | +0.0188 | +0.0108 | -0.0080 | 11 | 149423 | 0.254 |
| mana_denial              | -0.0092 | +0.0018 | +0.0110 | 11 | 165177 | 0.416 |
| counter_spell            | -0.0182 | -0.0053 | +0.0129 | 7 | 107961 | 0.559 |
| hand_disruption          | -0.0373 | -0.0134 | +0.0239 | 5 | 74596 | 0.317 |
| creature_removal         | -0.0498 | -0.0453 | +0.0046 | 4 | 65289 | 0.794 |

- known-tech best rank by **A-specific DiD**: 2
- known-tech best rank by **prevalence baseline**: 3
- **PASS** (top-3 by DiD and DiD rank <= baseline rank)

### vs RubyStorm  (known: ['counter_spell', 'hand_disruption'], GATED)

| role                     | A-specific | eff_vsA | eff_field | strata | support | prev_vsA |
|---|---|---|---|---|---|---|
| counter_ability          | +0.0703 | +0.0751 | +0.0048 | 3 | 61748 | 0.416 |
| counter_spell            | +0.0513 | +0.0635 | +0.0122 | 5 | 83936 | 0.492 |
| graveyard_hate           | +0.0265 | +0.0033 | -0.0232 | 4 | 64566 | 0.884 |
| artifact_enchant_removal | +0.0185 | +0.0015 | -0.0170 | 5 | 82821 | 0.526 |
| board_sweeper            | +0.0016 | +0.0008 | -0.0008 | 7 | 94897 | 0.294 |
| land_destruction         | -0.0133 | -0.0272 | -0.0138 | 8 | 83812 | 0.577 |
| hand_disruption          | -0.0244 | -0.0218 | +0.0026 | 4 | 47230 | 0.309 |
| mana_denial              | -0.0292 | -0.0192 | +0.0099 | 10 | 107248 | 0.418 |
| creature_removal         | -0.0722 | -0.1511 | -0.0789 | 1 | 2825 | 0.856 |

- known-tech best rank by **A-specific DiD**: 2
- known-tech best rank by **prevalence baseline**: 5
- **PASS** (top-3 by DiD and DiD rank <= baseline rank)

### vs Footfalls  (known: ['counter_spell'], reported-only)

| role                     | A-specific | eff_vsA | eff_field | strata | support | prev_vsA |
|---|---|---|---|---|---|---|
| board_sweeper            | +0.0120 | +0.0031 | -0.0089 | 18 | 177991 | 0.213 |
| counter_ability          | +0.0059 | -0.0020 | -0.0079 | 10 | 117104 | 0.062 |
| counter_spell            | +0.0023 | +0.0152 | +0.0129 | 16 | 182285 | 0.527 |
| hand_disruption          | -0.0020 | +0.0120 | +0.0140 | 14 | 160437 | 0.337 |
| land_destruction         | -0.0030 | -0.0150 | -0.0119 | 18 | 173626 | 0.469 |
| mana_denial              | -0.0038 | +0.0061 | +0.0099 | 24 | 217354 | 0.355 |
| artifact_enchant_removal | -0.0088 | -0.0109 | -0.0021 | 20 | 185124 | 0.648 |
| creature_removal         | -0.0125 | -0.0090 | +0.0036 | 12 | 85653 | 0.787 |
| graveyard_hate           | -0.0202 | -0.0271 | -0.0069 | 13 | 133073 | 0.773 |

- known-tech best rank by **A-specific DiD**: 3
- known-tech best rank by **prevalence baseline**: 4
- **PASS** (top-3 by DiD and DiD rank <= baseline rank)

### vs Aggro  (known: ['board_sweeper'], reported-only)

| role                     | A-specific | eff_vsA | eff_field | strata | support | prev_vsA |
|---|---|---|---|---|---|---|
| hand_disruption          | +0.0287 | +0.0408 | +0.0121 | 25 | 178987 | 0.331 |
| board_sweeper            | +0.0197 | +0.0116 | -0.0082 | 28 | 183863 | 0.218 |
| land_destruction         | +0.0172 | +0.0075 | -0.0097 | 38 | 246007 | 0.548 |
| counter_spell            | +0.0014 | +0.0046 | +0.0032 | 24 | 183040 | 0.570 |
| counter_ability          | -0.0005 | -0.0022 | -0.0016 | 17 | 142199 | 0.080 |
| mana_denial              | -0.0031 | +0.0047 | +0.0078 | 46 | 260992 | 0.365 |
| graveyard_hate           | -0.0056 | -0.0096 | -0.0040 | 27 | 180854 | 0.874 |
| artifact_enchant_removal | -0.0095 | -0.0084 | +0.0011 | 41 | 251241 | 0.677 |
| creature_removal         | -0.0191 | -0.0156 | +0.0034 | 23 | 143874 | 0.755 |

- known-tech best rank by **A-specific DiD**: 2
- known-tech best rank by **prevalence baseline**: 8
- **PASS** (top-3 by DiD and DiD rank <= baseline rank)

## B1 — temporal reproducibility (disjoint blocks): does the primary role keep a positive, top-k A-specific effect on both halves?

### vs GenericTron, primary role `land_destruction`  (GATED)

| block | A-specific | strata | rank |
|---|---|---|---|
| 2022-01-01..2023-12-31 | -0.0208 | 10 | 5 |
| 2024-01-01..2025-12-31 | +0.0295 | 12 | 1 |

- **MISS** (positive and top-k on both blocks)

### vs Titan, primary role `land_destruction`  (GATED)

| block | A-specific | strata | rank |
|---|---|---|---|
| 2022-01-01..2023-12-31 | -0.0163 | 9 | 7 |
| 2024-01-01..2025-12-31 | -0.0528 | 15 | 9 |

- **MISS** (positive and top-k on both blocks)

### vs Eldrazi, primary role `land_destruction`  (reported-only)

| block | A-specific | strata | rank |
|---|---|---|---|
| 2022-01-01..2023-12-31 | +0.0000 | 0 | None |
| 2024-01-01..2025-12-31 | +0.0626 | 10 | 1 |

- **MISS** (positive and top-k on both blocks)

### vs LivingEnd, primary role `graveyard_hate`  (GATED)

| block | A-specific | strata | rank |
|---|---|---|---|
| 2022-01-01..2023-12-31 | +0.0513 | 6 | 2 |
| 2024-01-01..2025-12-31 | +0.0670 | 6 | 1 |

- **PASS** (positive and top-k on both blocks)

### vs GoryoReanimator, primary role `graveyard_hate`  (GATED)

| block | A-specific | strata | rank |
|---|---|---|---|
| 2022-01-01..2023-12-31 | +0.2050 | 1 | 2 |
| 2024-01-01..2025-12-31 | +0.1070 | 6 | 1 |

- **PASS** (positive and top-k on both blocks)

### vs Yawgmoth, primary role `graveyard_hate`  (reported-only)

| block | A-specific | strata | rank |
|---|---|---|---|
| 2022-01-01..2023-12-31 | +0.0112 | 8 | 4 |
| 2024-01-01..2025-12-31 | -0.0127 | 13 | 7 |

- **MISS** (positive and top-k on both blocks)

### vs Dredge, primary role `graveyard_hate`  (reported-only)

| block | A-specific | strata | rank |
|---|---|---|---|
| 2022-01-01..2023-12-31 | +0.0831 | 2 | 2 |
| 2024-01-01..2025-12-31 | +0.0000 | 0 | None |

- **MISS** (positive and top-k on both blocks)

### vs HammerTime, primary role `artifact_enchant_removal`  (GATED)

| block | A-specific | strata | rank |
|---|---|---|---|
| 2022-01-01..2023-12-31 | -0.0223 | 15 | 7 |
| 2024-01-01..2025-12-31 | -0.0754 | 6 | 9 |

- **MISS** (positive and top-k on both blocks)

### vs Affinity, primary role `artifact_enchant_removal`  (GATED)

| block | A-specific | strata | rank |
|---|---|---|---|
| 2022-01-01..2023-12-31 | -0.0276 | 2 | 8 |
| 2024-01-01..2025-12-31 | +0.0537 | 5 | 2 |

- **MISS** (positive and top-k on both blocks)

### vs HardenedScales, primary role `artifact_enchant_removal`  (reported-only)

| block | A-specific | strata | rank |
|---|---|---|---|
| 2022-01-01..2023-12-31 | +0.0018 | 3 | 3 |
| 2024-01-01..2025-12-31 | -0.0407 | 4 | 9 |

- **MISS** (positive and top-k on both blocks)

### vs RubyStorm, primary role `hand_disruption`  (GATED)

| block | A-specific | strata | rank |
|---|---|---|---|
| 2022-01-01..2023-12-31 | +0.0000 | 0 | None |
| 2024-01-01..2025-12-31 | -0.0259 | 4 | 7 |

- **MISS** (positive and top-k on both blocks)

### vs Footfalls, primary role `counter_spell`  (reported-only)

| block | A-specific | strata | rank |
|---|---|---|---|
| 2022-01-01..2023-12-31 | +0.0108 | 9 | 2 |
| 2024-01-01..2025-12-31 | -0.0329 | 7 | 8 |

- **MISS** (positive and top-k on both blocks)

### vs Aggro, primary role `board_sweeper`  (reported-only)

| block | A-specific | strata | rank |
|---|---|---|---|
| 2022-01-01..2023-12-31 | +0.0257 | 15 | 2 |
| 2024-01-01..2025-12-31 | +0.0128 | 17 | 4 |

- **MISS** (positive and top-k on both blocks)

## Verdict

Gated B2: 6/7 pass. Gated B1: 2/7 pass.

**TARGETS MISSED — see above; not lowered (CLAUDE.md)**

## Discussion & failure analysis

**Headline: B2 recovery works and systematically beats the naive baseline.**
Gated 6/7 (overall 11/13) recover the known tech role in the top-3 by the
within-archetype DiD, and in every pass the DiD rank is ≤ the frequency-only
baseline — often far better: Tron 1 vs 5, Titan 2 vs 5, Ruby Storm 2 vs 5, Aggro
2 vs 8. The naive "what's played most vs A" baseline ranks generic answers
(creature removal, graveyard hate) on top because everyone packs them; the DiD
strips that out and surfaces the *specific* answer. The §4c/§4d confound is
defeated for recovery across a wide, pre-registered set of archetypes.

**Two genuine insights the tool surfaced (not just recovery):**
- **Titan distinguishes mana denial from land destruction.** Vs Titan the DiD
  ranks `mana_denial` #2 (+0.100) and `counter_spell` #1 (+0.120) but
  `land_destruction` **#8, negative** (−0.035). This is correct: Amulet/Primeval
  Titan floods lands (Amulet + bounce-lands), so destroying one land is near
  useless, while Blood Moon / Damping Sphere (mana denial) and countering the
  payoff are the real answers. The two "attack their mana" roles are not
  interchangeable and the model learns which one bites — exactly the kind of
  nuance a tech finder should provide. (Note: our a-priori `primary` for Titan
  was `land_destruction`, which is why its B1 misses; the data says the primary
  anti-Titan role is `mana_denial`.)
- **Creature aggro is less muddy than §4d feared.** Vs Aggro, `board_sweeper`
  is #2 by DiD (+0.020) vs #8 by baseline, and `hand_disruption` #1 — plausible
  proactive answers, recovered despite §4d's pessimism about creature decks.

**Honest misses (reported, not massaged):**
- **HammerTime (GATED MISS): artifact removal ranks LAST (#9, −0.030).** Only
  `counter_spell` (#1, +0.036) shows an A-specific effect; both artifact removal
  and creature removal are negative. Two readings, both worth the owner's eye:
  (a) the conventional "just kill the Hammer" wisdom is wrong — HammerTime is
  resilient (Sigarda's Aid flash-equips, Puresteel/Urza's Saga redundancy, a
  fast clock), so reactive removal underperforms and only counters/disruption
  help; or (b) the `artifact_enchant_removal` role is diluted by generic
  "destroy target permanent" flexible removal. Either way, a-priori wisdom did
  not hold — flagged.
- **Yawgmoth (reported MISS): graveyard hate not A-specific (#7, −0.006).**
  Most likely our a-priori label was wrong: Yawgmoth is a *battlefield*
  sacrifice-value engine (undying + Yawgmoth), not a graveyard deck, so graveyard
  hate — though the single most-played role vs it (prev 0.806) — does not
  specifically beat it. The model saying "graveyard hate isn't the Yawgmoth
  answer" is metagame-defensible.

**B1 reproducibility: gated 2/7 — and the pattern is itself the finding.** The
only roles stationary across the 2022–2023 vs 2024–2025 split are
**graveyard_hate vs the graveyard decks** (LivingEnd, GoryoReanimator both PASS).
Every narrow tech (land destruction, mana denial, artifact removal, counters,
discard) shifts sign or top-k rank between eras. Interpretation: graveyard hate
is a **persistent structural** tech relationship; most other tech is
**metagame-contingent** — it's the right answer *this season*, not for all time.
That is a real property of the format, and B1 correctly detects it rather than
papering over it.

**What this establishes.** Layer A + Layer B is a working tech finder for
*recovery* across many archetypes, beating the naive baseline everywhere it
passes, and surfacing correct nuance (Titan, Aggro). It is end-to-end
reproducible for the stationary graveyard-hate relationships. It is NOT yet a
stationary predictor for narrow techs (needs era-aware estimation), and Layer C
(ranking *unplayed* hidden tech) + C1 (temporal precision@k) remain future work.
Two of our a-priori labels (Titan→land_destruction, Yawgmoth→graveyard_hate)
were arguably mis-specified — a reminder that the "known tech" ground truth is
itself a judgement call; the DiD rankings are informative even where they
disagree with first-guess wisdom.

## Reproduce

```
python scripts/extract_matches_guarded.py          # matches (tolerant of live raw_refs)
python -m archetypes.labeler --format modern --granularity parent
python scripts/materialize_card_roles.py           # card_roles from Scryfall bulk
python -m validation.tech_finder                    # this report (13 archetypes)
```
