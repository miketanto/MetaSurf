"""Scryfall oracle-cards bulk file -> game-neutral `cards` table (MTG resolver).

Everything here is driven by the observed structure of the real bulk file —
see docs/notes/scryfall-oracle-cards-observed-schema.md. In particular:

- The file is JSONL (one card object per line); the legacy JSON-array framing
  (served in parallel until 2026-07-20) is detected by sniffing a leading '['.
- Non-playable layouts are skipped: their names collide with 2,320 playable
  card names in the observed file (decklist names must never resolve to
  tokens/emblems/art-series/etc.).
- `attrs.resolution_tier` is 1 for set_type in {funny, memorabilia}, else 0:
  the observed file has 14 duplicated playable full names, and in every case
  where a real tournament card collides with a variant (`Pick Your Poison`,
  `Red Herring`, `Fast // Furious`, `Unquenchable Fury`) the two sides are
  separated exactly by this set_type split. Cards are inserted ordered by
  (resolution_tier, oracle_id) so the resolver's first-wins-by-id rule
  deterministically prefers the real card.
- `attrs.face_names` lists face names when `card_faces` is present (8 layouts,
  always combined "A // B" top-level names). The corpus references split cards
  by combined name and DFCs by front-face name, so the resolver indexes both.
"""

from __future__ import annotations

import json
from collections import Counter
from collections.abc import Iterator
from dataclasses import dataclass, field
from pathlib import Path
from typing import IO, Any

import psycopg

# Observed non-playable layouts (full layout vocabulary of the file is in the
# schema note). These object classes cannot appear as decklist entries and
# massively collide with playable names.
EXCLUDED_LAYOUTS = frozenset(
    {
        "token",
        "double_faced_token",
        "emblem",
        "art_series",
        "vanguard",
        "scheme",
        "planar",
    }
)

# set_types whose cards lose name-collision ties against regular cards
# (observed: funny/playtest and memorabilia variants of real card names).
DEPRIORITIZED_SET_TYPES = frozenset({"funny", "memorabilia"})


@dataclass(frozen=True)
class CardRow:
    oracle_id: str
    name: str
    attrs: dict[str, Any]

    @property
    def resolution_tier(self) -> int:
        tier = self.attrs["resolution_tier"]
        assert isinstance(tier, int)
        return tier


@dataclass
class ScryfallStats:
    objects_seen: int = 0
    cards_imported: int = 0
    skipped_by_layout: Counter = field(default_factory=Counter)
    with_face_names: int = 0
    deprioritized: int = 0

    def summary(self) -> str:
        skipped = ", ".join(f"{k}={v}" for k, v in sorted(self.skipped_by_layout.items()))
        return "\n".join(
            [
                f"card objects seen:        {self.objects_seen}",
                f"cards imported:           {self.cards_imported}",
                f"  with face_names:        {self.with_face_names}",
                f"  resolution_tier=1:      {self.deprioritized}",
                f"skipped by layout:        {skipped or '(none)'}",
            ]
        )


def _iter_objects(fh: IO[str]) -> Iterator[dict[str, Any]]:
    """Yield card objects from JSONL or (legacy, pre-2026-07-20) JSON-array framing."""
    first = fh.read(1)
    while first and first.isspace():
        first = fh.read(1)
    fh.seek(0)
    if first == "[":
        yield from json.load(fh)
        return
    for line in fh:
        line = line.strip()
        if line:
            yield json.loads(line)


def _to_row(card: dict[str, Any]) -> CardRow:
    attrs: dict[str, Any] = {
        "layout": card["layout"],
        "set_type": card["set_type"],
        "type_line": card["type_line"],
        "resolution_tier": 1 if card["set_type"] in DEPRIORITIZED_SET_TYPES else 0,
        # per-format legality (Scryfall: legal / not_legal / banned / restricted).
        # Point-in-time snapshot as of the bulk file; used to tell whether a deck
        # is still legal in a rotating format (rotation/bans), not just played.
        "legalities": card.get("legalities") or {},
    }
    faces = card.get("card_faces")
    if faces:
        attrs["face_names"] = [f["name"] for f in faces]
    return CardRow(oracle_id=card["oracle_id"], name=card["name"], attrs=attrs)


def parse_cards(path: Path, stats: ScryfallStats | None = None) -> list[CardRow]:
    """Parse the bulk file into rows, sorted by (resolution_tier, oracle_id)
    so that insertion order (and therefore cards.id order, which the resolver
    uses as first-wins preference) is deterministic and prefers regular cards."""
    stats = stats if stats is not None else ScryfallStats()
    rows: list[CardRow] = []
    seen: set[str] = set()
    with open(path, encoding="utf-8") as fh:
        for card in _iter_objects(fh):
            stats.objects_seen += 1
            if card["layout"] in EXCLUDED_LAYOUTS:
                stats.skipped_by_layout[card["layout"]] += 1
                continue
            if card["oracle_id"] in seen:  # 0 observed; guard stays for safety
                raise ValueError(f"duplicate oracle_id in bulk file: {card['oracle_id']}")
            seen.add(card["oracle_id"])
            row = _to_row(card)
            rows.append(row)
            if "face_names" in row.attrs:
                stats.with_face_names += 1
            if row.resolution_tier == 1:
                stats.deprioritized += 1
    rows.sort(key=lambda r: (r.resolution_tier, r.oracle_id))
    stats.cards_imported = len(rows)
    return rows


def load_cards(conn: psycopg.Connection, rows: list[CardRow], game: str = "mtg") -> None:
    """COPY rows into the cards table for `game`. The table must be empty for
    the game (rebuilds always start from a fresh database; a partial cards
    table would make resolution silently incomplete)."""
    with conn.cursor() as cur:
        cur.execute("INSERT INTO games (name) VALUES (%s) ON CONFLICT (name) DO NOTHING", (game,))
        cur.execute("SELECT id FROM games WHERE name = %s", (game,))
        row = cur.fetchone()
        assert row is not None
        game_id = row[0]
        cur.execute("SELECT count(*) FROM cards WHERE game_id = %s", (game_id,))
        existing = cur.fetchone()
        assert existing is not None
        if existing[0]:
            raise RuntimeError(
                f"cards table already has {existing[0]} rows for game {game!r}; "
                "card ingestion runs once per rebuild on an empty table"
            )
        with cur.copy("COPY cards (game_id, canonical_ref, name, attrs) FROM STDIN") as copy:
            for r in rows:
                copy.write_row((game_id, r.oracle_id, r.name, json.dumps(r.attrs)))
    conn.commit()
