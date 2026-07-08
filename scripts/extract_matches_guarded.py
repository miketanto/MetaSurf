"""Match extraction tolerant of mixed archive roots (tech-finder research).

Identical parsing to ``ingest.match_extract.extractor`` but skips events whose
raw file is absent under the cache clone — the live-scraped events store
``raw_ref`` against the scraper's own archive root, not the MTGODecklistCache
clone, so the strict extractor raises FileNotFoundError on them. Reuses the
production ``_deck_map`` / ``_extract_event`` / ``_copy_rows`` — no parsing is
reimplemented here.
"""

from __future__ import annotations

from pathlib import Path

import orjson
import psycopg

from db.connection import database_url
from ingest.match_extract.extractor import (
    BATCH_EVENTS,
    ExtractStats,
    _copy_rows,
    _deck_map,
    _extract_event,
)

CACHE_ROOT = Path("data/MTGODecklistCache")


def main() -> None:
    stats = ExtractStats()
    missing = 0
    with psycopg.connect(database_url()) as conn:
        with conn.cursor() as cur:
            cur.execute("DELETE FROM matches")
            cur.execute(
                "SELECT id, source, event_type, raw_ref FROM events"
                " WHERE raw_ref IS NOT NULL ORDER BY id"
            )
            events = cur.fetchall()
            batch: list = []
            pending = 0
            for event_id, source, event_type, raw_ref in events:
                stats.events_seen += 1
                path = CACHE_ROOT / raw_ref
                if not path.exists():
                    missing += 1
                    continue
                raw = orjson.loads(path.read_bytes())
                rounds = raw.get("Rounds") or []
                if not rounds:
                    stats.events_without_rounds += 1
                    continue
                if event_type is not None and "league" in event_type:
                    continue  # winner-censored; never feed league data to winrates
                stats.events_with_rounds += 1
                stats.by_source[source] += 1
                deck_map, ambiguous = _deck_map(cur, event_id)
                batch.extend(
                    _extract_event(event_id, source, rounds, deck_map, ambiguous, stats)
                )
                pending += 1
                if pending >= BATCH_EVENTS:
                    _copy_rows(cur, batch)
                    stats.matches_inserted += len(batch)
                    batch, pending = [], 0
            if batch:
                _copy_rows(cur, batch)
                stats.matches_inserted += len(batch)
        conn.commit()
    print(stats.summary())
    print(f"events with raw file missing under cache (live-scraped, skipped): {missing}")


if __name__ == "__main__":
    main()
