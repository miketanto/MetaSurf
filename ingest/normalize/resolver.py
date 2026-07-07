"""Card-name -> cards.id resolution.

All card references resolve through the `cards` table (CLAUDE.md rule 3).
The map is built from real card rows; unresolvable names are returned to the
caller for logging — never guessed, never spell-corrected.

MTG name variants observed in the corpus (see the schema note):
- split/aftermath/adventure cards appear as combined 'A // B' names;
- double-faced cards appear as front-face-only names.
The cards table stores the canonical full name plus face names in attrs, so we
index both. Full names win over face names on collision.
"""

from __future__ import annotations

import psycopg


class CardResolver:
    def __init__(self, by_name: dict[str, int]):
        self._by_name = by_name
        # casefold fallback for pure case mismatches (still exact spelling)
        self._by_casefold: dict[str, int] = {}
        for name, cid in by_name.items():
            self._by_casefold.setdefault(name.casefold(), cid)

    @classmethod
    def from_db(cls, conn: psycopg.Connection, game: str) -> CardResolver:
        by_name: dict[str, int] = {}
        face_names: dict[str, int] = {}
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT c.id, c.name, c.attrs->'face_names'
                FROM cards c JOIN games g ON g.id = c.game_id
                WHERE g.name = %s
                ORDER BY c.id
                """,
                (game,),
            )
            for cid, name, faces in cur:
                by_name.setdefault(name, cid)
                if faces:
                    for f in faces:
                        face_names.setdefault(f, cid)
        for f, cid in face_names.items():
            by_name.setdefault(f, cid)
        return cls(by_name)

    def resolve(self, name: str) -> int | None:
        cid = self._by_name.get(name)
        if cid is not None:
            return cid
        return self._by_casefold.get(name.casefold())

    def __len__(self) -> int:
        return len(self._by_name)
