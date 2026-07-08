"""TopDeck scrape run: search completed tournaments -> per-tournament fetch ->
CacheItem files the existing importer consumes. Best-effort; never blocks MTGO.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any

import orjson

from ingest.topdeck_scraper import SOURCE
from ingest.topdeck_scraper.client import TopdeckClient
from ingest.topdeck_scraper.parse import build_cacheitem

# TopDeck games/formats are their own vocabulary; the canonical format token is
# what the importer matches on, so we tag the filename with it.
_RE_DATE = re.compile(r"(\d{4})-(\d{2})-(\d{2})")


@dataclass
class TopdeckScrapeStats:
    tournaments_found: int = 0
    already_have: int = 0
    written: int = 0
    errors: int = 0
    error_tids: list[str] = field(default_factory=list)

    def summary(self) -> str:
        line = (
            f"tournaments found: {self.tournaments_found}, already have: "
            f"{self.already_have}, written: {self.written}, errors: {self.errors}"
        )
        if self.error_tids:
            line += f" ({', '.join(self.error_tids)})"
        return line


def _event_relpath(tid: str, format_slug: str, date: str | None) -> str:
    m = _RE_DATE.search(date or "")
    y, mo, d = (m.group(1), m.group(2), m.group(3)) if m else ("0000", "00", "00")
    return f"Tournaments/{SOURCE}/{y}/{mo}/{d}/{format_slug}-{tid}.json"


def _iso(date: str | None) -> str | None:
    if not date:
        return None
    try:
        return datetime.fromisoformat(date.replace("Z", "+00:00")).strftime("%Y-%m-%dT%H:%M:%SZ")
    except ValueError:
        return date


def run_scrape(
    client: TopdeckClient,
    cache_root: Path,
    *,
    game: str,
    fmt: str,
    format_slug: str,
    start: str | None = None,
    end: str | None = None,
) -> TopdeckScrapeStats:
    stats = TopdeckScrapeStats()
    tournaments = client.search(game, fmt, start=start, end=end)
    stats.tournaments_found = len(tournaments)
    for t in tournaments:
        tid = t.get("id") or t.get("TID")
        if not tid:
            continue
        date = t.get("startDate") or t.get("date") or t.get("start")
        rel = _event_relpath(tid, format_slug, date)
        if (cache_root / rel).exists():
            stats.already_have += 1
            continue
        try:
            info = {**t, "id": tid, "startDate": _iso(date)}
            standings = client.standings(tid)
            rounds = client.rounds(tid)
            item = build_cacheitem(info, standings, rounds)
        except Exception as exc:  # best-effort: one bad tournament never sinks the run
            stats.errors += 1
            stats.error_tids.append(f"{tid}:{type(exc).__name__}")
            continue
        path = cache_root / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(orjson.dumps(item, option=orjson.OPT_SORT_KEYS | orjson.OPT_INDENT_2))
        stats.written += 1
    return stats


def scrape_kwargs_from_config(game_name: str, format_name: str) -> dict[str, Any]:
    """Map our canonical game/format to TopDeck's query vocabulary + the
    filename format slug. TopDeck uses 'Magic: The Gathering' / 'Modern'."""
    game = "Magic: The Gathering" if game_name == "mtg" else game_name
    fmt = format_name.capitalize()
    return {"game": game, "fmt": fmt, "format_slug": format_name}
