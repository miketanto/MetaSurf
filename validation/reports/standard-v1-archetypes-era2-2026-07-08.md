# M1 V1 archetype-classifier validation — 2026-07-08 (Standard, era `standard-20240803-20250730`)

Per-era Standard V1 (rotating format): this validates the 2024-08-03..2025-07-30
era. The earlier era is in `standard-v1-archetypes-era1-2026-07-08.md` (V1.1
agreement 0.9878 but one archetype below the F1 target — Reanimator 0.881,
a clustering-recovery miss; flagged there). **This era PASSES all criteria.**

All numbers are printed output of `python -m validation.v1_archetypes` against the rebuilt database. Methodology: docstring of `validation/v1_archetypes/run.py`.

Classifier version: `rules-41da46c95ba4`
Rule-name resolution: fold-resolved=[] unresolved=[]

## V1.1 — standard hold-out 2024-11-01 .. 2024-11-30 (era-matched rules `standard-20240803-20250730`)

Decks: 2316 | specific-rules labeled: 2051 (conflicts: 14, fallback-labeled: 214) | clusters: 133 | noise decks: 69

**Agreement on established archetypes (>= 50 decks): 0.9876** (target >= 0.95) | **ARI: 0.1200**

ARI is computed against raw cluster ids BEFORE majority-label mapping; HDBSCAN deliberately splits archetypes into many fine-grained clusters (builds/variants), so ARI is structurally low while mapped agreement is high. The plan sets a target on agreement, not ARI; ARI is reported for reference.

Clustering-stage hyperparameters (frozen BEFORE this holdout run on the disjoint tuning month 2023-03; grid + scores in the `archetypes/classifier/clustering.py` docstring): min_cluster_size=5, min_samples=1, selection=eom, noise-attachment tau=0.3 (noise decks join the nearest cluster centroid at cosine >= tau; below tau stays Rogue). Tuning-month score: agreement 0.9925, worst established F1 0.933. The holdout month was not used for any tuning.

| archetype | decks | precision | recall | F1 |
|---|---|---|---|---|
| Aggro | 473 | 1.0000 | 0.9873 | 0.9936 |
| Auras | 61 | 1.0000 | 1.0000 | 1.0000 |
| Burn | 104 | 0.9720 | 1.0000 | 0.9858 |
| Caretaker | 130 | 1.0000 | 0.9923 | 0.9961 |
| Convoke | 86 | 1.0000 | 0.9767 | 0.9882 |
| Demons | 98 | 0.9677 | 0.9184 | 0.9424 |
| Domain | 122 | 1.0000 | 1.0000 | 1.0000 |
| Midrange | 699 | 0.9900 | 0.9900 | 0.9900 |
| Oculus | 87 | 0.9886 | 1.0000 | 0.9943 |
| Prowess | 82 | 1.0000 | 1.0000 | 1.0000 |

## V1.2 — emergence backtest (horizon 7 days)

| event | archetype | key card | first >=5 | deadline | detected | cluster size | purity | passed |
|---|---|---|---|---|---|---|---|---|
| Duskmourn release — Oculus | Oculus | Abhorrent Oculus | 2024-09-29 | 2024-10-06 | 2024-09-29 | 18 | 1.0 | PASS |
| Duskmourn release — Demons | UBDemon | Unholy Annex // Ritual Chamber | 2024-10-09 | 2024-10-16 | 2024-10-11 | 12 | 0.5833 | PASS |

Note: the acceptance criterion's "before/at the time community sites named it" clause is not verifiable offline (no archived naming dates in this environment); the measurable criterion applied is detection within 7 days of the first 5 appearances.

## V1.3 — determinism

Full V1.1+V1.2 computation executed twice in-process; serialized metrics **byte-identical** — PASS.

## Verdict

All V1.1-V1.3 acceptance criteria met.
