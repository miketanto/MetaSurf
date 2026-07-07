# Deck-recommender validation (V-REC, hardens M3.5b) — 2026-07-07

Printed output of `python -m validation.v_recommender`. Pre-registered protocol + acceptance in the `validation/v_recommender/run.py` docstring; nothing here was tuned against the result.

Blocked weekly walk-forward, 2022-01-01 .. 2025-03-29 (all quarters, not the single M3.5b window). Each Saturday one deck is picked from the trailing-1% universe using past data only, then scored by its REALIZED match winrate that weekend (>= 15 matches to count; no leakage, no circularity). Field mean is 0.500 by construction.

## Pooled result

| strategy | mean realized winrate | match-weighted |
|---|---|---|
| **MODEL** (best response to field) | **0.5642 (95% CI 0.5496-0.5787, 94 wks, t=+8.77)** | 0.5513 |
| STRONGEST (bring a strong deck) | 0.5632 (95% CI 0.5490-0.5775, 96 wks, t=+8.81) | 0.5524 |
| POPULAR (most played) | 0.5106 (95% CI 0.4998-0.5214, 128 wks, t=+1.95) | 0.5074 |

## Acceptance verdicts (pre-registered)

- **V-REC.1** edge is real (MODEL 95% CI lower bound > 0.500): **PASS** (CI lo 0.5496)
- **V-REC.2** MODEL >= POPULAR pooled: **PASS**
- **V-REC.3** MODEL > 0.500 in >= 75% of quarters (>=4 scored weeks): **PASS** (100% of 12 quarters)

## Positioning bonus and robustness

- MODEL vs STRONGEST (the field-positioning bonus over pure deck strength): mean per-week winrate diff -0.0004 over 92 shared weeks (p=0.936). Most of the edge is deck strength; positioning adds a little.
- MODEL vs POPULAR: mean diff +0.0557, MODEL better in 71/92 weeks (p=2.06e-08).
- **Winrate-model tuning-overlap check:** MODEL realized winrate is 0.5501 in quarters overlapping the winrate model's tuning window (2022-07..2023-12) vs 0.5771 outside it — the recommender adds no parameters, so similar values indicate the edge is not a tuning artifact.

## Per-quarter detail (mean realized winrate; n scored weeks)

| quarter | tuning-overlap | MODEL | STRONGEST | POPULAR |
|---|---|---|---|---|
| 2022Q1 |  | 0.517 (n=3) | 0.551 (n=3) | 0.503 (n=4) |
| 2022Q2 |  | 0.586 (n=7) | 0.586 (n=7) | 0.472 (n=8) |
| 2022Q3 | yes | 0.603 (n=8) | 0.574 (n=9) | 0.468 (n=10) |
| 2022Q4 | yes | 0.556 (n=9) | 0.551 (n=9) | 0.495 (n=9) |
| 2023Q1 | yes | 0.553 (n=8) | 0.562 (n=9) | 0.501 (n=11) |
| 2023Q2 | yes | 0.538 (n=5) | 0.539 (n=5) | 0.513 (n=9) |
| 2023Q3 | yes | 0.505 (n=7) | 0.535 (n=6) | 0.515 (n=12) |
| 2023Q4 | yes | 0.536 (n=8) | 0.543 (n=8) | 0.498 (n=11) |
| 2024Q1 |  | 0.546 (n=8) | 0.525 (n=8) | 0.501 (n=9) |
| 2024Q2 |  | 0.585 (n=9) | 0.564 (n=10) | 0.510 (n=11) |
| 2024Q3 |  | 0.652 (n=8) | 0.652 (n=8) | 0.562 (n=12) |
| 2024Q4 |  | 0.580 (n=6) | 0.586 (n=6) | 0.525 (n=12) |
| 2025Q1 |  | 0.537 (n=8) | 0.537 (n=8) | 0.547 (n=10) |

## Determinism

Full computation executed twice in-process; serialized metrics **byte-identical** — PASS.
