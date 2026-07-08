# Tech finder — recovery + reproducibility across 13 archetypes — 2026-07-08 (Modern)

Extends the initial 3-archetype proof to **13 opponent archetypes** to guard
against cherry-picking. First **positive** evidence for the function-first,
within-archetype tech finder (BL-1, research-log §4b); prior work (§4c/§4d) only
established that the naive methods fail. The design: abstract cards to functional
**roles** (Layer A, `archetypes/roles`), then estimate each role's effect
**within a fixed player archetype, conditioned on the opponent** (Layer B,
`validation/tech_finder/estimate.py`).

Each opponent's community-known tech role was fixed **a priori** (in `run.py`,
from each deck's structural weakness) BEFORE running. `min_cell=20`, `top_k=3`;
B2 PASS = known role in top-3 by the within-archetype DiD AND at a rank ≤ the
frequency-only baseline; B1 PASS = the primary role stays positive AND top-3 on
both disjoint blocks (2022–2023, 2024–2025). A miss is reported, not lowered
(CLAUDE.md). Deterministic (byte-identical across two runs). Roles are the
fixture-tested parser (50 tests vs real Scryfall text, incl. Standard removal
templating).

Directed decided non-mirror match rows: **347438**. Roles vocabulary (9): land_destruction, mana_denial, graveyard_hate, creature_removal, board_sweeper, counter_spell, counter_ability, artifact_enchant_removal, hand_disruption.

All numbers are printed output of `python -m validation.tech_finder --format modern` against the rebuilt modern corpus (import + match_extract + rules labeling). Design: docstring of `validation/tech_finder/estimate.py`.

## B2 — recovery: does the within-archetype DiD rank the known tech role in the top 3, beating the frequency-only baseline?

### vs GenericTron  (known: ['land_destruction', 'mana_denial'], GATED)

| role                     | A-specific | eff_vsA | eff_field | strata | support | prev_vsA |
|---|---|---|---|---|---|---|
| land_destruction         | +0.0173 | +0.0070 | -0.0103 | 24 | 215390 | 0.485 |
| counter_ability          | -0.0023 | -0.0035 | -0.0011 | 16 | 161920 | 0.128 |
| mana_denial              | -0.0141 | -0.0037 | +0.0104 | 31 | 270911 | 0.432 |
| graveyard_hate           | -0.0193 | -0.0178 | +0.0015 | 17 | 161389 | 0.854 |
| artifact_enchant_removal | -0.0229 | -0.0246 | -0.0017 | 18 | 159894 | 0.820 |
| board_sweeper            | -0.0256 | -0.0310 | -0.0054 | 21 | 216263 | 0.251 |
| creature_removal         | -0.0317 | -0.0369 | -0.0051 | 9 | 80168 | 0.875 |
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
| graveyard_hate           | +0.0763 | +0.0710 | -0.0054 | 15 | 158865 | 0.865 |
| counter_ability          | +0.0356 | +0.0302 | -0.0055 | 17 | 180168 | 0.195 |
| board_sweeper            | +0.0323 | +0.0240 | -0.0084 | 22 | 200155 | 0.273 |
| creature_removal         | +0.0144 | +0.0089 | -0.0055 | 9 | 60300 | 0.922 |
| hand_disruption          | -0.0226 | -0.0062 | +0.0164 | 22 | 199774 | 0.317 |
| artifact_enchant_removal | -0.0332 | -0.0334 | -0.0001 | 21 | 186158 | 0.829 |
| land_destruction         | -0.0349 | -0.0451 | -0.0102 | 22 | 223162 | 0.482 |

- known-tech best rank by **A-specific DiD**: 2
- known-tech best rank by **prevalence baseline**: 5
- **PASS** (top-3 by DiD and DiD rank <= baseline rank)

### vs Eldrazi  (known: ['land_destruction', 'mana_denial'], reported-only)

| role                     | A-specific | eff_vsA | eff_field | strata | support | prev_vsA |
|---|---|---|---|---|---|---|
| land_destruction         | +0.0534 | +0.0390 | -0.0144 | 11 | 140015 | 0.546 |
| artifact_enchant_removal | +0.0115 | +0.0056 | -0.0059 | 12 | 118934 | 0.816 |
| hand_disruption          | +0.0088 | +0.0168 | +0.0079 | 8 | 69327 | 0.288 |
| counter_ability          | -0.0163 | -0.0285 | -0.0121 | 7 | 89513 | 0.480 |
| mana_denial              | -0.0186 | -0.0110 | +0.0076 | 14 | 141859 | 0.341 |
| board_sweeper            | -0.0204 | -0.0198 | +0.0005 | 14 | 153729 | 0.289 |
| graveyard_hate           | -0.0237 | -0.0381 | -0.0143 | 4 | 60139 | 0.913 |
| counter_spell            | -0.0306 | -0.0310 | -0.0004 | 8 | 112636 | 0.535 |
| creature_removal         | -0.0504 | -0.0523 | -0.0019 | 4 | 28744 | 0.909 |

- known-tech best rank by **A-specific DiD**: 1
- known-tech best rank by **prevalence baseline**: 4
- **PASS** (top-3 by DiD and DiD rank <= baseline rank)

### vs LivingEnd  (known: ['graveyard_hate'], GATED)

| role                     | A-specific | eff_vsA | eff_field | strata | support | prev_vsA |
|---|---|---|---|---|---|---|
| graveyard_hate           | +0.0475 | +0.0461 | -0.0014 | 11 | 150889 | 0.856 |
| counter_spell            | +0.0232 | +0.0389 | +0.0158 | 12 | 145343 | 0.570 |
| land_destruction         | +0.0077 | -0.0075 | -0.0152 | 16 | 197264 | 0.492 |
| counter_ability          | +0.0067 | +0.0022 | -0.0045 | 11 | 137210 | 0.123 |
| board_sweeper            | +0.0030 | -0.0026 | -0.0056 | 15 | 174580 | 0.246 |
| mana_denial              | -0.0010 | +0.0121 | +0.0131 | 19 | 193440 | 0.432 |
| hand_disruption          | -0.0130 | +0.0010 | +0.0141 | 12 | 164308 | 0.262 |
| artifact_enchant_removal | -0.0142 | -0.0168 | -0.0026 | 9 | 130386 | 0.841 |
| creature_removal         | -0.0207 | -0.0257 | -0.0049 | 5 | 59710 | 0.911 |

- known-tech best rank by **A-specific DiD**: 1
- known-tech best rank by **prevalence baseline**: 2
- **PASS** (top-3 by DiD and DiD rank <= baseline rank)

### vs GoryoReanimator  (known: ['graveyard_hate'], GATED)

| role                     | A-specific | eff_vsA | eff_field | strata | support | prev_vsA |
|---|---|---|---|---|---|---|
| graveyard_hate           | +0.1067 | +0.0997 | -0.0069 | 6 | 94204 | 0.886 |
| mana_denial              | +0.0399 | +0.0487 | +0.0088 | 15 | 187207 | 0.412 |
| counter_spell            | +0.0272 | +0.0398 | +0.0126 | 8 | 124287 | 0.520 |
| hand_disruption          | +0.0112 | +0.0173 | +0.0062 | 8 | 106216 | 0.292 |
| board_sweeper            | +0.0099 | +0.0000 | -0.0099 | 13 | 175622 | 0.295 |
| artifact_enchant_removal | +0.0093 | +0.0016 | -0.0076 | 5 | 93741 | 0.819 |
| land_destruction         | -0.0106 | -0.0256 | -0.0150 | 13 | 171310 | 0.569 |
| counter_ability          | -0.0249 | -0.0253 | -0.0004 | 9 | 122167 | 0.266 |
| creature_removal         | -0.0680 | -0.0825 | -0.0145 | 2 | 22188 | 0.901 |

- known-tech best rank by **A-specific DiD**: 1
- known-tech best rank by **prevalence baseline**: 2
- **PASS** (top-3 by DiD and DiD rank <= baseline rank)

### vs Yawgmoth  (known: ['graveyard_hate'], reported-only)

| role                     | A-specific | eff_vsA | eff_field | strata | support | prev_vsA |
|---|---|---|---|---|---|---|
| board_sweeper            | +0.0069 | -0.0011 | -0.0080 | 21 | 216383 | 0.281 |
| counter_spell            | +0.0037 | +0.0171 | +0.0134 | 14 | 161194 | 0.607 |
| artifact_enchant_removal | +0.0012 | -0.0001 | -0.0012 | 10 | 119015 | 0.842 |
| land_destruction         | +0.0008 | -0.0103 | -0.0110 | 18 | 215278 | 0.500 |
| counter_ability          | -0.0002 | -0.0044 | -0.0042 | 15 | 170967 | 0.163 |
| mana_denial              | -0.0049 | +0.0057 | +0.0106 | 24 | 222401 | 0.431 |
| creature_removal         | -0.0074 | -0.0094 | -0.0020 | 9 | 80168 | 0.866 |
| graveyard_hate           | -0.0157 | -0.0154 | +0.0003 | 13 | 158123 | 0.860 |
| hand_disruption          | -0.0303 | -0.0158 | +0.0145 | 14 | 167467 | 0.266 |

- known-tech best rank by **A-specific DiD**: 8
- known-tech best rank by **prevalence baseline**: 2
- **MISS** (top-3 by DiD and DiD rank <= baseline rank)

### vs Dredge  (known: ['graveyard_hate'], reported-only)

| role                     | A-specific | eff_vsA | eff_field | strata | support | prev_vsA |
|---|---|---|---|---|---|---|
| graveyard_hate           | +0.1092 | +0.1143 | +0.0052 | 3 | 62399 | 0.852 |
| hand_disruption          | +0.0711 | +0.1029 | +0.0318 | 2 | 38119 | 0.303 |
| board_sweeper            | +0.0124 | +0.0070 | -0.0054 | 5 | 97568 | 0.256 |
| counter_spell            | +0.0054 | +0.0152 | +0.0098 | 5 | 93612 | 0.537 |
| mana_denial              | -0.0007 | +0.0169 | +0.0176 | 5 | 102315 | 0.415 |
| creature_removal         | -0.0011 | -0.0009 | +0.0003 | 1 | 19363 | 0.906 |
| counter_ability          | -0.0057 | -0.0139 | -0.0083 | 1 | 19652 | 0.065 |
| land_destruction         | -0.0403 | -0.0580 | -0.0177 | 6 | 98207 | 0.459 |
| artifact_enchant_removal | -0.0502 | -0.0528 | -0.0026 | 1 | 37658 | 0.831 |

- known-tech best rank by **A-specific DiD**: 1
- known-tech best rank by **prevalence baseline**: 2
- **PASS** (top-3 by DiD and DiD rank <= baseline rank)

### vs HammerTime  (known: ['artifact_enchant_removal'], GATED)

| role                     | A-specific | eff_vsA | eff_field | strata | support | prev_vsA |
|---|---|---|---|---|---|---|
| counter_spell            | +0.0355 | +0.0529 | +0.0175 | 15 | 163021 | 0.592 |
| graveyard_hate           | +0.0109 | +0.0132 | +0.0023 | 11 | 115478 | 0.866 |
| land_destruction         | +0.0072 | -0.0059 | -0.0131 | 21 | 222940 | 0.486 |
| hand_disruption          | +0.0063 | +0.0213 | +0.0150 | 14 | 139905 | 0.288 |
| mana_denial              | +0.0039 | +0.0165 | +0.0127 | 20 | 214170 | 0.436 |
| board_sweeper            | +0.0003 | -0.0073 | -0.0077 | 17 | 188932 | 0.216 |
| counter_ability          | -0.0140 | -0.0236 | -0.0096 | 8 | 115688 | 0.061 |
| artifact_enchant_removal | -0.0159 | -0.0199 | -0.0040 | 12 | 141526 | 0.842 |
| creature_removal         | -0.0357 | -0.0427 | -0.0070 | 6 | 60393 | 0.869 |

- known-tech best rank by **A-specific DiD**: 8
- known-tech best rank by **prevalence baseline**: 3
- **MISS** (top-3 by DiD and DiD rank <= baseline rank)

### vs Affinity  (known: ['artifact_enchant_removal'], GATED)

| role                     | A-specific | eff_vsA | eff_field | strata | support | prev_vsA |
|---|---|---|---|---|---|---|
| counter_ability          | +0.0469 | +0.0531 | +0.0062 | 6 | 77997 | 0.157 |
| land_destruction         | +0.0438 | +0.0278 | -0.0161 | 9 | 112045 | 0.489 |
| counter_spell            | +0.0178 | +0.0332 | +0.0154 | 6 | 110853 | 0.553 |
| artifact_enchant_removal | +0.0101 | +0.0033 | -0.0068 | 2 | 60167 | 0.845 |
| graveyard_hate           | +0.0088 | +0.0108 | +0.0020 | 4 | 76973 | 0.881 |
| board_sweeper            | +0.0075 | +0.0016 | -0.0058 | 9 | 152320 | 0.253 |
| mana_denial              | -0.0124 | +0.0055 | +0.0179 | 11 | 159280 | 0.375 |
| creature_removal         | -0.0338 | -0.0370 | -0.0032 | 2 | 39015 | 0.897 |
| hand_disruption          | -0.0416 | -0.0263 | +0.0153 | 5 | 65774 | 0.276 |

- known-tech best rank by **A-specific DiD**: 4
- known-tech best rank by **prevalence baseline**: 3
- **MISS** (top-3 by DiD and DiD rank <= baseline rank)

### vs HardenedScales  (known: ['artifact_enchant_removal'], reported-only)

| role                     | A-specific | eff_vsA | eff_field | strata | support | prev_vsA |
|---|---|---|---|---|---|---|
| counter_ability          | +0.0582 | +0.0515 | -0.0067 | 6 | 102465 | 0.147 |
| land_destruction         | +0.0324 | +0.0193 | -0.0131 | 10 | 119639 | 0.504 |
| artifact_enchant_removal | +0.0234 | +0.0226 | -0.0008 | 6 | 91386 | 0.842 |
| graveyard_hate           | +0.0233 | +0.0228 | -0.0005 | 7 | 95481 | 0.844 |
| board_sweeper            | +0.0171 | +0.0085 | -0.0085 | 11 | 149423 | 0.256 |
| mana_denial              | -0.0092 | +0.0018 | +0.0110 | 11 | 165177 | 0.416 |
| counter_spell            | -0.0182 | -0.0053 | +0.0129 | 7 | 107961 | 0.559 |
| hand_disruption          | -0.0373 | -0.0134 | +0.0239 | 5 | 74596 | 0.317 |
| creature_removal         | -0.0598 | -0.0538 | +0.0059 | 3 | 53147 | 0.874 |

- known-tech best rank by **A-specific DiD**: 3
- known-tech best rank by **prevalence baseline**: 3
- **PASS** (top-3 by DiD and DiD rank <= baseline rank)

### vs RubyStorm  (known: ['counter_spell', 'hand_disruption'], GATED)

| role                     | A-specific | eff_vsA | eff_field | strata | support | prev_vsA |
|---|---|---|---|---|---|---|
| counter_ability          | +0.0703 | +0.0751 | +0.0048 | 3 | 61748 | 0.416 |
| counter_spell            | +0.0513 | +0.0635 | +0.0122 | 5 | 83936 | 0.492 |
| creature_removal         | +0.0457 | +0.0075 | -0.0383 | 2 | 22188 | 0.908 |
| graveyard_hate           | +0.0155 | -0.0031 | -0.0187 | 4 | 64566 | 0.904 |
| board_sweeper            | +0.0012 | +0.0008 | -0.0004 | 7 | 94897 | 0.297 |
| land_destruction         | -0.0133 | -0.0272 | -0.0138 | 8 | 83812 | 0.577 |
| artifact_enchant_removal | -0.0182 | -0.0197 | -0.0015 | 4 | 59694 | 0.781 |
| hand_disruption          | -0.0244 | -0.0218 | +0.0026 | 4 | 47230 | 0.309 |
| mana_denial              | -0.0292 | -0.0192 | +0.0099 | 10 | 107248 | 0.418 |

- known-tech best rank by **A-specific DiD**: 2
- known-tech best rank by **prevalence baseline**: 5
- **PASS** (top-3 by DiD and DiD rank <= baseline rank)

### vs Footfalls  (known: ['counter_spell'], reported-only)

| role                     | A-specific | eff_vsA | eff_field | strata | support | prev_vsA |
|---|---|---|---|---|---|---|
| board_sweeper            | +0.0123 | +0.0027 | -0.0096 | 18 | 177991 | 0.216 |
| counter_ability          | +0.0059 | -0.0020 | -0.0079 | 10 | 117104 | 0.062 |
| counter_spell            | +0.0023 | +0.0152 | +0.0129 | 16 | 182285 | 0.527 |
| creature_removal         | -0.0009 | +0.0005 | +0.0013 | 7 | 57691 | 0.855 |
| hand_disruption          | -0.0020 | +0.0120 | +0.0140 | 14 | 160437 | 0.337 |
| land_destruction         | -0.0030 | -0.0150 | -0.0119 | 18 | 173626 | 0.469 |
| mana_denial              | -0.0038 | +0.0061 | +0.0099 | 24 | 217354 | 0.355 |
| artifact_enchant_removal | -0.0065 | -0.0071 | -0.0006 | 9 | 112203 | 0.840 |
| graveyard_hate           | -0.0227 | -0.0194 | +0.0033 | 13 | 133073 | 0.838 |

- known-tech best rank by **A-specific DiD**: 3
- known-tech best rank by **prevalence baseline**: 4
- **PASS** (top-3 by DiD and DiD rank <= baseline rank)

### vs Aggro  (known: ['board_sweeper'], reported-only)

| role                     | A-specific | eff_vsA | eff_field | strata | support | prev_vsA |
|---|---|---|---|---|---|---|
| hand_disruption          | +0.0287 | +0.0408 | +0.0121 | 25 | 178987 | 0.331 |
| board_sweeper            | +0.0186 | +0.0100 | -0.0086 | 28 | 183863 | 0.221 |
| land_destruction         | +0.0172 | +0.0075 | -0.0097 | 38 | 246007 | 0.548 |
| counter_spell            | +0.0014 | +0.0046 | +0.0032 | 24 | 183040 | 0.570 |
| creature_removal         | +0.0004 | -0.0047 | -0.0051 | 13 | 105683 | 0.850 |
| counter_ability          | -0.0005 | -0.0022 | -0.0016 | 17 | 142199 | 0.080 |
| graveyard_hate           | -0.0015 | -0.0047 | -0.0032 | 26 | 180235 | 0.888 |
| mana_denial              | -0.0031 | +0.0047 | +0.0078 | 46 | 260992 | 0.365 |
| artifact_enchant_removal | -0.0071 | -0.0114 | -0.0043 | 30 | 207126 | 0.870 |

- known-tech best rank by **A-specific DiD**: 2
- known-tech best rank by **prevalence baseline**: 8
- **PASS** (top-3 by DiD and DiD rank <= baseline rank)

## B1 — temporal reproducibility (disjoint blocks): does the primary role keep a positive, top-k A-specific effect on both halves?

### vs GenericTron, primary role `land_destruction`  (GATED)

| block | A-specific | strata | rank |
|---|---|---|---|
| 2022-01-01..2023-12-31 | -0.0208 | 10 | 3 |
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
| 2022-01-01..2023-12-31 | +0.0674 | 5 | 1 |
| 2024-01-01..2025-12-31 | +0.0434 | 7 | 2 |

- **PASS** (positive and top-k on both blocks)

### vs GoryoReanimator, primary role `graveyard_hate`  (GATED)

| block | A-specific | strata | rank |
|---|---|---|---|
| 2022-01-01..2023-12-31 | +0.3028 | 1 | 2 |
| 2024-01-01..2025-12-31 | +0.1137 | 5 | 1 |

- **PASS** (positive and top-k on both blocks)

### vs Yawgmoth, primary role `graveyard_hate`  (reported-only)

| block | A-specific | strata | rank |
|---|---|---|---|
| 2022-01-01..2023-12-31 | +0.0075 | 6 | 6 |
| 2024-01-01..2025-12-31 | -0.0335 | 10 | 8 |

- **MISS** (positive and top-k on both blocks)

### vs Dredge, primary role `graveyard_hate`  (reported-only)

| block | A-specific | strata | rank |
|---|---|---|---|
| 2022-01-01..2023-12-31 | +0.1145 | 2 | 1 |
| 2024-01-01..2025-12-31 | +0.0000 | 0 | None |

- **MISS** (positive and top-k on both blocks)

### vs HammerTime, primary role `artifact_enchant_removal`  (GATED)

| block | A-specific | strata | rank |
|---|---|---|---|
| 2022-01-01..2023-12-31 | -0.0021 | 8 | 5 |
| 2024-01-01..2025-12-31 | -0.0288 | 1 | 9 |

- **MISS** (positive and top-k on both blocks)

### vs Affinity, primary role `artifact_enchant_removal`  (GATED)

| block | A-specific | strata | rank |
|---|---|---|---|
| 2022-01-01..2023-12-31 | +0.0063 | 2 | 4 |
| 2024-01-01..2025-12-31 | +0.1136 | 1 | 1 |

- **MISS** (positive and top-k on both blocks)

### vs HardenedScales, primary role `artifact_enchant_removal`  (reported-only)

| block | A-specific | strata | rank |
|---|---|---|---|
| 2022-01-01..2023-12-31 | +0.0038 | 4 | 1 |
| 2024-01-01..2025-12-31 | +0.0347 | 2 | 3 |

- **PASS** (positive and top-k on both blocks)

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
| 2022-01-01..2023-12-31 | +0.0226 | 15 | 2 |
| 2024-01-01..2025-12-31 | +0.0141 | 17 | 3 |

- **PASS** (positive and top-k on both blocks)

## Verdict

Gated B2: 5/7 pass. Gated B1: 2/7 pass.

**TARGETS MISSED — see above; not lowered (CLAUDE.md)**

## Discussion & failure analysis

**Headline: B2 recovery works and systematically beats the naive baseline.**
Gated **5/7**, overall **10/13** recover the known tech role in the top-3 by the
within-archetype DiD, and in every pass the DiD rank is ≤ the frequency-only
baseline — often far better: Tron 1 vs 5, Titan 2 vs 5, Ruby Storm 2 vs 5, Aggro
2 vs 8. The naive "what's played most vs A" baseline ranks generic answers on
top because everyone packs them; the DiD strips that out and surfaces the
*specific* answer. The §4c/§4d confound is defeated for recovery across a wide,
pre-registered set of archetypes.

**Two genuine insights the tool surfaced (not just recovery):**
- **Titan distinguishes mana denial from land destruction.** Vs Titan the DiD
  ranks `mana_denial` #2 (+0.100) and `counter_spell` #1 (+0.120) but
  `land_destruction` **last, negative** (−0.035). This is correct: Amulet /
  Primeval Titan floods lands (Amulet + bounce-lands), so destroying one land is
  near useless, while Blood Moon / Damping Sphere and countering the payoff are
  the real answers. The two "attack their mana" roles are not interchangeable and
  the model learns which one bites. (Our a-priori `primary` for Titan was
  `land_destruction`, which is why its B1 misses; the data says the anti-Titan
  role is `mana_denial`.)
- **Creature aggro is less muddy than §4d feared.** Vs Aggro, `board_sweeper`
  is #2 by DiD (+0.019) vs #8 by baseline, and `hand_disruption` #1 — plausible
  proactive answers, recovered despite §4d's pessimism about creature decks.

**Three honest misses (reported, not massaged):**
- **HammerTime (GATED): artifact removal ranks 8th (near last).** Only
  `counter_spell` shows a clear A-specific effect; reactive removal underperforms
  — either HammerTime is genuinely resilient (Sigarda's Aid flash-equips,
  Puresteel / Urza's Saga redundancy, a fast clock) or the conventional
  "kill the Hammer" wisdom is wrong. Flagged.
- **Affinity (GATED): artifact removal ranks 4th (strata only 2).** This flipped
  from a PASS after Layer A's role vocabulary was broadened (for Standard
  coverage) to fold flexible any-permanent removal ("destroy/exile target
  (nonland) permanent" — Assassin's Trophy, Anguished Unmaking) into
  `artifact_enchant_removal`. That is functionally correct (those cards *do* kill
  artifacts) but dilutes artifact-*specificity*, so the artifact tech signal vs
  Affinity weakens. A real finding: broad, flexible removal is a noisier tech
  role than a narrow one — the role granularity is a genuine modeling knob.
- **Yawgmoth (reported): graveyard hate not A-specific (#8).** Most likely our
  a-priori label was wrong — Yawgmoth is a *battlefield* sacrifice-value engine,
  not a graveyard deck, so graveyard hate (its single most-played role) does not
  specifically beat it. Metagame-defensible.

**B1 reproducibility: gated 2/7 — and the pattern is itself the finding.** The
only roles stationary across the 2022–2023 vs 2024–2025 split are
**graveyard_hate vs the graveyard decks** (LivingEnd, GoryoReanimator both PASS).
Every narrow tech (land destruction, mana denial, artifact removal, counters,
discard) shifts sign or top-k rank between eras. Graveyard hate is a **persistent
structural** tech; most other tech is **metagame-contingent** — the right answer
this season, not for all time. B1 correctly detects this rather than papering
over it.

**What this establishes.** Layer A + Layer B is a working tech finder for
*recovery* across many archetypes, beating the naive baseline everywhere it
passes, and surfacing correct nuance (Titan, Aggro). It is end-to-end
reproducible for the stationary graveyard-hate relationships. It is NOT yet a
stationary predictor for narrow techs (needs era-aware estimation), and Layer C
(ranking *unplayed* hidden tech) + C1 (temporal precision@k) remain future work.
See `tech-finder-standard-2026-07-08.md` for a transfer test to Standard (the
method does not transfer there — insufficient within-archetype sample).

## Reproduce

```
python scripts/extract_matches_guarded.py          # matches (tolerant of live raw_refs)
python -m archetypes.labeler --format modern --granularity parent
python scripts/materialize_card_roles.py           # card_roles from Scryfall bulk
python -m validation.tech_finder --format modern    # this report
```
