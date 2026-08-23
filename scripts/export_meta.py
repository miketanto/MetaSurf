"""Export a metagame snapshot as JSON for downstream mechanical analysis.

**Not the M5 read API.** This is a research/ops export: a read-only view of the
corpus written to a file, so that tools outside this repo (currently CardGuru's
answer engine) can consume real archetype shares and representative decklists
instead of scraping an aggregator. The M5 endpoints remain unbuilt and this
script does not prefigure their contract.

Representative decklist = the deck whose vector is closest to its archetype's
centroid over the window, reusing the M1 vectorizer and cosine similarity. That
is a deliberate choice over "most recent" or "best finish": the centroid deck is
the one whose card choices are most typical of the archetype, which is what a
mechanical analysis of "what does this deck do" should be reading.

Usage:
    python scripts/export_meta.py --start 2025-05-01 --end 2025-06-09 \
        --top 12 --out meta-modern.json
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

import numpy as np
import psycopg

from archetypes.classifier.vectorizer import vectorize
from db.connection import connect
from validation.v1_archetypes.common import (
    basic_land_ids,
    load_decks,
    load_definitions,
    rules_label,
)


def _card_names(conn: psycopg.Connection, deck_ids: list[int]) -> dict[int, dict[str, list]]:
    """deck_id -> {'main': [[name, count], ...], 'side': [...]}, name-sorted."""
    out: dict[int, dict[str, list]] = defaultdict(lambda: {"main": [], "side": []})
    if not deck_ids:
        return out
    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT dc.deck_id, dc.board, c.name, dc.count
            FROM deck_cards dc JOIN cards c ON c.id = dc.card_id
            WHERE dc.deck_id = ANY(%s)
            ORDER BY dc.deck_id, dc.board, c.name
            """,
            (deck_ids,),
        )
        for deck_id, board, name, count in cur:
            out[deck_id][board].append([name, count])
    return out


def _play_rates(
    conn: psycopg.Connection, start: dt.date, end: dt.date, min_decks: int
) -> dict[str, dict[str, Any]]:
    """card name -> how many decks in the window play it (either board).

    This is the **card-quality prior** CardGuru's `plan/product.md` §4 says the
    mechanical layer is missing ("mechanics propose, popularity re-ranks").
    Without it, every bounce spell ever printed ranks equal to the good ones,
    because mechanically they all answer a creature. Play rate is not card
    quality — it is a proxy, and a circular one — but it is a *format legality
    and viability filter* first and a ranking signal second, which is exactly
    what the mechanical layer cannot derive on its own.
    """
    rates: dict[str, dict[str, Any]] = {}
    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT c.name,
                   count(DISTINCT d.id) AS decks,
                   sum(dc.count) FILTER (WHERE dc.board = 'main') AS main_copies,
                   sum(dc.count) FILTER (WHERE dc.board = 'side') AS side_copies
            FROM deck_cards dc
            JOIN cards c ON c.id = dc.card_id
            JOIN decks d ON d.id = dc.deck_id
            JOIN events e ON e.id = d.event_id
            JOIN formats f ON f.id = e.format_id
            WHERE f.name = 'modern' AND e.date BETWEEN %s AND %s
            GROUP BY c.name
            HAVING count(DISTINCT d.id) >= %s
            ORDER BY c.name
            """,
            (start, end, min_decks),
        )
        for name, decks, main_copies, side_copies in cur:
            rates[name] = {
                "decks": int(decks),
                "main_copies": int(main_copies or 0),
                "side_copies": int(side_copies or 0),
            }
    return rates


def _deck_meta(conn: psycopg.Connection, deck_ids: list[int]) -> dict[int, dict[str, Any]]:
    meta: dict[int, dict[str, Any]] = {}
    if not deck_ids:
        return meta
    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT d.id, d.player, d.finish_rank, e.date, e.source, e.event_type
            FROM decks d JOIN events e ON e.id = d.event_id
            WHERE d.id = ANY(%s)
            """,
            (deck_ids,),
        )
        for deck_id, player, rank, date, source, event_type in cur:
            meta[deck_id] = {
                "player": player,
                "finish_rank": rank,
                "event_date": date.isoformat(),
                "source": source,
                "event_type": event_type,
            }
    return meta


def export(
    conn: psycopg.Connection,
    start: dt.date,
    end: dt.date,
    top: int,
    min_play_decks: int = 3,
) -> dict[str, Any]:
    defs, _ = load_definitions(conn)
    decks = load_decks(conn, start, end)
    classifications = rules_label(decks, defs)

    labelled: dict[int, str] = {}
    for d, c in zip(decks, classifications, strict=True):
        if c.match is not None and not c.conflict:
            labelled[d.deck_id] = c.match.archetype

    counts = Counter(labelled.values())
    total = len(decks)
    chosen = [name for name, _ in counts.most_common(top)]

    exclude = basic_land_ids(conn)
    vectors = vectorize([(d.deck_id, d.deck.main) for d in decks], exclude)
    row_of = {deck_id: i for i, deck_id in enumerate(vectors.deck_ids)}
    matrix = vectors.matrix

    archetypes: list[dict[str, Any]] = []
    representatives: list[int] = []
    for name in chosen:
        members = sorted(d for d, a in labelled.items() if a == name)
        rows = [row_of[d] for d in members if d in row_of]
        if not rows:
            continue
        # centroid over L2-normalized rows; representative = argmax cosine
        centroid = np.asarray(matrix[rows].mean(axis=0)).ravel()
        norm = np.linalg.norm(centroid)
        if norm:
            centroid = centroid / norm
        sims = np.asarray(matrix[rows] @ centroid).ravel()
        best = int(np.argmax(sims))
        rep_deck = members[best]
        representatives.append(rep_deck)
        archetypes.append(
            {
                "archetype": name,
                "decks": counts[name],
                "meta_share": counts[name] / total if total else 0.0,
                "representative_deck_id": rep_deck,
                "representative_similarity": float(sims[best]),
            }
        )

    names = _card_names(conn, representatives)
    deck_meta = _deck_meta(conn, representatives)
    for entry in archetypes:
        deck_id = entry["representative_deck_id"]
        entry["representative"] = {
            **deck_meta.get(deck_id, {}),
            "mainboard": names[deck_id]["main"],
            "sideboard": names[deck_id]["side"],
        }

    play_rates = _play_rates(conn, start, end, min_play_decks)
    for rate in play_rates.values():
        rate["deck_share"] = rate["decks"] / total if total else 0.0

    return {
        "format": "modern",
        "window": {"start": start.isoformat(), "end": end.isoformat()},
        "total_decks": total,
        "labelled_decks": len(labelled),
        "classifier_version": defs.classifier_version,
        "archetypes": archetypes,
        "play_rates": play_rates,
        "play_rate_min_decks": min_play_decks,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--start", type=dt.date.fromisoformat, required=True)
    parser.add_argument("--end", type=dt.date.fromisoformat, required=True)
    parser.add_argument("--top", type=int, default=12)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument(
        "--min-play-decks",
        type=int,
        default=3,
        help="minimum decks playing a card for it to appear in play_rates",
    )
    args = parser.parse_args()

    with connect() as conn:
        snapshot = export(conn, args.start, args.end, args.top, args.min_play_decks)

    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(snapshot, indent=2, sort_keys=True), encoding="utf-8")
    print(
        f"wrote {args.out}: {len(snapshot['archetypes'])} archetypes, "
        f"{snapshot['labelled_decks']}/{snapshot['total_decks']} decks labelled, "
        f"{len(snapshot['play_rates'])} cards in the play-rate prior"
    )
    for a in snapshot["archetypes"]:
        print(f"  {a['meta_share'] * 100:5.2f}%  {a['decks']:>5}  {a['archetype']}")


if __name__ == "__main__":
    main()
