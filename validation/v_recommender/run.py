"""V-REC — deck-recommender validation (hardens M3.5b).

Pre-registered blocked walk-forward over the full frozen span. Every knob
below is fixed before the run; the suite is executed once and the numbers
stand (CLAUDE.md: no target lowering, no window cherry-picking).

PROTOCOL (frozen)
- Decision cadence: every Saturday in EVAL_FIRST..EVAL_LAST with a non-empty
  universe. Universe(t) = archetypes with >= 1% pooled share over the trailing
  8 weekends strictly before t (training data only), same rule as V3.1/M3.5b.
- Strategies (pick ONE archetype from the universe, past data only):
    MODEL     = best response to the current field
                (argmax_a Σ_b W[a,b]·share_{t-1}[b], W fit on matches < Sat t)
    STRONGEST = highest Layer-2 overall winrate as-of t ("bring a strong deck")
    POPULAR   = most-played last weekend (naive baseline)
- Scoring: the pick's REALIZED match winrate that weekend, from the matches
  table (model-independent → no circularity; weekend t is the future relative
  to the pick → no leakage). Draws excluded. A pick counts only if it played
  >= MIN_MATCHES that weekend; per-strategy coverage is reported.
- Primary metric: mean of per-week realized winrate (each scored week = one
  observation), matching M3.5b. Secondary: match-weighted pooled winrate.
- Blocks: calendar quarters. Reported individually for stability, and split by
  whether the quarter overlaps the winrate-model tuning window
  (2022-07..2023-12) — the recommender adds no parameters, so consistent
  performance across tuned/untuned quarters is the robustness evidence.

ACCEPTANCE (frozen before running)
  V-REC.1  pooled MODEL realized winrate, 95% CI lower bound > 0.500 (real edge)
  V-REC.2  pooled MODEL >= pooled POPULAR (beats naive popularity)
  V-REC.3  MODEL mean realized winrate > 0.500 in >= 75% of quarters that have
           >= 4 scored weeks (stability)
  Reported, not gated: MODEL vs STRONGEST (the positioning bonus over pure
  strength — expected small per M3.5b).
"""

from __future__ import annotations

import datetime as dt
from collections import defaultdict
from typing import Any

import numpy as np
import psycopg
from scipy import stats as sps

from models.recommender import (
    best_response_index,
    most_popular_index,
    strongest_index,
)
from models.winrate import WinrateModel
from validation.v2_winrates.data import load_match_data, n_archetype_slots
from validation.v3_evolution.data import load_share_panel
from validation.v3_evolution.walkforward import universe_mask

EVAL_FIRST = dt.date(2022, 1, 1)
EVAL_LAST = dt.date(2025, 3, 29)
PANEL_FIRST = dt.date(2021, 1, 2)  # >= 8 weekends of warm-up before EVAL_FIRST
PANEL_LAST = dt.date(2025, 3, 29)
MIN_MATCHES = 15
TUNING_OVERLAP = (dt.date(2022, 7, 1), dt.date(2023, 12, 31))
STRATEGIES = ("MODEL", "STRONGEST", "POPULAR")
STABILITY_MIN_WEEKS = 4
STABILITY_TARGET = 0.75


def realized_winrates(
    conn: psycopg.Connection, format_name: str
) -> dict[tuple[dt.date, int], tuple[int, int]]:
    """(saturday, archetype) -> (match_wins, match_losses), draws excluded,
    counted from both sides of each weekend match."""
    with conn.cursor() as cur:
        cur.execute(
            """
            WITH mm AS (
              SELECT date_trunc('week', e.date - 5)::date + 5 AS sat,
                     da.archetype_id AS aa, db.archetype_id AS ab,
                     split_part(m.result,'-',1)::int AS w,
                     split_part(m.result,'-',2)::int AS l
              FROM matches m
              JOIN events e ON e.id = m.event_id
              JOIN formats f ON f.id = e.format_id AND f.name = %s
              JOIN decks da ON da.id = m.deck_id_a
              LEFT JOIN decks db ON db.id = m.deck_id_b
              WHERE extract(isodow FROM e.date) IN (6, 7)
            )
            SELECT sat, aa, ab, w, l FROM mm WHERE w <> l
            """,
            (format_name,),
        )
        out: dict[tuple[dt.date, int], list[int]] = {}
        for sat, aa, ab, w, lo in cur.fetchall():
            a_won = w > lo
            if aa is not None:
                cell = out.setdefault((sat, int(aa)), [0, 0])
                cell[0 if a_won else 1] += 1
            if ab is not None:
                cell = out.setdefault((sat, int(ab)), [0, 0])
                cell[1 if a_won else 0] += 1
    return {k: (v[0], v[1]) for k, v in out.items()}


def _quarter(d: dt.date) -> str:
    return f"{d.year}Q{(d.month - 1) // 3 + 1}"


def _ci95(vals: np.ndarray) -> tuple[float, float]:
    """t-based 95% CI of the mean (deterministic; no bootstrap RNG)."""
    n = len(vals)
    if n < 2:
        return (float("nan"), float("nan"))
    m = float(vals.mean())
    se = float(vals.std(ddof=1)) / (n ** 0.5)
    h = float(sps.t.ppf(0.975, n - 1)) * se
    return (m - h, m + h)


def evaluate(conn: psycopg.Connection, format_name: str = "modern") -> dict[str, Any]:
    panel, _ = load_share_panel(conn, format_name, PANEL_FIRST, PANEL_LAST)
    assert panel.counts is not None
    data, names, _ = load_match_data(conn, format_name)
    realized = realized_winrates(conn, format_name)
    slots = n_archetype_slots(names)
    model = WinrateModel()
    ids = panel.entity_ids
    n = len(ids)
    ai = np.repeat(ids, n)
    bi = np.tile(ids, n)
    sats = panel.saturdays

    # per-strategy per-week (saturday, realized_wr, wins, losses)
    weekly: dict[str, list[tuple[dt.date, float, int]]] = {s: [] for s in STRATEGIES}
    for j, sat in enumerate(sats):
        if not (EVAL_FIRST <= sat <= EVAL_LAST) or j < 1:
            continue
        uni = universe_mask(panel.counts, j)
        if not uni.any():
            continue
        uid = ids[uni]
        post = model.fit(data, sat.toordinal(), slots)
        W = post.match_prob(ai, bi).reshape(n, n)[np.ix_(uni, uni)]
        xprev = panel.values[uni, j - 1]
        xprev = xprev / xprev.sum() if xprev.sum() > 0 else xprev
        overall = post.archetype_mean()[uid]
        picks = {
            "MODEL": int(uid[best_response_index(xprev, W)]),
            "STRONGEST": int(uid[strongest_index(overall)]),
            "POPULAR": int(uid[most_popular_index(xprev)]),
        }
        for strat, arch in picks.items():
            wl = realized.get((sat, arch))
            if wl is None or (wl[0] + wl[1]) < MIN_MATCHES:
                continue
            weekly[strat].append((sat, wl[0] / (wl[0] + wl[1]), wl[0] + wl[1]))

    # pooled + per-quarter aggregation
    pooled: dict[str, Any] = {}
    for strat in STRATEGIES:
        vals = np.array([w for _, w, _ in weekly[strat]])
        matchw = np.array([m for _, _, m in weekly[strat]], dtype=float)
        lo, hi = _ci95(vals)
        t, p = sps.ttest_1samp(vals, 0.5) if len(vals) >= 2 else (float("nan"),) * 2
        pooled[strat] = {
            "weeks": len(vals),
            "mean_wr": float(vals.mean()) if len(vals) else float("nan"),
            "ci_lo": lo,
            "ci_hi": hi,
            "t_vs_half": float(t),
            "p_vs_half": float(p),
            "match_weighted_wr": float((vals * matchw).sum() / matchw.sum())
            if matchw.sum() > 0
            else float("nan"),
        }

    quarters: dict[str, dict[str, list[float]]] = defaultdict(lambda: defaultdict(list))
    for strat in STRATEGIES:
        for sat, wr, _ in weekly[strat]:
            quarters[_quarter(sat)][strat].append(wr)
    per_quarter = []
    for q in sorted(quarters):
        row: dict[str, Any] = {"quarter": q}
        overlap = TUNING_OVERLAP[0] <= _quarter_start(q) <= TUNING_OVERLAP[1]
        row["tuning_overlap"] = overlap
        for strat in STRATEGIES:
            v = quarters[q][strat]
            row[strat] = (len(v), float(np.mean(v)) if v else float("nan"))
        per_quarter.append(row)

    # stability: quarters with >= STABILITY_MIN_WEEKS MODEL weeks, MODEL > .5
    model_qs = [r for r in per_quarter if r["MODEL"][0] >= STABILITY_MIN_WEEKS]
    stable = sum(1 for r in model_qs if r["MODEL"][1] > 0.5)
    stability_frac = stable / len(model_qs) if model_qs else float("nan")

    # tuning-overlap robustness
    def _mean_over(pred: Any) -> float:
        vs = [wr for strat_ok, sat, wr in _flat(weekly) if strat_ok == "MODEL" and pred(sat)]
        return float(np.mean(vs)) if vs else float("nan")

    overlap_wr = _mean_over(lambda s: TUNING_OVERLAP[0] <= s <= TUNING_OVERLAP[1])
    nonoverlap_wr = _mean_over(lambda s: not (TUNING_OVERLAP[0] <= s <= TUNING_OVERLAP[1]))

    # paired head-to-heads on weeks both scored
    def _paired(a: str, b: str) -> dict[str, Any]:
        da = {s: w for s, w, _ in weekly[a]}
        db = {s: w for s, w, _ in weekly[b]}
        common = sorted(set(da) & set(db))
        diff = np.array([da[s] - db[s] for s in common])
        if len(diff) < 2:
            return {"weeks": len(diff), "mean_diff": float("nan"), "p": float("nan")}
        _t, p = sps.ttest_1samp(diff, 0.0)
        return {
            "weeks": len(diff),
            "mean_diff": float(diff.mean()),
            "a_better_weeks": int((diff > 0).sum()),
            "p": float(p),
        }

    verdicts = {
        "V-REC.1 edge real (CI>0.5)": pooled["MODEL"]["ci_lo"] > 0.5,
        "V-REC.2 beats POPULAR": pooled["MODEL"]["mean_wr"] >= pooled["POPULAR"]["mean_wr"],
        "V-REC.3 stable (>=75% quarters)": stability_frac >= STABILITY_TARGET,
    }
    return {
        "pooled": pooled,
        "per_quarter": per_quarter,
        "stability_frac": stability_frac,
        "stability_quarters": len(model_qs),
        "overlap_wr": overlap_wr,
        "nonoverlap_wr": nonoverlap_wr,
        "model_vs_popular": _paired("MODEL", "POPULAR"),
        "model_vs_strongest": _paired("MODEL", "STRONGEST"),
        "verdicts": verdicts,
    }


def _flat(
    weekly: dict[str, list[tuple[dt.date, float, int]]],
) -> Any:
    for strat, rows in weekly.items():
        for sat, wr, _ in rows:
            yield strat, sat, wr


def _quarter_start(q: str) -> dt.date:
    year, qq = q.split("Q")
    return dt.date(int(year), (int(qq) - 1) * 3 + 1, 1)


def serialize(result: dict[str, Any]) -> str:
    """Deterministic serialization compared byte-for-byte across two runs."""
    lines = []
    for strat in STRATEGIES:
        p = result["pooled"][strat]
        lines.append(
            f"{strat} weeks={p['weeks']} wr={p['mean_wr']:.6f}"
            f" ci=[{p['ci_lo']:.6f},{p['ci_hi']:.6f}] t={p['t_vs_half']:.4f}"
            f" mww={p['match_weighted_wr']:.6f}"
        )
    lines.append(f"stability={result['stability_frac']:.6f}/{result['stability_quarters']}")
    lines.append(f"overlap={result['overlap_wr']:.6f} nonoverlap={result['nonoverlap_wr']:.6f}")
    for r in result["per_quarter"]:
        lines.append(
            f"{r['quarter']} " + " ".join(
                f"{s}={r[s][0]}:{r[s][1]:.6f}" for s in STRATEGIES
            )
        )
    return "\n".join(lines)
