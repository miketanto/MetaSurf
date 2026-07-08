"""Pure parsers: TopDeck Tournament Data API responses -> CacheItem dict.

Written against the documented v2 schema (https://topdeck.gg/docs/tournaments-v2,
captured 2026-07-08) — see the module docstring in __init__ for the
inspect-before-you-parse caveat. No network, no DB.

Documented shapes used:
- standings: [{"standing": int, "name": str, "id": str, "decklist": str,
   "points": int, "winRate": float, "opponentWinRate": float}]
- rounds: [{"round": int, "tables": [{"table": int,
   "players": [{"name": str, "id": str}, ...], "winner": str|None,
   "winner_id": str|None, "winner_games": int?, "loser_games": int?,
   "status": str}]}]
- decklist text: sections "~~Mainboard~~" / "~~Sideboard~~" / "~~Commanders~~",
   each followed by "<qty> <card name>" lines.

Output matches the MTGODecklistCache CacheItem shape so the existing
normalize/import/match-extract paths ingest TopDeck events unchanged. The
existing code already handles topdeck.gg's documented quirks (numeric round
names, match-level results, byes) — see docs/notes/mtgodecklistcache-observed-schema.md.
"""

from __future__ import annotations

import re
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
    for raw in (text or "").splitlines():
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


def _decks(standings: list[dict[str, Any]]) -> list[dict[str, Any]]:
    decks: list[dict[str, Any]] = []
    for s in standings:
        name = s.get("name")
        main, side = parse_decklist(s.get("decklist"))
        rank = s.get("standing")
        decks.append(
            {
                "Player": name,
                "AnchorUri": None,
                "Result": _ordinal_place(int(rank)) if rank is not None else "",
                "Mainboard": main,
                "Sideboard": side,
            }
        )
    return decks


def _standings(standings: list[dict[str, Any]]) -> list[dict[str, Any]] | None:
    if not standings:
        return None
    out: list[dict[str, Any]] = []
    for s in standings:
        rank = s.get("standing")
        if rank is None:
            continue
        row: dict[str, Any] = {"Rank": int(rank), "Player": s.get("name")}
        if s.get("points") is not None:
            row["Points"] = int(s["points"])
        for src, dst in (("winRate", "GWP"), ("opponentWinRate", "OGWP")):
            if s.get(src) is not None:
                row[dst] = s[src]
        out.append(row)
    out.sort(key=lambda r: r["Rank"])
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


def build_cacheitem(
    info: dict[str, Any],
    standings: list[dict[str, Any]],
    rounds: list[dict[str, Any]],
) -> dict[str, Any]:
    """Assemble a CacheItem from a tournament's info + standings + rounds.

    ``info`` carries at least an id (TID); name/date are used when present.
    """
    tid = info.get("id") or info.get("TID")
    if not tid:
        raise TopdeckParseError("tournament info has no id/TID")
    date = info.get("startDate") or info.get("date") or info.get("start")
    return {
        "Tournament": {
            "Date": date,
            "Name": info.get("name"),
            "Uri": f"{BASE_URL}/event/{tid}",
        },
        "Decks": _decks(standings or []),
        "Rounds": _rounds(rounds or []),
        "Standings": _standings(standings or []),
    }
