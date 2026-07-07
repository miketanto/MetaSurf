"""EXPLORATORY M3.5b prototype — "which deck should I bring?" backtest.

NOT a validated result. Tests the owner's counter-adaptation idea directly and
honestly: instead of forecasting exact shares (M3.5 showed that is noise-
dominated), does a *recommendation* that anticipates how the field adapts win
more REAL matches than naive strategies?

Each evaluation Saturday t we pick one archetype from the trailing-1% universe
by four strategies, using only data before t, then score it by its ACTUAL
match winrate that weekend (from the matches table — independent of the model,
so no circularity, and the weekend is the future relative to the pick, so no
leakage):

  POPULAR      argmax share_{t-1}                     (bring the most-played deck)
  PAST_WINNER  argmax Layer-2 winrate as-of t         (bring last stretch's best deck)
  BR_CURRENT   argmax_a Σ_b W[a,b]·share_{t-1}[b]     (best response to the CURRENT field)
  BR_ANTICIP   argmax_a Σ_b W[a,b]·x̂_t[b]             (best response to the ANTICIPATED
                                                       field: one replicator step ahead)

W is the as-of Layer-2 matchup matrix; x̂_t is a single replicator step from
share_{t-1} (eta=REPLICATOR_ETA). Realized winrate is match-level (draws
excluded), pooled over the weeks each strategy's pick cleared MIN_MATCHES.
A one-sample t-test reports whether mean realized winrate differs from 0.500.

The owner's specific hypotheses this checks:
  - PAST_WINNER should UNDERperform if winners get teched against (V3.2's
    negative coupling) — "don't just bring last week's best deck".
  - BR_CURRENT / BR_ANTICIP should clear 0.500 if a best-positioned deck is
    exploitable, and BR_ANTICIP should beat BR_CURRENT if anticipating
    adaptation adds value.

Run: python -m validation.v3_evolution.recommendation_explore
"""

from __future__ import annotations

import datetime as dt

import numpy as np
import psycopg
from scipy import stats as sps

from db.connection import database_url
from models.evolution import replicator_step
from models.winrate import WinrateModel
from validation.v2_winrates.data import load_match_data, n_archetype_slots
from validation.v3_evolution.data import load_share_panel
from validation.v3_evolution.run import EVAL_FIRST_SATURDAY, EVAL_LAST_SATURDAY
from validation.v3_evolution.tune import PANEL_FIRST_SATURDAY, PANEL_LAST_SATURDAY
from validation.v3_evolution.walkforward import universe_mask

REPLICATOR_ETA = 1.0  # from M3.5 eval-optimal; the field barely moves anyway
MIN_MATCHES = 15  # weekend match floor for a pick's realized winrate to count
STRATEGIES = ("POPULAR", "PAST_WINNER", "BR_CURRENT", "BR_ANTICIP")


def realized_winrates(
    conn: psycopg.Connection,
) -> dict[tuple[dt.date, int], tuple[int, int]]:
    """(saturday, archetype_id) -> (match_wins, match_losses), draws excluded,
    counted from both sides of each match. Saturday = weekend bucket key."""
    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT date_trunc('week', e.date - 5)::date + 5 AS sat,
                   da.archetype_id AS arch,
                   split_part(m.result, '-', 1)::int AS w,
                   split_part(m.result, '-', 2)::int AS l,
                   db.archetype_id AS arch_b
            FROM matches m
            JOIN events e ON e.id = m.event_id
            JOIN formats f ON f.id = e.format_id AND f.name = 'modern'
            JOIN decks da ON da.id = m.deck_id_a
            LEFT JOIN decks db ON db.id = m.deck_id_b
            WHERE extract(isodow FROM e.date) IN (6, 7)
            """
        )
        out: dict[tuple[dt.date, int], list[int]] = {}
        for sat, arch_a, w, lo, arch_b in cur.fetchall():
            if w == lo:
                continue  # draw, no signal
            a_won = w > lo
            if arch_a is not None:
                key = (sat, int(arch_a))
                cell = out.setdefault(key, [0, 0])
                cell[0 if a_won else 1] += 1
            if arch_b is not None:
                key = (sat, int(arch_b))
                cell = out.setdefault(key, [0, 0])
                cell[1 if a_won else 0] += 1
    return {k: (v[0], v[1]) for k, v in out.items()}


def main() -> None:
    with psycopg.connect(database_url()) as conn:
        panel, _totals = load_share_panel(
            conn, "modern", PANEL_FIRST_SATURDAY, PANEL_LAST_SATURDAY
        )
        data, names, _ = load_match_data(conn, "modern")
        realized = realized_winrates(conn)
    assert panel.counts is not None
    counts = panel.counts
    slots = n_archetype_slots(names)
    model = WinrateModel()
    ids = panel.entity_ids
    n = len(ids)
    ai = np.repeat(ids, n)
    bi = np.tile(ids, n)
    sats = panel.saturdays
    eval_idx = [i for i, s in enumerate(sats)
                if EVAL_FIRST_SATURDAY <= s <= EVAL_LAST_SATURDAY]

    picks: dict[str, list[float]] = {s: [] for s in STRATEGIES}
    pick_names: dict[str, list[str]] = {s: [] for s in STRATEGIES}

    for j in eval_idx:
        uni = universe_mask(counts, j)
        if not uni.any() or j < 1:
            continue
        uni_ids = ids[uni]
        post = model.fit(data, sats[j].toordinal(), slots)
        W = post.match_prob(ai, bi).reshape(n, n)
        x_prev = panel.values[:, j - 1]
        # restrict the field to the universe and renormalize
        xu = x_prev[uni]
        xu = xu / xu.sum() if xu.sum() > 0 else xu
        Wu = W[np.ix_(uni, uni)]
        overall = post.archetype_mean()[uni_ids]
        x_hat = replicator_step(xu, Wu, REPLICATOR_ETA)

        choice = {
            "POPULAR": int(uni_ids[np.argmax(xu)]),
            "PAST_WINNER": int(uni_ids[np.argmax(overall)]),
            "BR_CURRENT": int(uni_ids[np.argmax(Wu @ xu)]),
            "BR_ANTICIP": int(uni_ids[np.argmax(Wu @ x_hat)]),
        }
        for strat, arch in choice.items():
            wl = realized.get((sats[j], arch))
            if wl is None or (wl[0] + wl[1]) < MIN_MATCHES:
                continue
            picks[strat].append(wl[0] / (wl[0] + wl[1]))
            pick_names[strat].append(names.get(arch, str(arch)))

    print(f"eval weeks: {len(eval_idx)};"
          f" realized-winrate floor {MIN_MATCHES} matches/weekend\n")
    print(f"{'strategy':<12} {'weeks':>5} {'mean realized WR':>17}"
          f" {'std':>7} {'t vs .500':>10} {'p':>8}")
    for strat in STRATEGIES:
        vals = np.array(picks[strat])
        if len(vals) < 2:
            print(f"{strat:<12} {len(vals):>5}  (too few)")
            continue
        t, p = sps.ttest_1samp(vals, 0.5)
        print(f"{strat:<12} {len(vals):>5} {vals.mean():>17.4f}"
              f" {vals.std(ddof=1):>7.4f} {t:>10.2f} {p:>8.4f}")

    # head-to-head: on weeks where BOTH picks scored, does anticipation help?
    print("\nhead-to-head BR_ANTICIP vs BR_CURRENT (same weeks both scored):")
    paired_a, paired_c = [], []
    # rebuild paired series
    for j in eval_idx:
        uni = universe_mask(counts, j)
        if not uni.any() or j < 1:
            continue
        uni_ids = ids[uni]
        post = model.fit(data, sats[j].toordinal(), slots)
        W = post.match_prob(ai, bi).reshape(n, n)
        xu = panel.values[uni, j - 1]
        xu = xu / xu.sum() if xu.sum() > 0 else xu
        Wu = W[np.ix_(uni, uni)]
        x_hat = replicator_step(xu, Wu, REPLICATOR_ETA)
        cur_a = int(uni_ids[np.argmax(Wu @ xu)])
        ant_a = int(uni_ids[np.argmax(Wu @ x_hat)])
        wl_c = realized.get((sats[j], cur_a))
        wl_a = realized.get((sats[j], ant_a))
        if not wl_c or not wl_a:
            continue
        if wl_c[0] + wl_c[1] < MIN_MATCHES or wl_a[0] + wl_a[1] < MIN_MATCHES:
            continue
        paired_c.append(wl_c[0] / (wl_c[0] + wl_c[1]))
        paired_a.append(wl_a[0] / (wl_a[0] + wl_a[1]))
    if len(paired_a) >= 2:
        diff = np.array(paired_a) - np.array(paired_c)
        same_pick = sum(1 for a, c in zip(paired_a, paired_c, strict=True) if a == c)
        t, p = sps.ttest_1samp(diff, 0.0)
        print(f"  paired weeks {len(diff)} (identical pick in {same_pick}):"
              f" mean WR diff {diff.mean():+.4f}  t={t:.2f} p={p:.4f}")


if __name__ == "__main__":
    main()
