# M3 V3 evolution-model validation — 2026-07-07

All numbers are printed output of `python -m validation.v3_evolution` against the rebuilt database. Methodology: docstrings of `validation/v3_evolution/run.py`, `walkforward.py`, `data.py`.

Model: Holt linear smoothing + lagged-winrate coupling (`models/evolution/`), share alpha=0.6 beta=0.1, card alpha=0.6 beta=0.1 — frozen by grid search on the tuning weeks 2022-07-02 .. 2023-12-30 (disjoint from and strictly before the evaluation weeks; grid + scores in `models/evolution/model.py` and `validation/v3_evolution/tune.py`).

## Verdict: **DESCRIPTIVE TRENDS (forecast target(s) missed — plan §5 V3.1 fallback)**

## V3.1 — meta-share forecast, 2024-01-06 .. 2025-03-29

Weeks: 65; scored universe per week: 16-25 archetypes (trailing 8-weekend pooled share >= 1%, training data only).

| forecaster | mean weekly MAE (share points) | improvement vs persistence |
|---|---|---|
| Holt + coupling (the model) | 0.013182 | +2.48% |
| Holt only | 0.013225 | +2.16% |
| persistence baseline | 0.013517 | — |

**Improvement +2.48% vs target >= 10%** — **FAIL**. Model beats persistence in 34/65 weeks; expanding-window gamma moved -0.7173 -> -1.0695 across the window.

## V3.2 — flocking hypothesis (share residual on lagged winrate)

| window | gamma | stderr | t | n | significant (|t|>=1.96) |
|---|---|---|---|---|---|
| tuning (2022-07..2023-12) | -0.7173 | 0.2443 | -2.94 | 1543 | yes |
| eval first half | -0.8161 | 0.3698 | -2.21 | 658 | yes |
| eval second half | -1.4132 | 0.2754 | -5.13 | 636 | yes |
| pooled (tuning+eval) | -1.0801 | 0.1572 | -6.87 | 2837 | yes |

Same sign in all windows: **True**; significant in all windows: **True**. Plan rule (drop the term unless significant and stable): **KEEP**.

**The sign contradicts the flocking hypothesis.** gamma is negative (-1.0801 pooled): archetypes whose lagged latent winrate is high come in *below* their Holt-projected share, not above it — counter-adaptation / mean reversion rather than "players flock to last weekend's winners". The term survives the plan's keep rule (significant, stable sign) and improves V3.1 slightly, but the behavioral story in plan §5 Layer 3 is rejected as stated.

## V3.3 — tech drift, 20 fastest-moving cards per week

Weeks: 65 (cards reselected weekly from training data: top 20 |change| between trailing-4 and previous-4 weekend means, eligibility >= 0.25 mean mainboard copies/deck).

| forecaster | mean weekly MAE (copies/deck) | improvement |
|---|---|---|
| Holt | 0.112707 | -1.77% |
| persistence | 0.110743 | — |

**Improvement -1.77% vs target >= 10%** — **FAIL**. Model beats persistence in 35/65 weeks.

## Failure analysis (V3.1 and V3.3 targets missed — owner review requested)

Per CLAUDE.md the targets are not lowered and the evaluation window is not adjusted; the numbers above stand. Why persistence is this hard to beat here:

- **Weekly meta shares are strongly autocorrelated.** The scored universe's mean weekly share MAE under persistence is already ~0.0135 share points (~1.4pp) — most archetypes barely move week to week, so the achievable headroom over last-weekend's-value is small, and Holt spends it lagging one week behind every sharp break (set releases, bans: see the 2024-06-22, 2024-08-24 and 2024-09-07 rows in the weekly detail, where the model loses). Holt wins in smooth-trend stretches (34/65 weeks) but gives most of it back at regime shifts.
- **The coupling term is real but tiny**: it adds ~+0.31% MAE improvement on top of Holt, and its negative sign (V3.2) means it corrects winners *downward* — informative, not predictive firepower.
- **V3.3 tuning did not transfer.** On the tuning window Holt beat persistence on the card series (0.081551 vs 0.082756, +1.5%); on the evaluation window it lost (0.112707 vs 0.110743, -1.77%). The fastest-mover selection targets precisely the most volatile series, and the mtgo decklist-policy change mid-corpus (2024-06) plus melee's schedule variance make that population noisier in the evaluation period than in tuning.

Not attempted, deliberately: damped-trend Holt, ban/set-release event dummies, cross-archetype pooling, or any other variant — iterating further against this evaluation window would burn the holdout. If the owner wants another attempt, it needs a fresh protocol (new tuning split, pre-registered variants).

**Product consequence (plan §5 V3.1, §7 M3 DoD):** ship the descriptive-trends positioning — trend arrows, movers, emerging decks from Layer 1, winrates/matchups from Layer 2 — and do not market share *prediction*. The plan names this outcome acceptable in advance; the DoD asks for the honest verdict, which this is.

## Data quality (series feeding this suite)

- panel: 170 Saturdays 2022-01-01 .. 2025-03-29; 124 archetype series, 4961 card series
- labeled weekend decks per week: min 189, median 599; zero-deck weekends: 0

## Determinism

Full V3.1+V3.2+V3.3 computation executed twice in-process; serialized metrics **byte-identical** — PASS.

## Weekly detail (V3.1: model MAE vs persistence MAE)

| saturday | universe | model | persistence | model better |
|---|---|---|---|---|
| 2024-01-06 | 21 | 0.007794 | 0.007690 | no |
| 2024-01-13 | 21 | 0.009522 | 0.008768 | no |
| 2024-01-20 | 20 | 0.010778 | 0.012066 | yes |
| 2024-01-27 | 21 | 0.009838 | 0.009997 | yes |
| 2024-02-03 | 21 | 0.009306 | 0.009502 | yes |
| 2024-02-10 | 20 | 0.011895 | 0.010145 | no |
| 2024-02-17 | 19 | 0.018523 | 0.017569 | no |
| 2024-02-24 | 19 | 0.016317 | 0.015974 | no |
| 2024-03-02 | 19 | 0.008520 | 0.013241 | yes |
| 2024-03-09 | 20 | 0.006716 | 0.007827 | yes |
| 2024-03-16 | 20 | 0.017945 | 0.017435 | no |
| 2024-03-23 | 20 | 0.016552 | 0.013389 | no |
| 2024-03-30 | 20 | 0.011890 | 0.011644 | no |
| 2024-04-06 | 20 | 0.011982 | 0.011914 | no |
| 2024-04-13 | 21 | 0.007905 | 0.007357 | no |
| 2024-04-20 | 21 | 0.010550 | 0.009152 | no |
| 2024-04-27 | 21 | 0.011197 | 0.008536 | no |
| 2024-05-04 | 21 | 0.009973 | 0.009176 | no |
| 2024-05-11 | 20 | 0.009292 | 0.010771 | yes |
| 2024-05-18 | 19 | 0.014973 | 0.016120 | yes |
| 2024-05-25 | 18 | 0.014580 | 0.013763 | no |
| 2024-06-01 | 19 | 0.007993 | 0.008136 | yes |
| 2024-06-08 | 19 | 0.012184 | 0.010881 | no |
| 2024-06-15 | 20 | 0.020885 | 0.019564 | no |
| 2024-06-22 | 24 | 0.017399 | 0.012711 | no |
| 2024-06-29 | 25 | 0.013955 | 0.012894 | no |
| 2024-07-06 | 24 | 0.013189 | 0.013752 | yes |
| 2024-07-13 | 24 | 0.006434 | 0.008542 | yes |
| 2024-07-20 | 21 | 0.013428 | 0.015576 | yes |
| 2024-07-27 | 20 | 0.013003 | 0.015863 | yes |
| 2024-08-03 | 20 | 0.011315 | 0.011667 | yes |
| 2024-08-10 | 20 | 0.013321 | 0.015620 | yes |
| 2024-08-17 | 19 | 0.009819 | 0.013545 | yes |
| 2024-08-24 | 18 | 0.017882 | 0.014498 | no |
| 2024-08-31 | 18 | 0.025907 | 0.028652 | yes |
| 2024-09-07 | 19 | 0.011725 | 0.006127 | no |
| 2024-09-14 | 19 | 0.014406 | 0.014354 | no |
| 2024-09-21 | 19 | 0.012791 | 0.014800 | yes |
| 2024-09-28 | 20 | 0.013692 | 0.015263 | yes |
| 2024-10-05 | 21 | 0.007226 | 0.008086 | yes |
| 2024-10-12 | 22 | 0.014675 | 0.014340 | no |
| 2024-10-19 | 22 | 0.014129 | 0.015719 | yes |
| 2024-10-26 | 22 | 0.008775 | 0.011535 | yes |
| 2024-11-02 | 22 | 0.011930 | 0.012874 | yes |
| 2024-11-09 | 22 | 0.013521 | 0.012716 | no |
| 2024-11-16 | 22 | 0.011649 | 0.013269 | yes |
| 2024-11-23 | 21 | 0.008297 | 0.007909 | no |
| 2024-11-30 | 20 | 0.008086 | 0.009296 | yes |
| 2024-12-07 | 17 | 0.014755 | 0.015919 | yes |
| 2024-12-14 | 16 | 0.018559 | 0.023256 | yes |
| 2024-12-21 | 16 | 0.030603 | 0.034431 | yes |
| 2024-12-28 | 18 | 0.013846 | 0.018355 | yes |
| 2025-01-04 | 19 | 0.009349 | 0.009332 | no |
| 2025-01-11 | 21 | 0.019879 | 0.018080 | no |
| 2025-01-18 | 20 | 0.015059 | 0.014374 | no |
| 2025-01-25 | 21 | 0.012344 | 0.013128 | yes |
| 2025-02-01 | 19 | 0.018016 | 0.020670 | yes |
| 2025-02-08 | 18 | 0.008956 | 0.007768 | no |
| 2025-02-15 | 18 | 0.013026 | 0.012437 | no |
| 2025-02-22 | 19 | 0.013991 | 0.015856 | yes |
| 2025-03-01 | 17 | 0.011447 | 0.011427 | no |
| 2025-03-08 | 17 | 0.009862 | 0.011664 | yes |
| 2025-03-15 | 18 | 0.016954 | 0.016984 | yes |
| 2025-03-22 | 18 | 0.017310 | 0.014984 | no |
| 2025-03-29 | 18 | 0.019237 | 0.019713 | yes |
