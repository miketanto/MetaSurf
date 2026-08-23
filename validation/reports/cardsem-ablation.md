# Semantic-channel ablation (V1.1 sweep + V1.2) — 2026-08-23

Ablation of the CardGuru feature channel in the clustering-stage vectorizer (design: `docs/notes/card-semantics-integration.md`). Every number is printed output of `python -m validation.v1_archetypes.sweep`.

## V1.1 — beta sweep on the TUNING month

Tuning month 2023-03-01 .. 2023-03-31, disjoint from the M1 holdout (2024-01), which is deliberately NOT touched: beta is chosen here or not at all.

Established archetypes = rule labels with >= 50 decks. Agreement target >= 0.95; per-archetype F1 target >= 0.9.

| beta | agreement | ARI | clusters | noise | weakest archetype | weakest F1 | Azorius Control F1 |
|---:|---:|---:|---:|---:|---|---:|---:|
| 0.0 | 0.9925 | 0.0543 | 510 | 85 | OmnathControl | 0.9328 | 0.9661 |
| 0.15 | 0.9925 | 0.0542 | 511 | 82 | OmnathControl | 0.9328 | 0.9641 |
| 0.25 | 0.9925 | 0.0543 | 511 | 67 | OmnathControl | 0.9225 | 0.9641 |
| 0.35 | 0.9925 | 0.0542 | 512 | 53 | OmnathControl | 0.9225 | 0.9641 |
| 0.5 | 0.9926 | 0.0544 | 511 | 17 | OmnathControl | 0.9225 | 0.9574 |
| 0.75 | 0.9922 | 0.0541 | 511 | 1 | OmnathControl | 0.9149 | 0.9554 |
| 1.0 | 0.9922 | 0.0534 | 513 | 1 | OmnathControl | 0.9253 | 0.9554 |

## V1.2 — emergence backtest across beta

| beta | event | first >=5 | detected | lag (days) | cluster size | purity | result |
|---:|---|---|---|---:|---:|---:|---|
| 0.0 | MH3 release — Nadu | 2024-06-09 | 2024-06-09 | 0 | 5 | 1.000 | PASS |
| 0.0 | Assassin's Creed release — Basim | 2024-07-07 | 2024-07-07 | 0 | 6 | 0.833 | PASS |
| 0.25 | MH3 release — Nadu | 2024-06-09 | 2024-06-09 | 0 | 5 | 1.000 | PASS |
| 0.25 | Assassin's Creed release — Basim | 2024-07-07 | 2024-07-07 | 0 | 6 | 0.833 | PASS |
| 0.5 | MH3 release — Nadu | 2024-06-09 | 2024-06-09 | 0 | 6 | 0.833 | PASS |
| 0.5 | Assassin's Creed release — Basim | 2024-07-07 | 2024-07-07 | 0 | 7 | 0.714 | PASS |
| 1.0 | MH3 release — Nadu | 2024-06-09 | 2024-06-13 | 4 | 6 | 0.833 | PASS |
| 1.0 | Assassin's Creed release — Basim | 2024-07-07 | 2024-07-07 | 0 | 6 | 0.833 | PASS |

## Verdict

- Baseline (beta=0) agreement **0.9925**; best swept beta 0.5 at **0.9926** (delta +0.0002).
- Weakest established F1: baseline **0.9328** (OmnathControl); at best beta **0.9225** (OmnathControl).
- Pre-committed prediction (Azorius Control improves): baseline **0.9661** -> **0.9574** at best beta — **FALSIFIED**.
- V1.2 cluster purity: baseline min **0.833**, worst across beta>0 **0.714**. Detection lag: baseline max **0** days, worst across beta>0 **4** days.

