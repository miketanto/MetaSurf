"""Pure parsers: TopDeck Tournament Data API responses -> CacheItem dict.

Written against REAL captured v2 responses (fixtures under
tests/fixtures/topdeck.gg/, captured 2026-07-08), not just the docs — the live
API differs from https://topdeck.gg/docs/tournaments-v2 in ways that matter:

- A `POST /v2/tournaments` search returns tournament objects with `standings`
  and `rounds` INLINE (one call). Event name is `tournamentName`; the date is
  a unix-seconds `startDate`; the id is `TID`.
- standings entries: {"name", "decklist", "deckObj", "wins", "draws",
  "losses", "winRate"} — there is NO "standing" field; rank is the row order,
  and the record comes from wins/draws/losses.
- decklist text is DOUBLE-ESCAPED: line breaks are the literal two chars
  '\\n' and quotes arrive as "\\'" / '\\"'. `parse_decklist` normalizes these.
- rounds/tables: {"round", "tables":[{"players":[{name,id}], "winner",
  "winner_id", "winner_games", "loser_games", "status"}]}.

Output matches the MTGODecklistCache CacheItem shape so the existing
normalize/import/match-extract paths ingest TopDeck events unchanged (the
importer already handles topdeck.gg's quirks — see
docs/notes/mtgodecklistcache-observed-schema.md). No network, no DB here.
"""

from __future__ import annotations

import re
from datetime import UTC, datetime
from typing import Any

BASE_URL = "https://topdeck.gg"
_RE_SECTION = re.compile(r"^~~(.+?)~~$")
_RE_CARDLINE = re.compile(r"^(\d+)\s+(.+?)\s*$")


class TopdeckParseError(ValueError):
    """A response did not match the documented structure. Fail loudly."""


def parse_decklist(text: str | None) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """Decklist text -> (mainboard, sideboard) as [{CardName, Count}].

    Sideboard lines go to the sideboard; every other section (Mainboard,
    Commanders, Companion) folds into the mainboard. Card names resolve later
    through the cards table — never guessed here."""
    main: list[dict[str, Any]] = []
    side: list[dict[str, Any]] = []
    zone: str | None = None
    # Real API quirk (verified 2026-07-08): the decklist string is double-
    # escaped — line breaks are the literal two chars '\n' and quotes come as
    # "\'" / '\"'. Normalize before splitting. (Real newlines, if a source ever
    # sends them, pass through splitlines unchanged.)
    normalized = (
        (text or "")
        .replace("\\r\\n", "\n")
        .replace("\\n", "\n")
        .replace("\\r", "\n")
        .replace("\\'", "'")
        .replace('\\"', '"')
    )
    for raw in normalized.splitlines():
        line = raw.strip()
        if not line:
            continue
        sec = _RE_SECTION.match(line)
        if sec:
            zone = "side" if "side" in sec.group(1).lower() else "main"
            continue
        card = _RE_CARDLINE.match(line)
        if card and zone is not None:
            entry = {"CardName": card.group(2), "Count": int(card.group(1))}
            (side if zone == "side" else main).append(entry)
    return main, side


def _ordinal_place(rank: int) -> str:
    suffix = "th"
    if not 10 <= rank % 100 <= 20:
        suffix = {1: "st", 2: "nd", 3: "rd"}.get(rank % 10, "th")
    return f"{rank}{suffix} Place"


def _record(s: dict[str, Any]) -> str:
    """A standing's swiss record 'W-L-D' (real TopDeck standings carry wins/
    draws/losses). Empty string when the record isn't present."""
    w, losses, d = s.get("wins"), s.get("losses"), s.get("draws")
    if w is None or losses is None:
        return ""
    return f"{int(w)}-{int(losses)}-{int(d)}" if d is not None else f"{int(w)}-{int(losses)}"


def _decks(standings: list[dict[str, Any]]) -> list[dict[str, Any]]:
    # Real standings are ordered by finish and carry no explicit 'standing'
    # field, so rank = row order; the record comes from wins/draws/losses.
    decks: list[dict[str, Any]] = []
    for i, s in enumerate(standings):
        main, side = parse_decklist(s.get("decklist"))
        result = _record(s) or _ordinal_place(i + 1)
        decks.append(
            {
                "Player": s.get("name"),
                "AnchorUri": None,
                "Result": result,
                "Mainboard": main,
                "Sideboard": side,
            }
        )
    return decks


def _standings(standings: list[dict[str, Any]]) -> list[dict[str, Any]] | None:
    if not standings:
        return None
    out: list[dict[str, Any]] = []
    for i, s in enumerate(standings):
        row: dict[str, Any] = {"Rank": i + 1, "Player": s.get("name")}
        for src, dst in (("wins", "Wins"), ("losses", "Losses"), ("draws", "Draws")):
            if s.get(src) is not None:
                row[dst] = int(s[src])
        if s.get("points") is not None:
            row["Points"] = int(s["points"])
        for src, dst in (("winRate", "GWP"), ("opponentWinRate", "OGWP")):
            if s.get(src) is not None:
                row[dst] = s[src]
        out.append(row)
    return out


def _match_result(table: dict[str, Any], p1: dict[str, Any], p2: dict[str, Any]) -> str:
    """Result string from Player1's perspective (W-L-D). TopDeck 1v1 Pairs
    give winner_games/loser_games; other formats give a match-level winner.
    A table with no winner (drawn / unreported completed) reads as a draw."""
    wg, lg = table.get("winner_games"), table.get("loser_games")
    winner_id, winner = table.get("winner_id"), table.get("winner")
    p1_won = (winner_id is not None and winner_id == p1.get("id")) or (
        winner is not None and winner == p1.get("name")
    )
    p2_won = (winner_id is not None and winner_id == p2.get("id")) or (
        winner is not None and winner == p2.get("name")
    )
    if wg is not None and lg is not None:  # game counts (1v1 Pairs)
        return f"{wg}-{lg}-0" if p1_won else (f"{lg}-{wg}-0" if p2_won else f"{wg}-{lg}-0")
    # match-level (topdeck convention: 1-0-0 / 0-1-0 / 0-0-1 draw)
    if p1_won:
        return "1-0-0"
    if p2_won:
        return "0-1-0"
    return "0-0-1"


def _rounds(rounds: list[dict[str, Any]]) -> list[dict[str, Any]] | None:
    if not rounds:
        return None
    out: list[dict[str, Any]] = []
    for rnd in sorted(rounds, key=lambda r: r.get("round", 0)):
        matches: list[dict[str, Any]] = []
        for table in rnd.get("tables") or []:
            players = table.get("players") or []
            if not players:
                continue
            p1 = players[0]
            p2 = players[1] if len(players) > 1 else {}
            matches.append(
                {
                    "Player1": p1.get("name"),
                    "Player2": p2.get("name") if p2 else None,
                    "Result": _match_result(table, p1, p2),
                }
            )
        out.append({"RoundName": str(rnd.get("round", "")), "Matches": matches})
    return out


def to_iso_date(value: Any) -> str | None:
    """TopDeck startDate is a unix timestamp (seconds); accept that, an ISO
    string, or None. Returns ISO-8601 'YYYY-MM-DDTHH:MM:SSZ'."""
    if value is None:
        return None
    if isinstance(value, (int, float)) or (isinstance(value, str) and value.isdigit()):
        dt = datetime.fromtimestamp(int(value), tz=UTC)
        return dt.strftime("%Y-%m-%dT%H:%M:%SZ")
    try:
        return datetime.fromisoformat(str(value).replace("Z", "+00:00")).strftime(
            "%Y-%m-%dT%H:%M:%SZ"
        )
    except ValueError:
        return None


def build_cacheitem(
    info: dict[str, Any],
    standings: list[dict[str, Any]],
    rounds: list[dict[str, Any]],
) -> dict[str, Any]:
    """Assemble a CacheItem from a tournament's info + standings + rounds.

    ``info`` carries at least an id (TID); the real API names the event
    ``tournamentName`` and dates it with a unix ``startDate``.
    """
    tid = info.get("TID") or info.get("id")
    if not tid:
        raise TopdeckParseError("tournament has no TID/id")
    date = info.get("startDate") or info.get("date") or info.get("start")
    return {
        "Tournament": {
            "Date": to_iso_date(date),
            "Name": info.get("tournamentName") or info.get("name"),
            "Uri": f"{BASE_URL}/event/{tid}",
        },
        "Decks": _decks(standings or []),
        "Rounds": _rounds(rounds or []),
        "Standings": _standings(standings or []),
    }
