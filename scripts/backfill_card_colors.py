"""Backfill cards.attrs.color_identity from the Scryfall bulk (for deck colour
indicators). Idempotent: jsonb_set on each card matched by canonical_ref =
oracle_id. Run once after adding color_identity to the scryfall ingest."""

from __future__ import annotations

import json
from pathlib import Path

import psycopg

from db.connection import database_url

BULK = Path("data/scryfall/oracle-cards.jsonl")


def main() -> None:
    ci: dict[str, list[str]] = {}
    with BULK.open() as fh:
        for line in fh:
            d = json.loads(line)
            oid = d.get("oracle_id")
            if oid:
                ci[oid] = d.get("color_identity") or []

    with psycopg.connect(database_url()) as conn, conn.cursor() as cur:
        cur.execute("SELECT id, canonical_ref FROM cards")
        rows = cur.fetchall()
        updates = [
            (json.dumps(ci.get(ref, [])), cid) for cid, ref in rows
        ]
        cur.executemany(
            "UPDATE cards SET attrs = jsonb_set(attrs, '{color_identity}', %s::jsonb)"
            " WHERE id = %s",
            updates,
        )
        conn.commit()
        cur.execute(
            "SELECT count(*) FROM cards WHERE attrs ? 'color_identity'"
        )
        print(f"cards with color_identity: {cur.fetchone()[0]} / {len(rows)}")


if __name__ == "__main__":
    main()
