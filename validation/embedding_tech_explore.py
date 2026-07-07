"""EXPLORATORY — can embeddings + data isolate tech cards?

NOT a validated gate. Tests one specific claim: embedding-measured card
FLEXIBILITY removes the archetype-identity confound from the matchup-DiD tech
signal (research-log §4c).

Recap of §4c on Eldrazi:
- naive share-correlation -> board wipes (generic creature answers, confound 1)
- matchup difference-in-differences (does card C improve the A matchup more
  than other matchups) removes the board wipes but surfaces STORM SIGNATURE
  cards (Past in Flames, ...) because Ruby Storm structurally beats Eldrazi
  (confound 2: archetype identity).

Embedding fix: a card's FLEXIBILITY = 1 - max cosine(card vector, archetype
centroid). Signature/engine cards sit ON their archetype's centroid (low
flexibility); splashable ANSWER cards (removal, counters, bounce) are played
across many decks and sit far from any one centroid (high flexibility). Real
tech is flexible. So we rank by matchup-DiD but KEEP only flexible cards.

Result to look for: the flexible-tech list drops the Storm identity cards and
keeps coherent answers. Honest about the remaining limit (co-occurrence can't
fully separate function from colour/archetype) is in the printout.

Run: python -m validation.embedding_tech_explore
"""

from __future__ import annotations

import gzip
import json

import numpy as np
import psycopg

from db.connection import database_url
from models.embeddings import embed
from validation.embeddings_explore import build

TARGETS = ("Eldrazi", "GenericTron")
MIN_VS_A = 40
MIN_SIDE_DECKS = 150
FLEX_SPLIT = 0.5  # flexibility threshold splitting "answer" vs "engine" cards


def card_text() -> dict[str, str]:
    out: dict[str, str] = {}
    with gzip.open("data/scryfall/oracle-cards.jsonl.gz", "rt") as f:
        for line in f:
            o = json.loads(line)
            nm = o.get("name")
            if nm and nm not in out:
                out[nm] = (o.get("oracle_text") or "")[:80].replace("\n", " ")
    return out


def matchup_did(
    conn: psycopg.Connection, aid: int
) -> dict[int, tuple[float, float, int]]:
    """card_id -> (DiD, wr_has_vsA, n_vsA): does a sideboard card improve the
    A matchup more than it improves other matchups?"""
    with conn.cursor() as cur:
        cur.execute("DROP TABLE IF EXISTS _M")
        cur.execute(
            """
            CREATE TEMP TABLE _M AS
            WITH mm AS (
              SELECT m.deck_id_a da, m.deck_id_b db,
                     split_part(m.result,'-',1)::int w, split_part(m.result,'-',2)::int l,
                     da2.archetype_id aa, db2.archetype_id ab
              FROM matches m
              JOIN events e ON e.id=m.event_id
              JOIN formats f ON f.id=e.format_id AND f.name='modern'
              JOIN decks da2 ON da2.id=m.deck_id_a
              JOIN decks db2 ON db2.id=m.deck_id_b
              WHERE m.deck_id_b IS NOT NULL
            )
            SELECT da AS deck_id, (ab=%s) AS opp_is_a, (w>l) AS won FROM mm
              WHERE aa IS DISTINCT FROM %s AND w<>l
            UNION ALL
            SELECT db, (aa=%s), (l>w) FROM mm WHERE ab IS DISTINCT FROM %s AND w<>l
            """,
            (aid, aid, aid, aid),
        )
        cur.execute(
            "SELECT count(*) FILTER (WHERE opp_is_a AND won),"
            " count(*) FILTER (WHERE opp_is_a),"
            " count(*) FILTER (WHERE NOT opp_is_a AND won),"
            " count(*) FILTER (WHERE NOT opp_is_a) FROM _M"
        )
        grow = cur.fetchone()
        assert grow is not None
        gwa, ga, gwo, go = grow
        cur.execute(
            """
            SELECT dc.card_id,
              count(*) FILTER (WHERE _M.opp_is_a) va,
              count(*) FILTER (WHERE _M.opp_is_a AND _M.won) wa,
              count(*) FILTER (WHERE NOT _M.opp_is_a) vo,
              count(*) FILTER (WHERE NOT _M.opp_is_a AND _M.won) wo
            FROM _M JOIN deck_cards dc ON dc.deck_id=_M.deck_id AND dc.board='side'
            GROUP BY dc.card_id
            HAVING count(*) FILTER (WHERE _M.opp_is_a) >= %s
            """,
            (MIN_VS_A,),
        )
        out: dict[int, tuple[float, float, int]] = {}
        for cid, va, wa, vo, wo in cur.fetchall():
            if vo < 50 or ga - va < 50 or go - vo < 50:
                continue
            wr_has_a = wa / va
            wr_no_a = (gwa - wa) / (ga - va)
            wr_has_o = wo / vo
            wr_no_o = (gwo - wo) / (go - vo)
            did = (wr_has_a - wr_no_a) - (wr_has_o - wr_no_o)
            out[int(cid)] = (did, wr_has_a, va)
    return out


def main() -> None:
    with psycopg.connect(database_url()) as conn:
        card_id, card_name, deck_arch, D = build(conn)
        vecs = embed(np.asarray((D.T @ D).todense()), dim=50)
        row_of = {int(c): i for i, c in enumerate(card_id)}
        name_of = {int(c): n for c, n in zip(card_id, card_name, strict=True)}

        # archetype centroids in embedding space (>= 30 decks)
        deg = np.asarray(D.sum(axis=1)).ravel()
        deg[deg == 0] = 1
        deck_vecs = np.asarray(D @ vecs) / deg[:, None]
        dn = np.linalg.norm(deck_vecs, axis=1, keepdims=True)
        dn[dn == 0] = 1
        deck_vecs /= dn
        cents = []
        for a in np.unique(deck_arch):
            m = deck_arch == a
            if m.sum() >= 30:
                c = deck_vecs[m].mean(axis=0)
                nrm = np.linalg.norm(c)
                cents.append(c / nrm if nrm else c)
        cent_mat = np.array(cents)
        # EMBEDDING flexibility[card] = 1 - max cosine to any archetype centroid
        maxsim = (vecs @ cent_mat.T).max(axis=1)
        emb_flex = 1.0 - maxsim

        # DATA flexibility[card] = normalized entropy of its archetype-play
        # distribution (spread across many archetypes = answer; concentrated in
        # one = engine/signature). Computed over all boards.
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT dc.card_id, d.archetype_id, count(*)
                FROM deck_cards dc JOIN decks d ON d.id = dc.deck_id
                JOIN events e ON e.id = d.event_id
                JOIN formats f ON f.id = e.format_id AND f.name = 'modern'
                WHERE d.archetype_id IS NOT NULL AND dc.card_id = ANY(%s)
                GROUP BY 1, 2
                """,
                ([int(c) for c in card_id],),
            )
            dist: dict[int, dict[int, int]] = {}
            for cid, arch, cnt in cur.fetchall():
                dist.setdefault(int(cid), {})[int(arch)] = int(cnt)
        ent_flex: dict[int, float] = {}
        for cid, counts in dist.items():
            p = np.array(list(counts.values()), dtype=float)
            p /= p.sum()
            h = -(p * np.log(p)).sum()
            ent_flex[cid] = float(h / np.log(len(p))) if len(p) > 1 else 0.0

        txt = card_text()
        for target in TARGETS:
            with conn.cursor() as cur:
                cur.execute("SELECT id FROM archetypes WHERE name=%s", (target,))
                arow = cur.fetchone()
                assert arow is not None
                aid = arow[0]
                did = matchup_did(cur.connection, aid)
            scored = []
            for cid, (d, wra, va) in did.items():
                if cid not in row_of:
                    continue
                scored.append(
                    (d, emb_flex[row_of[cid]], ent_flex.get(cid, 0.0), wra, va, name_of[cid])
                )
            scored.sort(reverse=True)
            # percentile split (top half by each measure among these candidates)
            emb_med = float(np.median([s[1] for s in scored]))
            ent_med = float(np.median([s[2] for s in scored]))
            print("\n" + "=" * 74)
            print(f"TECH vs {target}: matchup-DiD top 12; two 'flexibility' controls")
            print("  emb=1-maxcos(card,archetype centroid) | ent=archetype-play entropy")
            print("=" * 74)
            print(f"{'DiD':>6} {'emb':>5} {'ent':>5} {'WRvsA':>6} {'nA':>4}  card")
            for d, ef, hf, wra, va, nm in scored[:12]:
                print(f"{d:+6.3f} {ef:5.2f} {hf:5.2f} {wra:6.3f} {va:4d}  {nm}"
                      f"  {txt.get(nm,'')[:44]}")
            emb_keep = [s[5] for s in scored[:12] if s[1] >= emb_med]
            ent_keep = [s[5] for s in scored[:12] if s[2] >= ent_med]
            print(f"\n  top-12 kept by EMBEDDING flex (>= median {emb_med:.2f}): "
                  + ", ".join(emb_keep))
            print(f"  top-12 kept by ENTROPY flex   (>= median {ent_med:.2f}): "
                  + ", ".join(ent_keep))


if __name__ == "__main__":
    main()
