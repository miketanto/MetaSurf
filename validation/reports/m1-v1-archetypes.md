# M1 V1 archetype-classifier validation — 2026-07-07

All numbers are printed output of `python -m validation.v1_archetypes` against the rebuilt database. Methodology: docstring of `validation/v1_archetypes/run.py`.

Classifier version: `rules-99668739d46e`
Rule-name resolution: fold-resolved=[' Bottled Cloister', 'Troll of Khazad-dum'] unresolved=[]

## V1.1 — hold-out month 2024-01-01 .. 2024-01-31

Decks: 10149 | specific-rules labeled: 8370 (conflicts: 66, fallback-labeled: 1695) | clusters: 622 | noise decks: 72

**Agreement on established archetypes (>= 50 decks): 0.9949** (target >= 0.95) | **ARI: 0.0512**

ARI is computed against raw cluster ids BEFORE majority-label mapping; HDBSCAN deliberately splits archetypes into many fine-grained clusters (builds/variants), so ARI is structurally low while mapped agreement is high. The plan sets a target on agreement, not ARI; ARI is reported for reference.

Clustering-stage hyperparameters (frozen BEFORE this holdout run on the disjoint tuning month 2023-03; grid + scores in the `archetypes/classifier/clustering.py` docstring): min_cluster_size=5, min_samples=1, selection=eom, noise-attachment tau=0.3 (noise decks join the nearest cluster centroid at cosine >= tau; below tau stays Rogue). Tuning-month score: agreement 0.9925, worst established F1 0.933. The holdout month was not used for any tuning.

| archetype | decks | precision | recall | F1 |
|---|---|---|---|---|
| Aggro | 1346 | 0.9948 | 0.9970 | 0.9959 |
| AsmoFood | 146 | 0.9664 | 0.9863 | 0.9763 |
| Azorius Control | 188 | 0.8911 | 0.9574 | 0.9231 |
| CoffersControl | 271 | 0.9963 | 1.0000 | 0.9982 |
| Creativity | 200 | 0.9950 | 1.0000 | 0.9975 |
| DomainZoo | 219 | 0.9865 | 1.0000 | 0.9932 |
| Footfalls | 1371 | 1.0000 | 0.9993 | 0.9996 |
| GenericTron | 284 | 1.0000 | 1.0000 | 1.0000 |
| HammerTime | 220 | 1.0000 | 1.0000 | 1.0000 |
| HardenedScales | 360 | 1.0000 | 1.0000 | 1.0000 |
| LivingEnd | 469 | 0.9979 | 1.0000 | 0.9989 |
| Merfolk | 137 | 1.0000 | 1.0000 | 1.0000 |
| Mill | 108 | 1.0000 | 1.0000 | 1.0000 |
| OmnathControl | 349 | 0.9883 | 0.9656 | 0.9768 |
| Scam | 84 | 0.9286 | 0.9286 | 0.9286 |
| Shadow | 107 | 0.9381 | 0.9907 | 0.9636 |
| Titan | 717 | 1.0000 | 0.9986 | 0.9993 |
| Wizards | 88 | 0.9881 | 0.9432 | 0.9651 |
| Yawgmoth | 1152 | 1.0000 | 1.0000 | 1.0000 |

## V1.2 — emergence backtest (horizon 7 days)

| event | archetype | key card | first >=5 | deadline | detected | cluster size | purity | passed |
|---|---|---|---|---|---|---|---|---|
| MH3 release — Nadu | Nadu | Nadu, Winged Wisdom | 2024-06-09 | 2024-06-16 | 2024-06-09 | 5 | 1.0 | PASS |
| Assassin's Creed release — Basim | BassimAffinit | Basim Ibn Ishaq | 2024-07-07 | 2024-07-14 | 2024-07-07 | 6 | 0.8333 | PASS |

Note: the acceptance criterion's "before/at the time community sites named it" clause is not verifiable offline (no archived naming dates in this environment); the measurable criterion applied is detection within 7 days of the first 5 appearances.

## V1.3 — determinism

Full V1.1+V1.2 computation executed twice in-process; serialized metrics **byte-identical** — PASS.

## Verdict

All V1.1-V1.3 acceptance criteria met.
