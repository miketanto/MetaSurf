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


def _deck_cards(conn: psycopg.Connection, format_name: str) -> dict[int, dict[str, list[str]]]:
    """Full decklist per labeled deck: {deck_id: {'main': [...], 'side': [...]}},
    each entry '<count> <card name>', sorted by count desc then name."""
    out: dict[int, dict[str, list[str]]] = {}
    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT d.id, dc.board, dc.count, c.name
            FROM decks d
            JOIN events e ON e.id = d.event_id
            JOIN formats f ON f.id = e.format_id AND f.name = %s
            JOIN deck_cards dc ON dc.deck_id = d.id
            JOIN cards c ON c.id = dc.card_id
            WHERE d.archetype_id IS NOT NULL
            ORDER BY d.id, dc.board, dc.count DESC, c.name
            """,
            (format_name,),
        )
        for did, board, count, name in cur:
            zone = "main" if board == "main" else "side"
            out.setdefault(did, {"main": [], "side": []})[zone].append(f"{count} {name}")
    return out


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
    include_cards: bool = False,
) -> list[dict[str, Any]]:
    """2D point per labeled deck: card2vec deck embedding -> t-SNE. Decks with
    no vocab-card overlap (all cards below the frequency floor) are dropped.
    With ``include_cards``, each point carries its full 'main'/'side' list."""
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
    cards = _deck_cards(conn, format_name) if include_cards else {}
    out: list[dict[str, Any]] = []
    for m, (x, y) in zip(kept_meta, coords, strict=True):
        rec = {**m, "x": round(float(x), 3), "y": round(float(y), 3)}
        if include_cards:
            rec["main"] = cards.get(m["deck_id"], {}).get("main", [])
            rec["side"] = cards.get(m["deck_id"], {}).get("side", [])
        out.append(rec)
    return out


_PALETTE = [
    "#e6194b", "#3cb44b", "#4363d8", "#f58231", "#911eb4", "#42d4f4", "#f032e6",
    "#bfef45", "#fb9a99", "#469990", "#a678f0", "#9a6324", "#800000", "#33a02c",
    "#808000", "#000075", "#e07b39", "#ff5ab3", "#00b4a0", "#7a5c00",
]
_OTHER = "#9aa0a6"


def render_html(points: list[dict[str, Any]], title: str = "Modern deck map") -> str:
    """A self-contained interactive page: scatter of decks; click a dot to read
    its full decklist. Requires points built with include_cards=True."""
    import collections

    cnt = collections.Counter(p["archetype"] for p in points)
    top = [a for a, _ in cnt.most_common(len(_PALETTE))]
    cidx = {a: i for i, a in enumerate(top)}
    colors = [*_PALETTE, _OTHER]
    xs = [p["x"] for p in points]
    ys = [p["y"] for p in points]
    minx, maxx, miny, maxy = min(xs), max(xs), min(ys), max(ys)

    def nrm(v: float, lo: float, hi: float) -> int:
        return round((v - lo) / ((hi - lo) or 1) * 1000)

    events: list[str] = []
    eidx: dict[str, int] = {}

    def ecode(e: str) -> int:
        if e not in eidx:
            eidx[e] = len(events)
            events.append(e)
        return eidx[e]

    recs = [
        {
            "x": nrm(p["x"], minx, maxx),
            "y": nrm(p["y"], miny, maxy),
            "c": cidx.get(p["archetype"], len(top)),
            "a": p["archetype"],
            "p": p.get("player") or "?",
            "e": ecode(p.get("event") or ""),
            "d": p.get("date", ""),
            "m": p.get("main", []),
            "s": p.get("side", []),
        }
        for p in points
    ]
    legend = [{"a": a, "n": cnt[a], "i": i} for i, a in enumerate(top)]
    if len(cnt) > len(top):
        legend.append(
            {"a": "Other", "n": sum(v for k, v in cnt.items() if k not in cidx), "i": len(top)}
        )
    data = json.dumps(
        {"pts": recs, "ev": events, "col": colors, "leg": legend,
         "total": len(points), "narch": len(cnt)},
        separators=(",", ":"),
    )
    return _load_template().replace("__TITLE__", title).replace("__DATA__", data)


_TEMPLATE_PATH = Path(__file__).resolve().parent / "deck_map_template.html"


def _load_template() -> str:
    return _TEMPLATE_PATH.read_text(encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--format", default="modern", dest="format_name")
    parser.add_argument("--min-deck-freq", type=int, default=8)
    parser.add_argument("--out", type=Path, default=Path("data/state/deck_map.json"))
    parser.add_argument(
        "--html", type=Path, default=None,
        help="also write a standalone interactive page (click a dot -> decklist)",
    )
    args = parser.parse_args()
    with psycopg.connect(database_url()) as conn:
        points = build_deck_map(
            conn, args.format_name, min_deck_freq=args.min_deck_freq,
            include_cards=args.html is not None,
        )
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(points, indent=1))
    by_arch: dict[str, int] = {}
    for p in points:
        by_arch[p["archetype"]] = by_arch.get(p["archetype"], 0) + 1
    top = sorted(by_arch.items(), key=lambda kv: -kv[1])[:12]
    print(f"{len(points)} decks mapped -> {args.out}")
    print("top archetypes: " + ", ".join(f"{a}={n}" for a, n in top))
    if args.html is not None:
        args.html.parent.mkdir(parents=True, exist_ok=True)
        args.html.write_text(
            render_html(points, title=f"{args.format_name.title()} deck map")
        )
        print(f"interactive page -> {args.html}")


if __name__ == "__main__":
    main()
