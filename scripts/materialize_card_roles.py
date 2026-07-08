"""Materialize card -> functional-role membership into the card_roles table
(tech-finder research, BL-1). Roles come from the fixture-tested parser in
``archetypes.roles`` applied to real Scryfall oracle text from the bulk on
disk, joined to cards via canonical_ref = oracle_id. Derived / rebuildable.
"""

from __future__ import annotations

import json
from pathlib import Path

import psycopg

from archetypes.roles import roles_for_text
from db.connection import database_url

BULK = Path("data/scryfall/oracle-cards.jsonl")


def main() -> None:
    otext: dict[str, str | None] = {}
    with BULK.open() as fh:
        for line in fh:
            d = json.loads(line)
            oid = d.get("oracle_id")
            if oid:
                otext[oid] = d.get("oracle_text")

    with psycopg.connect(database_url()) as conn, conn.cursor() as cur:
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS card_roles (
                card_id bigint NOT NULL,
                role    text   NOT NULL,
                PRIMARY KEY (card_id, role)
            )
            """
        )
        cur.execute("TRUNCATE card_roles")
        cur.execute("SELECT id, canonical_ref FROM cards")
        cards = cur.fetchall()
        rows: list[tuple[int, str]] = []
        carded = 0
        for cid, ref in cards:
            roles = roles_for_text(otext.get(ref))
            if roles:
                carded += 1
                rows.extend((cid, r) for r in sorted(roles))
        cur.executemany("INSERT INTO card_roles (card_id, role) VALUES (%s, %s)", rows)
        conn.commit()

        print(f"cards total: {len(cards)}")
        print(f"cards with >=1 role: {carded} ({carded / len(cards) * 100:.1f}%)")
        print(f"role memberships: {len(rows)}")
        cur.execute("SELECT role, count(*) FROM card_roles GROUP BY role ORDER BY 2 DESC")
        for role, n in cur.fetchall():
            print(f"  {role:26} {n}")


if __name__ == "__main__":
    main()
