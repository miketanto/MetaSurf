"""Deck map: project every labeled deck to 2D so archetype clusters are visible.

Reuses the validated stack — the card2vec co-occurrence embedding
(`models.embeddings`, M3.8, 0.773 archetype recovery) for card vectors, each
deck embedded as the mean of its (mainboard, non-basic) card vectors, then a
deterministic t-SNE to 2D. Output is a list of point records
(x, y, archetype, parent, player, event, …) for a scatter view.

Deterministic: fixed embedding seed (models.embeddings) + fixed t-SNE seed;
same corpus -> same coordinates.

Run: python -m validation.deck_map --out data/state/deck_map.json
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
from pathlib import Path
from typing import Any

import numpy as np
import psycopg
from scipy import sparse
from sklearn.manifold import TSNE

from db.connection import database_url
from models.embeddings import embed

TSNE_SEED = 20260707


def _fetch(conn: psycopg.Connection, format_name: str, min_deck_freq: int) -> tuple[Any, ...]:
    with conn.cursor() as cur:
        # vocab: mainboard, non-basic cards played in >= min_deck_freq decks
        cur.execute(
            """
            SELECT dc.card_id
            FROM deck_cards dc
            JOIN decks d ON d.id = dc.deck_id
            JOIN events e ON e.id = d.event_id
            JOIN formats f ON f.id = e.format_id AND f.name = %s
            JOIN cards c ON c.id = dc.card_id
            WHERE dc.board = 'main' AND c.attrs->>'type_line' NOT LIKE 'Basic Land%%'
            GROUP BY dc.card_id
            HAVING count(DISTINCT dc.deck_id) >= %s
            ORDER BY dc.card_id
            """,
            (format_name, min_deck_freq),
        )
        card_ids = [r[0] for r in cur.fetchall()]
        col_of = {cid: k for k, cid in enumerate(card_ids)}

        # decks + metadata (labeled decks only), with their vocab cards
        cur.execute(
            """
            SELECT d.id, a.name, p.name AS parent, d.player, e.name AS event,
                   e.date, e.source, dc.card_id
            FROM decks d
            JOIN archetypes a ON a.id = d.archetype_id
            LEFT JOIN archetypes p ON p.id = a.parent_id
            JOIN events e ON e.id = d.event_id
            JOIN formats f ON f.id = e.format_id AND f.name = %s
            JOIN deck_cards dc ON dc.deck_id = d.id AND dc.board = 'main'
            WHERE d.archetype_id IS NOT NULL
            ORDER BY d.id
            """,
            (format_name,),
        )
        decks: dict[int, dict[str, Any]] = {}
        rows: list[int] = []
        cols: list[int] = []
        order: list[int] = []
        for did, arch, parent, player, event, date, source, cid in cur:
            if did not in decks:
                decks[did] = {
                    "deck_id": did,
                    "archetype": arch,
                    "parent": parent,
                    "player": player,
                    "event": event,
                    "date": date.isoformat() if isinstance(date, dt.date) else str(date),
                    "source": source,
                }
                order.append(did)
            if cid in col_of:
                rows.append(len(order) - 1)
                cols.append(col_of[cid])
    meta = [decks[d] for d in order]
    D = sparse.csr_matrix(
        (np.ones(len(rows)), (rows, cols)), shape=(len(order), len(card_ids))
    )
    return card_ids, meta, D


def build_deck_map(
    conn: psycopg.Connection,
    format_name: str = "modern",
    min_deck_freq: int = 8,
    dim: int = 50,
    seed: int = TSNE_SEED,
) -> list[dict[str, Any]]:
    """2D point per labeled deck: card2vec deck embedding -> t-SNE. Decks with
    no vocab-card overlap (all cards below the frequency floor) are dropped."""
    _card_ids, meta, D = _fetch(conn, format_name, min_deck_freq)
    if D.shape[0] < 3 or D.shape[1] < 3:
        raise RuntimeError(
            f"not enough data to map ({D.shape[0]} decks, {D.shape[1]} vocab cards); "
            "lower --min-deck-freq or ingest more events"
        )
    cooc = np.asarray((D.T @ D).todense(), dtype=float)
    card_vecs = embed(cooc, dim=dim)  # (n_cards, dim), unit rows, deterministic
    counts = np.asarray(D.sum(axis=1)).ravel()
    deck_vecs = np.asarray(D @ card_vecs)
    nonzero = counts > 0
    deck_vecs[nonzero] /= counts[nonzero, None]
    norms = np.linalg.norm(deck_vecs, axis=1, keepdims=True)
    keep = (norms.ravel() > 0) & nonzero

    kept_vecs = deck_vecs[keep]
    kept_vecs = kept_vecs / np.linalg.norm(kept_vecs, axis=1, keepdims=True)
    n = kept_vecs.shape[0]
    perplexity = max(5.0, min(30.0, (n - 1) / 3.0))
    coords = TSNE(
        n_components=2,
        metric="cosine",
        init="pca",
        perplexity=perplexity,
        random_state=seed,
    ).fit_transform(kept_vecs)

    kept_meta = [m for m, k in zip(meta, keep, strict=True) if k]
    out: list[dict[str, Any]] = []
    for m, (x, y) in zip(kept_meta, coords, strict=True):
        out.append({**m, "x": round(float(x), 3), "y": round(float(y), 3)})
    return out


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--format", default="modern", dest="format_name")
    parser.add_argument("--min-deck-freq", type=int, default=8)
    parser.add_argument("--out", type=Path, default=Path("data/state/deck_map.json"))
    args = parser.parse_args()
    with psycopg.connect(database_url()) as conn:
        points = build_deck_map(conn, args.format_name, min_deck_freq=args.min_deck_freq)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(points, indent=1))
    by_arch: dict[str, int] = {}
    for p in points:
        by_arch[p["archetype"]] = by_arch.get(p["archetype"], 0) + 1
    top = sorted(by_arch.items(), key=lambda kv: -kv[1])[:12]
    print(f"{len(points)} decks mapped -> {args.out}")
    print("top archetypes: " + ", ".join(f"{a}={n}" for a, n in top))


if __name__ == "__main__":
    main()
