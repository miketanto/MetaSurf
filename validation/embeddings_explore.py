"""EXPLORATORY — card2vec embeddings, archetype recovery, macro strategy axes.

NOT a validated gate. Builds a co-occurrence card embedding from the Modern
corpus (models.embeddings, deterministic PPMI-SVD) and runs three checks:

1. CARD SANITY — nearest neighbours of a few known cards should be
   functionally/archetypically related (qualitative).
2. ARCHETYPE RECOVERY (quantitative validation) — a deck's vector = mean of
   its cards' vectors; classify each sampled deck by its nearest ARCHETYPE
   CENTROID and compare to its rule/label. High accuracy vs the
   majority-class baseline = the embedding, trained with zero label
   supervision, has recovered the archetype structure.
3. MACRO STRATEGY AXES — cluster archetype centroids into K groups (KMeans,
   fixed seed) and characterise each by objective features (avg mainboard cmc,
   creature share) + most distinctive cards + member archetypes. Strategy
   NAMES (aggro/control/combo/…) are deliberately NOT assigned from memory
   (CLAUDE.md rule 4) — the clusters and their measured features are printed
   for the owner to name. Then aggregate the Layer-2 matchup matrix to a KxK
   macro matrix and report its transitive-vs-cyclic split (the type-level
   rock-paper-scissors).

Run: python -m validation.embeddings_explore
"""

from __future__ import annotations

import gzip
import json

import numpy as np
import psycopg
from scipy import sparse
from sklearn.cluster import KMeans

from db.connection import database_url
from models.embeddings import embed, nearest
from models.winrate import WinrateModel
from validation.v2_winrates.data import load_match_data, n_archetype_slots
from validation.v3_evolution.macro_tech_explore import hodge_decomposition

MIN_DECK_FREQ = 100
DIM = 50
N_MACRO = 6
KMEANS_SEED = 20260707
SAMPLE_STRIDE = 40  # deterministic deck subsample for recovery accuracy
SANITY_CARDS = [
    "Urza's Tower", "Ancient Stirrings", "Griselbrand", "Amulet of Vigor",
    "Goblin Guide", "Counterspell",
]


def build(conn: psycopg.Connection) -> tuple:
    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT dc.card_id, c.name, count(DISTINCT dc.deck_id) n
            FROM deck_cards dc
            JOIN decks d ON d.id = dc.deck_id
            JOIN events e ON e.id = d.event_id
            JOIN formats f ON f.id = e.format_id AND f.name = 'modern'
            JOIN cards c ON c.id = dc.card_id
            WHERE dc.board = 'main' AND c.attrs->>'type_line' NOT LIKE 'Basic Land%%'
            GROUP BY 1, 2 HAVING count(DISTINCT dc.deck_id) >= %s
            ORDER BY dc.card_id
            """,
            (MIN_DECK_FREQ,),
        )
        vocab_rows = cur.fetchall()
        card_id = np.array([r[0] for r in vocab_rows])
        card_name = [r[1] for r in vocab_rows]
        col_of = {int(cid): k for k, cid in enumerate(card_id)}

        cur.execute(
            """
            SELECT d.id, d.archetype_id, dc.card_id
            FROM decks d
            JOIN events e ON e.id = d.event_id
            JOIN formats f ON f.id = e.format_id AND f.name = 'modern'
            JOIN deck_cards dc ON dc.deck_id = d.id AND dc.board = 'main'
            WHERE d.archetype_id IS NOT NULL
            ORDER BY d.id
            """
        )
        deck_ids: list[int] = []
        deck_arch: list[int] = []
        rows: list[int] = []
        cols: list[int] = []
        cur_deck = None
        ridx = -1
        for did, arch, cid in cur:
            if int(cid) not in col_of:
                continue
            if did != cur_deck:
                cur_deck = did
                ridx += 1
                deck_ids.append(int(did))
                deck_arch.append(int(arch))
            rows.append(ridx)
            cols.append(col_of[int(cid)])
    n_decks = len(deck_ids)
    D = sparse.csr_matrix(
        (np.ones(len(rows)), (rows, cols)), shape=(n_decks, len(card_id))
    )
    return card_id, card_name, np.array(deck_arch), D


def card_attrs(names: list[str]) -> dict[str, tuple[float, bool]]:
    want = set(names)
    out: dict[str, tuple[float, bool]] = {}
    with gzip.open("data/scryfall/oracle-cards.jsonl.gz", "rt") as f:
        for line in f:
            o = json.loads(line)
            nm = o.get("name")
            if nm in want and nm not in out:
                out[nm] = (float(o.get("cmc") or 0.0), "Creature" in (o.get("type_line") or ""))
    return out


def main() -> None:
    with psycopg.connect(database_url()) as conn:
        card_id, card_name, deck_arch, D = build(conn)
        cooc = np.asarray((D.T @ D).todense())
        vecs = embed(cooc, dim=DIM)

        print(f"vocab {len(card_id)} cards, {D.shape[0]} decks, dim {DIM}")
        print("\n1) CARD NEIGHBOURS (sanity)")
        name_to_row = {n: i for i, n in enumerate(card_name)}
        for cn in SANITY_CARDS:
            if cn not in name_to_row:
                continue
            nbrs = nearest(vecs, name_to_row[cn], k=5)
            print(f"  {cn:22s} -> " + ", ".join(card_name[j] for j, _ in nbrs))

        # deck vectors = normalized mean of member card vectors
        deg = np.asarray(D.sum(axis=1)).ravel()
        deg[deg == 0] = 1
        deck_vecs = np.asarray(D @ vecs) / deg[:, None]
        dn = np.linalg.norm(deck_vecs, axis=1, keepdims=True)
        dn[dn == 0] = 1
        deck_vecs /= dn

        # archetype centroids (>= 30 decks)
        arch_ids = np.unique(deck_arch)
        cents = {}
        sizes = {}
        for a in arch_ids:
            m = deck_arch == a
            if m.sum() >= 30:
                c = deck_vecs[m].mean(axis=0)
                nrm = np.linalg.norm(c)
                cents[int(a)] = c / nrm if nrm else c
                sizes[int(a)] = int(m.sum())
        cent_ids = sorted(cents)
        cent_mat = np.array([cents[a] for a in cent_ids])

        # 2) archetype recovery: nearest-centroid classification on a subsample
        idx = np.arange(0, D.shape[0], SAMPLE_STRIDE)
        sims = deck_vecs[idx] @ cent_mat.T
        pred = np.array(cent_ids)[sims.argmax(axis=1)]
        true = deck_arch[idx]
        mask = np.isin(true, cent_ids)
        acc = float((pred[mask] == true[mask]).mean())
        # majority baseline
        _, counts = np.unique(true[mask], return_counts=True)
        baseline = float(counts.max() / counts.sum())
        print("\n2) ARCHETYPE RECOVERY (nearest-centroid, zero label supervision)")
        print(f"  top-1 accuracy {acc:.3f} over {int(mask.sum())} sampled decks"
              f"  (majority-class baseline {baseline:.3f})")

        # names for archetypes + card attrs
        with conn.cursor() as cur:
            cur.execute("SELECT id, name FROM archetypes")
            arch_name: dict[int, str] = dict(cur.fetchall())
        attrs = card_attrs(card_name)
        cmc = np.array([attrs.get(n, (0.0, False))[0] for n in card_name])
        is_cre = np.array([attrs.get(n, (0.0, False))[1] for n in card_name], dtype=float)

        # 3) macro clusters over archetype centroids
        km = KMeans(n_clusters=N_MACRO, random_state=KMEANS_SEED, n_init=10)
        lab = km.fit_predict(cent_mat)
        print(f"\n3) MACRO STRATEGY AXES (KMeans k={N_MACRO}; names for the OWNER"
              " to assign — features are data-derived)")
        # mean deck-level cmc / creature-share per archetype, for characterization
        deck_cmc = np.asarray(D @ cmc).ravel() / deg
        deck_cre = np.asarray(D @ is_cre).ravel() / deg
        for cl in range(N_MACRO):
            members = [cent_ids[i] for i in range(len(cent_ids)) if lab[i] == cl]
            if not members:
                continue
            mdecks = np.isin(deck_arch, members)
            avg_cmc = float(deck_cmc[mdecks].mean())
            avg_cre = float(deck_cre[mdecks].mean())
            # most distinctive cards: highest mean presence among cluster decks
            pres = np.asarray(D[mdecks].mean(axis=0)).ravel()
            top_cards = [card_name[i] for i in np.argsort(-pres)[:6]]
            top_members = sorted(members, key=lambda a: -sizes[a])[:6]
            print(f"\n  cluster {cl}: avg mainboard cmc {avg_cmc:.2f},"
                  f" creature share {avg_cre:.2f}, {len(members)} archetypes")
            print(f"    archetypes: {', '.join(arch_name[a] for a in top_members)}")
            print(f"    signature cards: {', '.join(top_cards)}")

        # macro matchup matrix (Layer-2 aggregated by cluster, size-weighted)
        data, names, _ = load_match_data(conn, "modern")
        slots = n_archetype_slots(names)
        post = WinrateModel().fit(data, int(data.day.max()) + 1, slots)
        a = np.repeat(cent_ids, len(cent_ids))
        b = np.tile(cent_ids, len(cent_ids))
        W = post.match_prob(a, b).reshape(len(cent_ids), len(cent_ids))
        w_arch = np.array([sizes[a_] for a_ in cent_ids], dtype=float)
        macro = np.full((N_MACRO, N_MACRO), 0.5)
        for c1 in range(N_MACRO):
            for c2 in range(N_MACRO):
                r = lab == c1
                cc = lab == c2
                if r.any() and cc.any():
                    wr = np.outer(w_arch[r], w_arch[cc])
                    macro[c1, c2] = float((W[np.ix_(r, cc)] * wr).sum() / wr.sum())
        counts = np.outer(
            [int(w_arch[lab == c].sum()) for c in range(N_MACRO)],
            [int(w_arch[lab == c].sum()) for c in range(N_MACRO)],
        ).astype(float)
        cyclic, _ = hodge_decomposition(macro, counts)
        print(f"\n  macro {N_MACRO}x{N_MACRO} matchup matrix — transitive"
              f" {1 - cyclic:.1%} / cyclic {cyclic:.1%} (type-level RPS)")
        print("   " + " ".join(f"c{c}" for c in range(N_MACRO)))
        for c1 in range(N_MACRO):
            print(f"  c{c1} " + " ".join(f"{macro[c1, c2]:.2f}" for c2 in range(N_MACRO)))


if __name__ == "__main__":
    main()
