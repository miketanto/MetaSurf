"""EXPLORATORY — macro strategy structure + empirical tech-card discovery.

NOT a validated gate result. Two cheap, honest experiments on the owner's
"macrostrategy / tech-card" idea, each measured on real data.

EXPERIMENT 1 — is there "kind beats kind" structure? (goal 1)
Helmholtz-Hodge / HodgeRank decomposition (Jiang-Lim-Yao-Ye 2011) of the
Layer-2 archetype matchup matrix, in log-odds space, weighted by pair match
count. Splits the pairwise flow into a TRANSITIVE part (a global strength
ranking — "deck A is just better") and a CYCLIC residual (rock-paper-scissors
— "A beats B beats C beats A", i.e. kind-beats-kind). The cyclic fraction
quantifies how much of matchup structure is NOT explained by a linear power
ranking. If it is non-trivial, macro strategy-types are real structure.

EXPERIMENT 2 — do people tech against rising decks, with identifiable cards? (goal 2)
For each top target archetype A, correlate A's weekly meta share with the
weekly SIDEBOARD-inclusion rate of every card AMONG DECKS THAT ARE NOT A
(so we measure the field teching against A, not A's own cards). The top
positively-correlated cards are candidate "tech vs A", discovered purely from
co-movement — no pre-tagging. We then print each card's Scryfall type_line /
oracle_text (from the committed raw snapshot) to check whether the discovered
tech is semantically coherent (does the anti-A card actually mention A's key
permanent type / mechanic?). This tests whether tech is (a) real and (b)
auto-discoverable, and whether card text can *explain* it after the fact.

Run: python -m validation.v3_evolution.macro_tech_explore
"""

from __future__ import annotations

import gzip
import json
from pathlib import Path
from typing import Any

import numpy as np
import psycopg

from db.connection import database_url
from models.winrate import WinrateModel
from validation.v2_winrates.data import load_match_data, n_archetype_slots

TOP_N_ARCHETYPES = 25  # for the Hodge decomposition
N_TARGETS = 4  # tech-discovery target archetypes (by total share)
MIN_CARD_DECKS = 200  # a card must appear in >= this many sideboards overall
MIN_WEEKS = 30
RAW = Path("data/scryfall/oracle-cards.jsonl.gz")


def top_archetypes(post: Any, names: dict[int, str], k: int) -> list[int]:
    evidence = (post.arch_alpha + post.arch_beta)
    order = np.argsort(-evidence)
    return [int(i) for i in order if int(i) in names][:k]


def hodge_decomposition(
    W: np.ndarray, weights: np.ndarray
) -> tuple[float, np.ndarray]:
    """Weighted HodgeRank. W[a,b]=P(a beats b); weights[a,b]=pair match count.
    Returns (cyclic energy fraction, transitive potential phi)."""
    eps = 1e-6
    s = np.log(np.clip(W, eps, 1 - eps)) - np.log(np.clip(1 - W, eps, 1 - eps))
    s = 0.5 * (s - s.T)  # enforce antisymmetry
    w = weights.copy()
    np.fill_diagonal(w, 0.0)
    # weighted graph Laplacian L phi = div, div_a = sum_b w_ab s_ab
    deg = w.sum(axis=1)
    lap = np.diag(deg) - w
    div = (w * s).sum(axis=1)
    phi, *_ = np.linalg.lstsq(lap, div, rcond=None)
    trans = phi[:, None] - phi[None, :]  # gradient (transitive) flow
    resid = s - trans  # cyclic residual
    total_energy = float((w * s**2).sum())
    cyclic_energy = float((w * resid**2).sum())
    return (cyclic_energy / total_energy if total_energy > 0 else 0.0), phi


def load_card_text() -> dict[str, tuple[str, str]]:
    out: dict[str, tuple[str, str]] = {}
    with gzip.open(RAW, "rt") as f:
        for line in f:
            o = json.loads(line)
            name = o.get("name")
            if name and name not in out:
                out[name] = (o.get("type_line") or "", (o.get("oracle_text") or "")[:120])
    return out


def experiment_1(conn: psycopg.Connection) -> None:
    data, names, _ = load_match_data(conn, "modern")
    slots = n_archetype_slots(names)
    post = WinrateModel().fit(data, int(data.day.max()) + 1, slots)
    raw = WinrateModel(half_life_days=None, hierarchical=False).fit(
        data, int(data.day.max()) + 1, slots
    )
    ids = top_archetypes(post, names, TOP_N_ARCHETYPES)
    a = np.repeat(ids, len(ids))
    b = np.tile(ids, len(ids))
    W = post.match_prob(a, b).reshape(len(ids), len(ids))
    counts = (raw.pair_wins + raw.pair_losses)[np.ix_(ids, ids)]
    cyclic_frac, phi = hodge_decomposition(W, counts)

    print("=" * 70)
    print("EXPERIMENT 1 — macro strategy structure (Hodge decomposition)")
    print("=" * 70)
    print(f"top {len(ids)} archetypes by evidence; matchup flow in log-odds,"
          f" weighted by pair match count")
    print(f"\n  TRANSITIVE (global power ranking) energy: {1 - cyclic_frac:.1%}")
    print(f"  CYCLIC   (kind-beats-kind / RPS)  energy: {cyclic_frac:.1%}")
    order = np.argsort(-phi)
    print("\n  transitive strength ranking (HodgeRank potential):")
    for r in order[:8]:
        print(f"    {phi[r]:+.3f}  {names[ids[r]]}")
    print("    ...")
    for r in order[-4:]:
        print(f"    {phi[r]:+.3f}  {names[ids[r]]}")
    # biggest cyclic triples: A>B>C>A far from the ranking
    print("\n  strongest rock-paper-scissors triangles (cyclic residual):")
    eps = 1e-6
    s = np.log(np.clip(W, eps, 1 - eps)) - np.log(np.clip(1 - W, eps, 1 - eps))
    trans = phi[:, None] - phi[None, :]
    resid = s - trans
    triples = []
    for i in range(len(ids)):
        for j in range(i + 1, len(ids)):
            for k in range(j + 1, len(ids)):
                cyc = resid[i, j] + resid[j, k] + resid[k, i]
                if counts[i, j] > 30 and counts[j, k] > 30 and counts[k, i] > 30:
                    triples.append((abs(cyc), cyc, i, j, k))
    triples.sort(reverse=True)
    for _, cyc, i, j, k in triples[:5]:
        loop = (i, j, k) if cyc > 0 else (i, k, j)
        nm = [names[ids[x]] for x in loop]
        print(f"    {nm[0]} -> {nm[1]} -> {nm[2]} -> (back)  |cyclic|={abs(cyc):.2f}")


def experiment_2(conn: psycopg.Connection) -> None:
    print("\n" + "=" * 70)
    print("EXPERIMENT 2 — empirical tech-card discovery")
    print("=" * 70)
    card_text = load_card_text()
    with conn.cursor() as cur:
        # target archetypes by total labeled weekend decks
        cur.execute(
            """
            SELECT a.id, a.name, count(*) AS decks
            FROM decks d JOIN events e ON e.id = d.event_id
            JOIN archetypes a ON a.id = d.archetype_id
            JOIN formats f ON f.id = e.format_id AND f.name = 'modern'
            WHERE extract(isodow FROM e.date) IN (6,7)
            GROUP BY 1,2 ORDER BY 3 DESC LIMIT %s
            """,
            (N_TARGETS,),
        )
        targets = cur.fetchall()

    for arch_id, arch_name, _ndecks in targets:
        with conn.cursor() as cur:
            # A's weekly share
            cur.execute(
                """
                WITH wk AS (
                  SELECT date_trunc('week', e.date-5)::date+5 AS sat,
                         count(*) FILTER (WHERE d.archetype_id = %s) AS a_decks,
                         count(*) AS total
                  FROM decks d JOIN events e ON e.id = d.event_id
                  JOIN formats f ON f.id = e.format_id AND f.name='modern'
                  WHERE extract(isodow FROM e.date) IN (6,7)
                  GROUP BY 1)
                SELECT sat, a_decks::float/total FROM wk ORDER BY sat
                """,
                (arch_id,),
            )
            share_rows = cur.fetchall()
            share = {s: v for s, v in share_rows}
            # weekly sideboard inclusion rate of each card AMONG NON-A decks
            cur.execute(
                """
                WITH nonA AS (
                  SELECT d.id, date_trunc('week', e.date-5)::date+5 AS sat
                  FROM decks d JOIN events e ON e.id = d.event_id
                  JOIN formats f ON f.id = e.format_id AND f.name='modern'
                  WHERE extract(isodow FROM e.date) IN (6,7)
                    AND d.archetype_id IS DISTINCT FROM %s
                ), tot AS (SELECT sat, count(*) n FROM nonA GROUP BY 1),
                inc AS (
                  SELECT n.sat, dc.card_id, count(DISTINCT n.id) c
                  FROM nonA n JOIN deck_cards dc ON dc.deck_id = n.id
                  WHERE dc.board='side'
                  GROUP BY 1,2
                )
                SELECT inc.card_id, c2.name, inc.sat, inc.c::float/tot.n
                FROM inc JOIN tot ON tot.sat=inc.sat
                JOIN cards c2 ON c2.id = inc.card_id
                WHERE inc.card_id IN (
                  SELECT card_id FROM deck_cards dc2 JOIN nonA n2 ON n2.id=dc2.deck_id
                  WHERE dc2.board='side' GROUP BY 1 HAVING count(DISTINCT n2.id) >= %s)
                """,
                (arch_id, MIN_CARD_DECKS),
            )
            rows = cur.fetchall()

        # assemble per-card weekly inclusion aligned to share weeks
        weeks = sorted(share)
        share_vec = np.array([share[w] for w in weeks])
        by_card: dict[int, tuple[str, dict]] = {}
        for card_id, cname, sat, rate in rows:
            by_card.setdefault(card_id, (cname, {}))[1][sat] = rate
        scored = []
        for _card_id, (cname, series) in by_card.items():
            inc = np.array([series.get(w, 0.0) for w in weeks])
            if (inc > 0).sum() < MIN_WEEKS:
                continue
            if inc.std() == 0 or share_vec.std() == 0:
                continue
            r = float(np.corrcoef(share_vec, inc)[0, 1])
            scored.append((r, cname))
        scored.sort(reverse=True)
        print(f"\n## tech discovered against '{arch_name}'"
              f" (top sideboard cards among NON-{arch_name} decks, by"
              f" corr with {arch_name}'s share):")
        for r, cname in scored[:6]:
            tl, txt = card_text.get(cname, ("?", ""))
            print(f"  r={r:+.2f}  {cname:<24} [{tl}] {txt}")


def experiment_3(conn: psycopg.Connection) -> None:
    """Multi-week share study: is share more predictable at longer horizons,
    and does the cyclic structure show up as mean reversion? For each horizon
    h, over the universe archetypes, measure (a) autocorrelation of share
    between week t and t+h, and (b) directional 'trend-continuation' accuracy:
    given share rose over the last h weeks, does it keep rising the next h?"""
    from validation.v3_evolution.data import load_share_panel
    from validation.v3_evolution.tune import PANEL_FIRST_SATURDAY, PANEL_LAST_SATURDAY
    from validation.v3_evolution.walkforward import universe_mask

    panel, _ = load_share_panel(conn, "modern", PANEL_FIRST_SATURDAY, PANEL_LAST_SATURDAY)
    assert panel.counts is not None
    V, C = panel.values, panel.counts
    print("\n" + "=" * 70)
    print("EXPERIMENT 3 — multi-week share predictability & mean reversion")
    print("=" * 70)
    print(f"{'horizon':>8} {'share autocorr(t,t+h)':>22} {'trend-continues acc':>21}"
          f" {'n':>7}")
    for h in (1, 2, 4, 8):
        xs_l: list[float] = []
        ys_l: list[float] = []
        ac_a: list[float] = []
        ac_b: list[float] = []
        for j in range(h, V.shape[1] - h):
            uni = universe_mask(C, j)
            if not uni.any():
                continue
            past = V[uni, j] - V[uni, j - h]
            future = V[uni, j + h] - V[uni, j]
            ac_a.extend(V[uni, j].tolist())
            ac_b.extend(V[uni, j + h].tolist())
            for p, f in zip(past, future, strict=True):
                if abs(p) < 1e-6:
                    continue
                xs_l.append(float(np.sign(p)))
                ys_l.append(float(np.sign(f)))
        xs, ys = np.array(xs_l), np.array(ys_l)
        cont = float(np.mean(xs == ys)) if len(xs) else float("nan")
        ac = float(np.corrcoef(ac_a, ac_b)[0, 1])
        print(f"{h:>8} {ac:>22.3f} {cont:>20.1%} {len(xs):>7}")
    print("  (trend-continues > 50% = momentum; < 50% = mean reversion / cycling)")


def main() -> None:
    with psycopg.connect(database_url()) as conn:
        experiment_1(conn)
        experiment_2(conn)
        experiment_3(conn)


if __name__ == "__main__":
    main()
