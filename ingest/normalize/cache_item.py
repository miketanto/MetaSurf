"""Normalizer for MTGODecklistCache `CacheItem` JSON files.

Written strictly against the observed schema documented in
docs/notes/mtgodecklistcache-observed-schema.md and the real fixtures under
tests/fixtures/MTGODecklistCache/. Pure functions: no database access here.

Observed shape (all five sources):
    {"Tournament": {"Date", "Name", "Uri"},
     "Decks":      [{"Date"?, "Player", "Result", "AnchorUri",
                     "Mainboard": [{"CardName", "Count"}], "Sideboard": [...]}],
     "Rounds":     null | [{"RoundName", "Matches": [...]}],
     "Standings":  null | [{"Rank", "Player", "Points", "Wins", "Losses", "Draws", ...}]}

Rounds are deliberately NOT parsed here — match extraction is milestone M2;
raw files remain the source of truth via events.raw_ref.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import date, datetime
from pathlib import Path
from typing import Any

import orjson

# league/swiss records like "5-0"; round-robin style "2-1-0" never appears in
# Deck.Result in the observed data, but accept an optional third group defensively.
_RE_RECORD = re.compile(r"^(\d+)-(\d+)(?:-(\d+))?$")
_RE_PLACE = re.compile(r"^(\d+)(?:st|nd|rd|th) Place$")
# mtgo slugs: <format>-<event-type>-<yyyy>-<mm>-<dd><digits>
_RE_MTGO_EVENT_TYPE = re.compile(r"^[a-z0-9]+-(.+?)-\d{4}-\d{2}-\d{2}")


@dataclass(frozen=True)
class CardLine:
    name: str
    count: int
    board: str


@dataclass
class NormalizedDeck:
    player: str | None
    result_raw: str | None
    finish_rank: int | None
    wins: int | None
    losses: int | None
    draws: int | None
    cards: list[CardLine] = field(default_factory=list)


@dataclass
class NormalizedEvent:
    source: str
    source_event_id: str
    name: str | None
    event_date: date
    event_type: str | None
    player_count: int | None
    raw_ref: str
    decks: list[NormalizedDeck] = field(default_factory=list)
    # data-quality counters (observed: decks and standings routinely disagree)
    standings_only_players: int = 0
    decks_without_standing: int = 0
    # observed on melee.gg: literal {"Count": 0, ...} card entries (no-submit
    # artifacts); dropped at normalization, never written as deck_cards rows
    zero_count_card_lines: int = 0


def detect_format(filename: str, tokens_by_format: dict[str, tuple[str, ...]]) -> str | None:
    """Match hyphen-delimited tokens of the filename against format slug tokens.

    Returns the format name, or None when no (or more than one) format matches;
    callers must skip-and-count, never guess.
    """
    parts = set(Path(filename).stem.lower().split("-"))
    hits = [fmt for fmt, tokens in tokens_by_format.items() if any(t in parts for t in tokens)]
    if len(hits) == 1:
        return hits[0]
    return None


def derive_event_type(source: str, stem: str) -> str | None:
    """Event-type slug for mtgo sources (observed vocabulary: league, preliminary,
    challenge, challenge-32/64/96, daily-swiss, ...). Other sources carry no
    event-type data -> 'tournament'."""
    if source.startswith("mtgo.com"):
        m = _RE_MTGO_EVENT_TYPE.match(stem.lower())
        return m.group(1) if m else None
    return "tournament"


def parse_result(result: str | None) -> tuple[int | None, int | None, int | None, int | None]:
    """Parse Deck.Result -> (finish_rank, wins, losses, draws).

    Observed values: 'N-N' records, 'Nst/Nnd/Nrd/Nth Place', and ''.
    """
    if not result:
        return None, None, None, None
    m = _RE_RECORD.match(result)
    if m:
        draws = int(m.group(3)) if m.group(3) is not None else None
        return None, int(m.group(1)), int(m.group(2)), draws
    m = _RE_PLACE.match(result)
    if m:
        return int(m.group(1)), None, None, None
    return None, None, None, None


def _parse_event_date(tournament: dict[str, Any], fallback: str) -> date:
    """Tournament.Date is ISO-8601 with Z suffix; fall back to the yyyy/mm/dd
    in the file path if it is missing/unparseable."""
    raw = tournament.get("Date")
    if isinstance(raw, str):
        try:
            return datetime.fromisoformat(raw.replace("Z", "+00:00")).date()
        except ValueError:
            pass
    return datetime.strptime(fallback, "%Y/%m/%d").date()


def _aggregate_cards(
    deck: dict[str, Any], zone_map: dict[str, str]
) -> tuple[list[CardLine], int]:
    """Aggregate counts per (name, board); duplicate CardName lines within a
    zone are summed rather than dropped. Entries whose aggregate count is < 1
    (observed: literal Count 0 lines in melee.gg files) are dropped and
    counted — a zero-count entry is a card that is not in the deck."""
    agg: dict[tuple[str, str], int] = {}
    for json_key, board in zone_map.items():
        for entry in deck.get(json_key) or []:
            key = (entry["CardName"], board)
            agg[key] = agg.get(key, 0) + int(entry["Count"])
    dropped = sum(1 for c in agg.values() if c < 1)
    lines = [CardLine(name=n, count=c, board=b) for (n, b), c in sorted(agg.items()) if c >= 1]
    return lines, dropped


def normalize_file(
    path: Path,
    cache_root: Path,
    source: str,
) -> NormalizedEvent:
    """Parse one CacheItem file into a NormalizedEvent (cards still by name)."""
    raw = orjson.loads(path.read_bytes())
    tournament = raw.get("Tournament") or {}
    stem = path.stem
    rel = path.relative_to(cache_root).as_posix()
    # path layout: Tournaments/<source>/<yyyy>/<mm>/<dd>/<file>
    date_from_path = "/".join(rel.split("/")[2:5])
    event_date = _parse_event_date(tournament, date_from_path)

    standings = raw.get("Standings")
    standings_by_player: dict[str, dict[str, Any]] = {}
    if standings:
        for s in standings:
            p = s.get("Player")
            if p is not None:
                standings_by_player[p] = s

    zone_map = {"Mainboard": "main", "Sideboard": "side"}
    decks: list[NormalizedDeck] = []
    deck_players: set[str] = set()
    zero_count_lines = 0
    for deck in raw.get("Decks") or []:
        player = deck.get("Player")
        result_raw = deck.get("Result") or None
        finish_rank, wins, losses, draws = parse_result(result_raw)
        standing = standings_by_player.get(player) if player is not None else None
        if standing is not None:
            # standings carry the authoritative record where present
            finish_rank = standing.get("Rank", finish_rank)
            wins = standing.get("Wins", wins)
            losses = standing.get("Losses", losses)
            draws = standing.get("Draws", draws)
        if player is not None:
            deck_players.add(player)
        cards, dropped = _aggregate_cards(deck, zone_map)
        zero_count_lines += dropped
        decks.append(
            NormalizedDeck(
                player=player,
                result_raw=result_raw,
                finish_rank=finish_rank,
                wins=wins,
                losses=losses,
                draws=draws,
                cards=cards,
            )
        )

    standings_only = len(set(standings_by_player) - deck_players)
    decks_without_standing = (
        sum(1 for d in decks if d.player not in standings_by_player) if standings_by_player else 0
    )
    # field size: standings enumerate the full field where present; otherwise
    # published decks are the only signal we have
    player_count = len(standings_by_player) if standings_by_player else len(decks)

    return NormalizedEvent(
        source=source,
        source_event_id=stem,
        name=tournament.get("Name"),
        event_date=event_date,
        event_type=derive_event_type(source, stem),
        player_count=player_count,
        raw_ref=rel,
        decks=decks,
        standings_only_players=standings_only,
        decks_without_standing=decks_without_standing,
        zero_count_card_lines=zero_count_lines,
    )
