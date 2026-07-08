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
        cid = self._by_casefold.get(name.casefold())
        if cid is not None:
            return cid
        # Observed corpus variant (mtgo.com_limited_data, 2024-10 onward):
        # split-card names written 'A && B' where the canonical name is
        # 'A // B' — 18 distinct corpus names, every one matching a split
        # card in the bulk file (see the observed-schema notes). A purely
        # mechanical separator mapping; spellings are still never guessed.
        if " && " in name:
            return self.resolve(name.replace(" && ", " // "))
        # Live mtgo.com (2026) writes split-card names 'A/B' (no spaces) where
        # the canonical Scryfall name is 'A // B'. Verified 2026-07-08 against
        # the live corpus: every unresolved 'A/B' name (Wear/Tear x182,
        # Fire/Ice, Claim/Fame, Dead/Gone, Rough/Tumble, Repudiate/Replicate)
        # maps to a layout:split card present in the bulk. Same mechanical
        # separator normalisation as ' && ' — spellings are still never guessed
        # (it only resolves if the ' // ' form actually exists).
        if "/" in name and " // " not in name:
            return self.resolve(name.replace("/", " // "))
        return None

    def __len__(self) -> int:
        return len(self._by_name)
