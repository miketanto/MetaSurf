# M1 V1 archetype-classifier validation — 2026-07-08 (Standard, era `standard-20230701-20240802`)

Per-era Standard V1 (rotating format): this validates the 2023-07-01..2024-08-02
era. The later era (`standard-v1-archetypes-era2-2026-07-08.md`) PASSES all
criteria (V1.1 0.9876 no misses; V1.2 both Duskmourn emergence events detected).
This era passes agreement but flags one archetype below F1 — see the verdict.

All numbers are printed output of `python -m validation.v1_archetypes` against the rebuilt database. Methodology: docstring of `validation/v1_archetypes/run.py`.

Classifier version: `rules-70eacd2efe74`
Rule-name resolution: fold-resolved=[] unresolved=[]

## V1.1 — standard hold-out 2024-05-01 .. 2024-05-31 (era-matched rules `standard-20230701-20240802`)

Decks: 5515 | specific-rules labeled: 5224 (conflicts: 70, fallback-labeled: 169) | clusters: 284 | noise decks: 101

**Agreement on established archetypes (>= 50 decks): 0.9878** (target >= 0.95) | **ARI: 0.0841**

ARI is computed against raw cluster ids BEFORE majority-label mapping; HDBSCAN deliberately splits archetypes into many fine-grained clusters (builds/variants), so ARI is structurally low while mapped agreement is high. The plan sets a target on agreement, not ARI; ARI is reported for reference.

Clustering-stage hyperparameters (frozen BEFORE this holdout run on the disjoint tuning month 2023-03; grid + scores in the `archetypes/classifier/clustering.py` docstring): min_cluster_size=5, min_samples=1, selection=eom, noise-attachment tau=0.3 (noise decks join the nearest cluster centroid at cosine >= tau; below tau stays Rogue). Tuning-month score: agreement 0.9925, worst established F1 0.933. The holdout month was not used for any tuning.

| archetype | decks | precision | recall | F1 |
|---|---|---|---|---|
| 5c Midrange | 88 | 0.9438 | 0.9545 | 0.9492 |
| Aggro | 457 | 1.0000 | 0.9912 | 0.9956 |
| Analyst | 613 | 0.9984 | 1.0000 | 0.9992 |
| Boros Convoke | 571 | 0.9930 | 0.9947 | 0.9939 |
| Control | 932 | 0.9968 | 0.9946 | 0.9957 |
| Domain | 368 | 0.9918 | 0.9864 | 0.9891 |
| Esper Midrange | 615 | 0.9919 | 0.9967 | 0.9943 |
| Legends | 365 | 0.9973 | 1.0000 | 0.9986 |
| Midrange | 696 | 0.9826 | 0.9741 | 0.9784 |
| Poison | 318 | 1.0000 | 0.9717 | 0.9856 |
| Reanimator | 64 | 0.9630 | 0.8125 | 0.8814 |

## V1.2 — emergence backtest (horizon 7 days)

| event | archetype | key card | first >=5 | deadline | detected | cluster size | purity | passed |
|---|---|---|---|---|---|---|---|---|

Note: the acceptance criterion's "before/at the time community sites named it" clause is not verifiable offline (no archived naming dates in this environment); the measurable criterion applied is detection within 7 days of the first 5 appearances.

## V1.3 — determinism

Full V1.1+V1.2 computation executed twice in-process; serialized metrics **byte-identical** — PASS.

## Verdict

**TARGETS MISSED — stopped for owner review (CLAUDE.md):**

- V1.1 archetypes below F1 0.9: Reanimator=0.881

### Failure analysis (Reanimator, F1 0.881)

- **What passed:** V1.1 overall agreement **0.9878 ≥ 0.95** target; V1.3
  determinism PASS; 10 of 11 established archetypes ≥ 0.94 F1 (most ≥ 0.985).
  The Standard rule set and the era-matched labeling are sound; this is a
  single sub-target on one archetype, not a systemic miss.
- **Where it misses:** Reanimator precision 0.963 (few false positives) but
  **recall 0.812** — ~19% of rule-labeled Reanimator decks are absorbed into a
  neighbouring cluster by the HDBSCAN stage, so the majority-label mapping
  doesn't recover them. This is a *clustering-recovery* limitation, not a rules
  error (the rule labels themselves are the ground truth).
- **Why:** Reanimator is the smallest established archetype here (n=64, barely
  over the 50-deck threshold) and shares heavy card overlap (ramp / removal /
  payoffs) with the much larger Midrange/Domain clusters, so density clustering
  merges some of its decks. Small, card-overlapping archetypes are the known
  weak spot of the clustering stage (Modern's tuning-month worst F1 was 0.933
  for the same reason).
- **Not adjusted:** per CLAUDE.md the target is not lowered and the window is
  not cherry-picked (2024-05 was chosen a priori as the highest-volume month in
  the era, before seeing per-archetype results). Options for the owner:
  (1) accept — the product labels Reanimator correctly by *rules*; the miss is
  only in the clustering *recovery* metric (affects emerging-cluster detection,
  not served labels); (2) treat 64-deck archetypes as below the "major
  archetype" bar the target intends; (3) re-tune the noise-attachment tau for
  Standard on a disjoint month (needs re-freezing hyperparameters — a separate
  task). Flagged for decision; nothing ships as a validated Standard V1 pass
  until resolved.
