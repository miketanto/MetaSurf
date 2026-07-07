# M2 V2 winrate-model validation — 2026-07-07

All numbers are printed output of `python -m validation.v2_winrates` against the rebuilt database. Methodology: docstrings of `validation/v2_winrates/run.py` and `walkforward.py`.

Model: hierarchical Bayesian beta-binomial (`models/winrate/`), half_life_days=182.0, prior_strength=10.0, pair_prior_strength=20.0 — frozen by grid search on the tuning weeks 2022-07-02 .. 2023-12-30 (mean weekly log-loss 0.684814), disjoint from and strictly before the evaluation weeks below (`validation/v2_winrates/tune.py`). The tuned half-life sits far above the plan's 14-21d initial guess on a very flat surface (21d scores 0.688773 on the tuning weeks); see the V2.3 discussion.

## V2.1 — weekly walk-forward 2024-01-06 .. 2025-03-29

Weeks evaluated: 65 of 65 scheduled Saturdays (every week with >= 1 evaluable match counts; smallest test weekend: 11 matches). Test matches scored: 70436 (decisive, both archetypes resolved, non-mirror, canonical lower-archetype-id-first orientation).

**Model beats the raw pooled-winrate baseline (B1) in 54/65 weeks = 0.8308** (target >= 0.8) — **PASS**

**Calibration slope (Cox, pooled): 0.9637** (target within [0.9, 1.1]; intercept -0.0017) — **PASS**

| metric | model | B0 raw side-a | B1 raw pooled | B2 raw pair |
|---|---|---|---|---|
| mean weekly log-loss | 0.682115 | 0.690651 | 0.689404 | 0.691042 |
| weeks model beats | — | 53 | 54 | 52 |

Baseline calibration slope (B1): 0.9781 (intercept -0.0069).

Reliability (pooled model predictions, 10 equal-width bins):

| bin | n | mean predicted | empirical |
|---|---|---|---|
| 0.2-0.3 | 163 | 0.2801 | 0.3313 |
| 0.3-0.4 | 5588 | 0.3673 | 0.3627 |
| 0.4-0.5 | 31900 | 0.4602 | 0.4620 |
| 0.5-0.6 | 27414 | 0.5437 | 0.5444 |
| 0.6-0.7 | 5092 | 0.6335 | 0.6180 |
| 0.7-0.8 | 279 | 0.7210 | 0.7025 |

## V2.2 — interval honesty (90% predictive intervals)

Cells: 1295 (evaluation Saturday x archetype, >= 10 decisive weekend matches).
**Mid-P coverage: 0.8842** (target within [0.85, 0.95]) — **PASS**. Plain ppf-interval coverage (conservative, discrete): 0.9112.

## V2.3 — ablations (same evaluation weeks)

| variant | mean weekly log-loss | weeks beating B1 |
|---|---|---|
| full | 0.682115 | 54/65 |
| no_decay | 0.683884 | 53/65 |
| no_hierarchy | 0.688056 | 38/65 |
| neither | 0.691042 | 39/65 |

Time-decay earns its complexity: **True**. Hierarchical shrinkage earns its complexity: **True**.

## Data quality (labeling + match extraction feeding this suite)

- matches: 217804 — by source: manatraders.com=9077, melee.gg=197424, mtgo.com=6481, mtgo.com_limited_data=3801, topdeck.gg=1021
- matches with unresolved opponent deck (deck_id_b null): 20147
- matches on league events: 0 (must be 0 — league data never feeds winrates)
- archetype labels by method: fallback=67678, rogue=2504, rules=379822
- model loader: matches loaded: 217734 (flipped: 96, dropped both-unlabeled: 70, opponent unknown: 20267, draws: 6874)

## Determinism

Full V2.1+V2.2+V2.3 computation executed twice in-process; serialized metrics **byte-identical** — PASS.

## Weekly log-loss detail (model vs B1)

| saturday | test matches | model | B1 baseline | model better |
|---|---|---|---|---|
| 2024-01-06 | 1141 | 0.688329 | 0.690010 | yes |
| 2024-01-13 | 24 | 0.643081 | 0.687057 | yes |
| 2024-01-20 | 26 | 0.703652 | 0.713381 | yes |
| 2024-01-27 | 5227 | 0.685518 | 0.691635 | yes |
| 2024-02-03 | 1341 | 0.677714 | 0.687271 | yes |
| 2024-02-10 | 8935 | 0.681449 | 0.690466 | yes |
| 2024-02-17 | 26 | 0.679860 | 0.704104 | yes |
| 2024-02-24 | 25 | 0.683787 | 0.692616 | yes |
| 2024-03-02 | 1023 | 0.676491 | 0.687711 | yes |
| 2024-03-09 | 3673 | 0.684353 | 0.692596 | yes |
| 2024-03-16 | 1182 | 0.680803 | 0.690024 | yes |
| 2024-03-23 | 2160 | 0.681813 | 0.690597 | yes |
| 2024-03-30 | 166 | 0.670984 | 0.682593 | yes |
| 2024-04-06 | 257 | 0.674927 | 0.681033 | yes |
| 2024-04-13 | 1064 | 0.676696 | 0.689642 | yes |
| 2024-04-20 | 1757 | 0.681602 | 0.689030 | yes |
| 2024-04-27 | 1666 | 0.683556 | 0.689836 | yes |
| 2024-05-04 | 521 | 0.693763 | 0.692313 | no |
| 2024-05-11 | 1044 | 0.678289 | 0.687877 | yes |
| 2024-05-18 | 30 | 0.692279 | 0.714996 | yes |
| 2024-05-25 | 97 | 0.680749 | 0.694263 | yes |
| 2024-06-01 | 65 | 0.673313 | 0.683252 | yes |
| 2024-06-08 | 320 | 0.690631 | 0.689421 | no |
| 2024-06-15 | 33 | 0.669737 | 0.631533 | no |
| 2024-06-22 | 1204 | 0.706475 | 0.716444 | yes |
| 2024-06-29 | 702 | 0.676188 | 0.687572 | yes |
| 2024-07-06 | 44 | 0.687031 | 0.677836 | no |
| 2024-07-13 | 685 | 0.675666 | 0.678424 | yes |
| 2024-07-20 | 41 | 0.712603 | 0.711031 | no |
| 2024-07-27 | 1143 | 0.674744 | 0.681869 | yes |
| 2024-08-03 | 735 | 0.681383 | 0.680355 | no |
| 2024-08-10 | 131 | 0.679381 | 0.683815 | yes |
| 2024-08-17 | 666 | 0.681031 | 0.680638 | no |
| 2024-08-24 | 693 | 0.677587 | 0.679277 | yes |
| 2024-08-31 | 920 | 0.683303 | 0.687934 | yes |
| 2024-09-07 | 1092 | 0.681297 | 0.687803 | yes |
| 2024-09-14 | 356 | 0.685968 | 0.691657 | yes |
| 2024-09-21 | 34 | 0.645298 | 0.659034 | yes |
| 2024-09-28 | 296 | 0.689608 | 0.695117 | yes |
| 2024-10-05 | 1267 | 0.687331 | 0.688958 | yes |
| 2024-10-12 | 1227 | 0.676481 | 0.680211 | yes |
| 2024-10-19 | 80 | 0.687247 | 0.668542 | no |
| 2024-10-26 | 616 | 0.669422 | 0.682261 | yes |
| 2024-11-02 | 467 | 0.683434 | 0.685839 | yes |
| 2024-11-09 | 41 | 0.682455 | 0.723399 | yes |
| 2024-11-16 | 253 | 0.669414 | 0.684620 | yes |
| 2024-11-23 | 337 | 0.680607 | 0.692761 | yes |
| 2024-11-30 | 672 | 0.683240 | 0.692713 | yes |
| 2024-12-07 | 1280 | 0.680429 | 0.689371 | yes |
| 2024-12-14 | 28 | 0.667631 | 0.692038 | yes |
| 2024-12-21 | 29 | 0.714280 | 0.706236 | no |
| 2024-12-28 | 29 | 0.689597 | 0.692370 | yes |
| 2025-01-04 | 553 | 0.691887 | 0.696023 | yes |
| 2025-01-11 | 11 | 0.646500 | 0.684992 | yes |
| 2025-01-18 | 47 | 0.694214 | 0.704968 | yes |
| 2025-01-25 | 6689 | 0.685894 | 0.689879 | yes |
| 2025-02-01 | 31 | 0.688954 | 0.691728 | yes |
| 2025-02-08 | 6147 | 0.684582 | 0.688994 | yes |
| 2025-02-15 | 356 | 0.692100 | 0.693264 | yes |
| 2025-02-22 | 679 | 0.661371 | 0.679286 | yes |
| 2025-03-01 | 1054 | 0.692100 | 0.687860 | no |
| 2025-03-08 | 7266 | 0.684970 | 0.690056 | yes |
| 2025-03-15 | 538 | 0.697459 | 0.697103 | no |
| 2025-03-22 | 25 | 0.695903 | 0.700713 | yes |
| 2025-03-29 | 169 | 0.679058 | 0.684997 | yes |
