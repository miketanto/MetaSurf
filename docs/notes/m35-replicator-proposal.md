# M3.5 investigation — replicator dynamics for share forecasting

**Status: prototype run, negative result. Recommendation: do NOT build M3.5 as
a share forecaster; the descriptive-trends verdict from M3 stands.** The same
machinery is valuable as a *product feature* (best-response recommender), not
as a predictor. All numbers below are printed output of
`python -m validation.v3_evolution.replicator_explore` and the diagnostic
in this session (2026-07-07); reproduce with that module.

## Question

M3's V3.1/V3.3 forecasts failed to beat a persistence ("same as last weekend")
baseline, and V3.2 found the plan's flocking coefficient was *negative*
(winners lose share next week). Before accepting the descriptive-trends
verdict, we asked whether other fields' work on competitive-game dynamics
offers a better model than per-series Holt smoothing.

## What the literature says (external, cited — not independently reproduced)

- **The metagame is a proven non-transitive (rock-paper-scissors) system.**
  Czarnecki et al., *Real World Games Look Like Spinning Tops* (NeurIPS 2020,
  arXiv:2004.09468): real competitive games have a transitive strength axis
  wrapped in a band of cycles that is *widest at mid power levels* — where a
  healthy format lives. Omidshafiei et al., *α-Rank* (Scientific Reports
  2019): rank strategies by running evolutionary (replicator) dynamics over
  the empirical matchup matrix rather than assuming one best deck.
- **Our negative-γ finding has a name: negative frequency-dependent
  selection** (Christie 2023, *Ecology and Evolution*): fitness falls as a
  strategy becomes common because the field adapts to beat it. Replicator-
  mutator RPS systems settle into *limit cycles*, not fixed points
  (arXiv:2312.00791) — which is exactly why a persistence baseline is hard to
  beat: the signal is a rotation, not a trend.
- **TCG-specific**: Hearthstone data-mining work (Info-theory & archetype
  choice, *Information Sciences* 2021; 3-year meta study 2016–2019) tracks the
  same coupled frequency-vs-winrate dynamic and a strong entropy signal at
  patches (our set-release/ban breaks — where Holt bled accuracy).
- **Behavioral framing**: fictitious play / best-response — players respond to
  the recent *field composition*, not raw winrates.

The natural model this points to: **replicator dynamics on our Layer-2
matchup matrix** (which M2 validated), forecasting shares by flowing them
toward strategies that beat the current field.

## Prototype (built this session: `models/evolution/replicator.py`)

Game-neutral one-step update `x'_a = x_a · exp(η·(f_a − 0.5))`, renormalized,
where `f_a = Σ_b W[a,b]·x_b` is a's expected win probability against the
current field and `W` is the as-of Layer-2 matchup matrix (fitted on matches
strictly before each Saturday — no leakage). η is the sole hyperparameter;
**η = 0 is exactly persistence**. Protocol matches V3.1 for comparability.

**Holdout hygiene (imperfect, disclosed):** η tuned ONLY on the tuning window
(2022-07-02 .. 2023-12-30); single run on the V3.1 evaluation window
(2024-01-06 .. 2025-03-29). That eval window is no longer pristine (Holt V3.1
saw it), so this is a directional go/no-go, not an acceptance-gate result.

### Result — the dynamics do not help

| window | best η | replicator MAE | persistence MAE | improvement |
|---|---|---|---|---|
| tuning (η selected here) | **0.0** | 0.010508 | 0.010508 | **+0.00%** |
| eval (single run at frozen η=0) | 0.0 | 0.013517 | 0.013517 | +0.00% |
| eval, Holt V3.1 baseline | — | 0.013225 | 0.013517 | +2.16% |
| eval, best η in hindsight (η≈1, not selectable) | 1.0 | 0.013473 | 0.013517 | +0.32% |

The tuner froze η=0 because on the tuning window **any** amount of replicator
motion made the forecast worse. Even with hindsight the eval-optimal η buys
only +0.32% — below Holt, far below the 10% target.

### Why — the signal is swamped by weekly noise (diagnostic, eval window)

- Mean off-diagonal matchup spread `|W_ab − 0.5|`: **0.059** — our Layer-2
  winrates are well-calibrated and heavily shrunk, so most matchups are near
  even. (This is a *good* property of M2, not a bug.)
- Mean replicator drive `|f_a − 0.5|` on universe decks: **0.026**.
- So at η≈1 the update nudges a 5%-share deck by ≈ 0.05·1·0.026 ≈ **0.13
  share-points**, while the actual mean week-over-week share move is **1.35
  share-points** — a ~10:1 noise-to-signal ratio.

Mechanistically: because our winrates correctly cluster near 50%, the matchup
matrix carries little *directional* weekly signal. The rock-paper-scissors
cycle is real but **slow relative to weekly sampling noise** — the spinning
top is near its transitive apex, where cycles are short. One-step-ahead, that
rotation is invisible under the noise floor.

## Recommendation

1. **Do not build M3.5 as a share forecaster.** Two independent model
   families (Holt trend, replicator dynamics) now fail to beat persistence on
   the same data; the literature predicts this. The M3 verdict —
   **descriptive trends, not prediction** — stands and is now better
   supported.
2. **Reuse the matchup matrix as a product feature, not a predictor.** The
   valuable, defensible output is *best-response positioning*: "what beats the
   current field" (α-Rank-style), which powers S2 (matchup matrix) and S6 (My
   Deck vs the meta) — features we're shipping anyway. This does not require
   beating persistence; it requires the calibrated matchups M2 already
   delivers.
3. **If prediction is revisited later, change the target, not the tuning.**
   The weekly one-step horizon is noise-dominated. Candidates worth a *fresh,
   pre-registered* evaluation on withheld data (not this eval window):
   multi-week-ahead or cumulative-share horizons; regime-segmented models with
   ban/set-release event dummies (the entropy-spike weeks); pooling across
   archetypes. None should be iterated against the 2024-2025 window, which is
   now spent for share forecasting.

## Artifacts

- `models/evolution/replicator.py` — game-neutral replicator step (7 property
  tests incl. RPS cycling, `tests/test_replicator.py`).
- `validation/v3_evolution/replicator_explore.py` — exploratory runner
  (clearly marked NOT a validated result).
- No change to the committed M3 report or verdict.
