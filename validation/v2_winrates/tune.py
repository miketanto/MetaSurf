"""Hyperparameter tuning for the winrate model (half-life, prior strengths).

Grid search scored by mean per-week walk-forward log-loss over the TUNING
weeks — Saturdays 2022-07-02 .. 2023-12-30, chosen to be disjoint from and
strictly before the V2.1 evaluation weeks (2024-01-06 .. 2025-03-29), so no
hyperparameter ever sees an evaluation weekend (CLAUDE.md tuning hygiene).

The winning values are frozen into models/winrate/model.py as the defaults
and quoted in the V2 report together with this grid.

Run: python -m validation.v2_winrates.tune
"""

from __future__ import annotations

import datetime as dt
from itertools import product

import psycopg

from db.connection import database_url
from models.winrate import WinrateModel
from validation.v2_winrates.data import load_match_data, n_archetype_slots
from validation.v2_winrates.walkforward import run_walkforward, saturdays

TUNING_FIRST_SATURDAY = dt.date(2022, 7, 2)
TUNING_LAST_SATURDAY = dt.date(2023, 12, 30)

HALF_LIFE_GRID: tuple[float, ...] = (
    7.0, 10.0, 14.0, 21.0, 28.0, 42.0, 63.0, 91.0, 126.0, 182.0, 365.0, 730.0,
)
PRIOR_STRENGTH_GRID: tuple[float, ...] = (5.0, 10.0, 20.0, 50.0)
PAIR_PRIOR_STRENGTH_GRID: tuple[float, ...] = (5.0, 10.0, 20.0, 50.0)


def main() -> None:
    with psycopg.connect(database_url()) as conn:
        data, names, stats = load_match_data(conn, "modern")
    n = n_archetype_slots(names)
    print(stats.summary())
    cutoffs = saturdays(TUNING_FIRST_SATURDAY, TUNING_LAST_SATURDAY)
    print(f"tuning weeks: {len(cutoffs)} Saturdays"
          f" {TUNING_FIRST_SATURDAY} .. {TUNING_LAST_SATURDAY}")

    rows: list[tuple[float, float, float, float, int]] = []
    for hl, k0, k1 in product(HALF_LIFE_GRID, PRIOR_STRENGTH_GRID, PAIR_PRIOR_STRENGTH_GRID):
        model = WinrateModel(half_life_days=hl, prior_strength=k0, pair_prior_strength=k1)
        res = run_walkforward(data, n, cutoffs, model)
        mean_ll = sum(res.model_ll) / len(res.model_ll)
        rows.append((mean_ll, hl, k0, k1, len(res.model_ll)))
        print(f"half_life={hl:5.1f} k0={k0:5.1f} k1={k1:5.1f}"
              f" -> mean weekly log-loss {mean_ll:.6f} over {len(res.model_ll)} weeks")

    rows.sort(key=lambda r: (r[0], r[1], r[2], r[3]))
    print("\ntop 5 configurations:")
    for mean_ll, hl, k0, k1, nw in rows[:5]:
        print(f"  log-loss {mean_ll:.6f}  half_life={hl} prior_strength={k0}"
              f" pair_prior_strength={k1} ({nw} weeks)")
    best = rows[0]
    print(f"\nFROZEN: half_life_days={best[1]}, prior_strength={best[2]},"
          f" pair_prior_strength={best[3]}")


if __name__ == "__main__":
    main()
