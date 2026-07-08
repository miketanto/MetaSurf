"""Pure parsers for live mtgo.com/decklists pages -> CacheItem-shaped dicts.

Written strictly against the real pages saved under tests/fixtures/mtgo.com/
and documented in docs/notes/mtgo-com-observed-schema.md. No network, no DB,
no side effects — every function takes page text and returns data, so the
whole parser is testable on saved fixture bytes (CLAUDE.md parser discipline).

The output dict matches the MTGODecklistCache `CacheItem` shape
(`Tournament`/`Decks`/`Rounds`/`Standings`) so that the existing
`ingest.normalize.cache_item`, `ingest.cache_import.importer`, and
`ingest.match_extract` consume live events unchanged.
"""

from __future__ import annotations

import json
import re
from datetime import datetime
from typing import Any

# The event payload is a one-line JS assignment: `window.MTGO.decklists.data = {…};`
# Match only the assignment head; the value is the rest of that physical line.
_RE_DATA = re.compile(r"window\.MTGO\.decklists\.data\s*=\s*")
# Listing anchors: href="/decklist/<site_name>"
_RE_LISTING = re.compile(r'href="/decklist/([A-Za-z0-9-]+)"')

BASE_URL = "https://www.mtgo.com"


class MtgoParseError(ValueError):
    """A live page did not match the observed structure. Fail loudly rather
    than ingest garbage (CLAUDE.md)."""


def parse_listing_slugs(html: str) -> list[str]:
    """Event site-name slugs linked from a /decklists listing page.

    Deterministic (sorted, de-duplicated) so fetch scheduling is reproducible.
    """
    return sorted({m.group(1) for m in _RE_LISTING.finditer(html)})


def extract_decklists_data(html: str) -> dict[str, Any] | None:
    """The `window.MTGO.decklists.data` payload, or None if the page carries no
    such assignment (e.g. a listing page or a redirect target). Raises
    MtgoParseError if the assignment exists but is not valid JSON."""
    m = _RE_DATA.search(html)
    if m is None:
        return None
    end = html.find("\n", m.end())
    raw = html[m.end() : end if end != -1 else len(html)].rstrip()
    if raw.endswith(";"):
        raw = raw[:-1].rstrip()
    try:
        obj = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise MtgoParseError(f"decklists.data is not valid JSON: {exc}") from exc
    if not isinstance(obj, dict):
        raise MtgoParseError(f"decklists.data is not an object: {type(obj).__name__}")
    return obj


def _iso_date(data: dict[str, Any]) -> str:
    """ISO-8601 event date. Tournaments carry `starttime`
    ('YYYY-MM-DD HH:MM:SS.s'); leagues carry `publish_date` ('YYYY-MM-DD')."""
    raw = data.get("starttime") or data.get("publish_date")
    if not isinstance(raw, str) or not raw:
        raise MtgoParseError("event payload has no starttime/publish_date")
    try:
        dt = datetime.fromisoformat(raw)
    except ValueError as exc:
        raise MtgoParseError(f"unparseable event date {raw!r}: {exc}") from exc
    return dt.strftime("%Y-%m-%dT%H:%M:%SZ")


def _ordinal_place(rank: int) -> str:
    """1 -> '1st Place', 2 -> '2nd Place', 11 -> '11th Place' — the
    `Nth Place` form the existing `parse_result` already handles."""
    suffix = "th"
    if not 10 <= rank % 100 <= 20:
        suffix = {1: "st", 2: "nd", 3: "rd"}.get(rank % 10, "th")
    return f"{rank}{suffix} Place"


def _card_lines(entries: Any, board_label: str) -> list[dict[str, Any]]:
    """One board's card entries -> [{CardName, Count}]. A missing card_name or
    qty is a structural break (fail loudly), not something to guess past."""
    out: list[dict[str, Any]] = []
    for entry in entries or []:
        try:
            name = entry["card_attributes"]["card_name"]
            count = int(entry["qty"])
        except (KeyError, TypeError, ValueError) as exc:
            raise MtgoParseError(
                f"malformed {board_label} card entry: {entry!r} ({exc})"
            ) from exc
        out.append({"CardName": name, "Count": count})
    return out


def _standings(data: dict[str, Any]) -> list[dict[str, Any]] | None:
    rows = data.get("standings")
    if not rows:
        return None
    out: list[dict[str, Any]] = []
    for s in rows:
        try:
            rank = int(s["rank"])
        except (KeyError, TypeError, ValueError) as exc:
            raise MtgoParseError(f"malformed standings row: {s!r} ({exc})") from exc
        row: dict[str, Any] = {"Rank": rank, "Player": s.get("login_name")}
        score = s.get("score")
        if score is not None:
            row["Points"] = int(score)
        # keep the tiebreak percentages for fidelity (unused by the normalizer)
        for src, dst in (
            ("opponentmatchwinpercentage", "OMWP"),
            ("gamewinpercentage", "GWP"),
            ("opponentgamewinpercentage", "OGWP"),
        ):
            if s.get(src) is not None:
                row[dst] = s[src]
        out.append(row)
    out.sort(key=lambda r: r["Rank"])
    return out


def _match_count_round_name(n_matches: int) -> str:
    """Bracket round name from its match count (Top-8 tree: 4/2/1)."""
    return {1: "Finals", 2: "Semifinals", 4: "Quarterfinals", 8: "Top 16"}.get(
        n_matches, f"Top {n_matches * 2}"
    )


def _rounds(data: dict[str, Any]) -> list[dict[str, Any]] | None:
    """`brackets` -> CacheItem Rounds. Results are Player1's-perspective
    `W-L-D` game counts (draws=0; brackets don't record draws) — the exact
    orientation `ingest.match_extract` documents and requires."""
    brackets = data.get("brackets")
    if not brackets:
        return None
    rounds: list[dict[str, Any]] = []
    # highest index = earliest round (Quarterfinals before Finals)
    for br in sorted(brackets, key=lambda b: b.get("index", 0), reverse=True):
        matches_out: list[dict[str, Any]] = []
        matches = br.get("matches") or []
        for match in matches:
            players = match.get("players") or []
            if not players:
                continue
            p1 = players[0]
            p2 = players[1] if len(players) > 1 else {}
            try:
                wins = int(p1["wins"])
                losses = int(p1["losses"])
            except (KeyError, TypeError, ValueError) as exc:
                raise MtgoParseError(f"malformed bracket match: {match!r} ({exc})") from exc
            matches_out.append(
                {
                    "Player1": p1.get("player"),
                    "Player2": p2.get("player"),
                    "Result": f"{wins}-{losses}-0",
                }
            )
        rounds.append(
            {"RoundName": _match_count_round_name(len(matches)), "Matches": matches_out}
        )
    return rounds


def _decks(data: dict[str, Any], rank_by_player: dict[str, int]) -> list[dict[str, Any]]:
    decks: list[dict[str, Any]] = []
    for dl in data.get("decklists") or []:
        player = dl.get("player")
        deck: dict[str, Any] = {
            "Player": player,
            "AnchorUri": None,
            "Mainboard": _card_lines(dl.get("main_deck"), "mainboard"),
            "Sideboard": _card_lines(dl.get("sideboard_deck"), "sideboard"),
        }
        wins = dl.get("wins")
        if isinstance(wins, dict) and "wins" in wins:
            # league 5-0 record: {"wins": "5", "losses": "0"}
            deck["Result"] = f"{int(wins['wins'])}-{int(wins.get('losses', 0))}"
        elif player is not None and player in rank_by_player:
            # tournament finish comes from the standings rank
            deck["Result"] = _ordinal_place(rank_by_player[player])
        else:
            deck["Result"] = ""
        decks.append(deck)
    return decks


def event_to_cacheitem(data: dict[str, Any]) -> dict[str, Any]:
    """Map an extracted event payload to a CacheItem-shaped dict.

    Tournament vs League is decided by the payload's own `type` field
    (`TOURNAMENT`) — leagues carry `publish_date`/`name` and per-deck `wins`,
    no standings or brackets.
    """
    is_tournament = data.get("type") == "TOURNAMENT"
    site_name = data.get("site_name")
    if not site_name:
        raise MtgoParseError("event payload has no site_name")

    standings = _standings(data) if is_tournament else None
    rounds = _rounds(data) if is_tournament else None
    rank_by_player: dict[str, int] = {}
    if standings:
        for row in standings:
            p = row.get("Player")
            if p is not None:
                rank_by_player.setdefault(p, row["Rank"])

    name = data.get("description") if is_tournament else data.get("name")
    return {
        "Tournament": {
            "Date": _iso_date(data),
            "Name": name,
            "Uri": f"{BASE_URL}/decklist/{site_name}",
        },
        "Decks": _decks(data, rank_by_player),
        "Rounds": rounds,
        "Standings": standings,
    }
