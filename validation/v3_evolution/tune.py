"""Holt smoothing-parameter tuning for the evolution model.

Grid search scored by mean weekly MAE (pure Holt, no coupling — the coupling
term is fit inside the walk-forward itself) over the TUNING weeks — Saturdays
2022-07-02 .. 2023-12-30 — disjoint from and strictly before the V3
evaluation weeks (2024-01-06 .. 2025-03-29). Share and card series are tuned
independently; winners are frozen into models/evolution/model.py and quoted
in the V3 report.

Run: python -m validation.v3_evolution.tune
"""

from __future__ import annotations

import datetime as dt
from itertools import product

import psycopg

from db.connection import database_url
from validation.v3_evolution.data import load_card_copies_panel, load_share_panel
from validation.v3_evolution.walkforward import (
    run_card_walkforward,
    run_share_walkforward,
)

PANEL_FIRST_SATURDAY = dt.date(2022, 1, 1)  # warm-up history before tuning
PANEL_LAST_SATURDAY = dt.date(2025, 3, 29)
TUNING_FIRST_SATURDAY = dt.date(2022, 7, 2)
TUNING_LAST_SATURDAY = dt.date(2023, 12, 30)

ALPHA_GRID = (0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9)
BETA_GRID = (0.0, 0.1, 0.2, 0.3, 0.4, 0.5)


def tuning_indexes(saturdays: list[dt.date]) -> list[int]:
    return [
        i for i, s in enumerate(saturdays)
        if TUNING_FIRST_SATURDAY <= s <= TUNING_LAST_SATURDAY
    ]


def main() -> None:
    with psycopg.connect(database_url()) as conn:
        share_panel, _totals = load_share_panel(
            conn, "modern", PANEL_FIRST_SATURDAY, PANEL_LAST_SATURDAY
        )
        card_panel = load_card_copies_panel(
            conn, "modern", PANEL_FIRST_SATURDAY, PANEL_LAST_SATURDAY
        )
    idx = tuning_indexes(share_panel.saturdays)
    print(f"tuning weeks: {len(idx)} Saturdays"
          f" {TUNING_FIRST_SATURDAY} .. {TUNING_LAST_SATURDAY}")
    print(f"share panel: {share_panel.values.shape}, card panel: {card_panel.values.shape}")

    assert share_panel.counts is not None
    share_rows = []
    for a, b in product(ALPHA_GRID, BETA_GRID):
        res = run_share_walkforward(
            share_panel.values, share_panel.counts, None, idx, a, b
        )
        share_rows.append((res.mean_mae_model(), a, b, res.mean_mae_persistence()))
    share_rows.sort()
    print("\nshare series — top 5 (mean weekly MAE, alpha, beta):")
    for mae, a, b, pers in share_rows[:5]:
        print(f"  MAE {mae:.6f}  alpha={a} beta={b}  (persistence {pers:.6f})")

    card_rows = []
    for a, b in product(ALPHA_GRID, BETA_GRID):
        cres = run_card_walkforward(card_panel.values, idx, a, b)
        card_rows.append((cres.mean_mae_model(), a, b, cres.mean_mae_persistence()))
    card_rows.sort()
    print("\ncard series — top 5 (mean weekly MAE, alpha, beta):")
    for mae, a, b, pers in card_rows[:5]:
        print(f"  MAE {mae:.6f}  alpha={a} beta={b}  (persistence {pers:.6f})")

    print(f"\nFROZEN: share alpha={share_rows[0][1]} beta={share_rows[0][2]};"
          f" card alpha={card_rows[0][1]} beta={card_rows[0][2]}")


if __name__ == "__main__":
    main()
