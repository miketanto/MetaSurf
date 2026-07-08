"""Scrape run: listing -> new event pages -> archived raw HTML -> CacheItem
files, ready for the existing importer. Pure orchestration over the fetcher
and parser; the network lives entirely in the injected Fetcher.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

from ingest.formats_config import load_formats
from ingest.mtgo_scraper.fetch import Fetcher
from ingest.mtgo_scraper.parse import (
    MtgoParseError,
    event_to_cacheitem,
    extract_decklists_data,
    parse_listing_slugs,
)
from ingest.mtgo_scraper.pipeline import cacheitem_relpath, write_cacheitem
from ingest.normalize.cache_item import detect_format


@dataclass
class ScrapeStats:
    events_listed: int = 0
    events_targeted: int = 0
    already_have: int = 0
    fetched: int = 0
    unavailable: int = 0
    written: int = 0
    parse_errors: int = 0
    parse_error_slugs: list[str] = field(default_factory=list)

    def summary(self) -> str:
        return "\n".join(
            [
                f"events listed:       {self.events_listed}",
                f"targeted (formats):  {self.events_targeted}",
                f"  already have:      {self.already_have}",
                f"  fetched:           {self.fetched}",
                f"  unavailable (yet): {self.unavailable}",
                f"  written:           {self.written}",
                f"  parse errors:      {self.parse_errors}"
                + (f" ({', '.join(self.parse_error_slugs)})" if self.parse_error_slugs else ""),
            ]
        )


def _target_formats(game: str) -> tuple[dict[str, tuple[str, ...]], set[str]]:
    formats = [f for f in load_formats() if f.game == game]
    tokens = {f.name: f.slug_tokens for f in formats}
    enabled = {f.name for f in formats if f.do_import}
    return tokens, enabled


def run_scrape(
    fetcher: Fetcher,
    cache_root: Path,
    *,
    game: str = "mtg",
    listing_html: str | None = None,
) -> ScrapeStats:
    """Fetch new events for the import-enabled formats and land them as
    CacheItem files under `cache_root`. Idempotent: an event whose CacheItem
    already exists is left untouched (and its raw HTML is never re-fetched).
    A single event that fails to parse is logged and counted, never fatal —
    one bad page must not sink the nightly run.
    """
    stats = ScrapeStats()
    tokens_by_format, enabled = _target_formats(game)

    html = listing_html if listing_html is not None else fetcher.fetch_listing()
    slugs = parse_listing_slugs(html)
    stats.events_listed = len(slugs)

    for slug in slugs:
        fmt = detect_format(slug, tokens_by_format)
        if fmt is None or fmt not in enabled:
            continue
        stats.events_targeted += 1
        if (cache_root / cacheitem_relpath(slug)).exists():
            stats.already_have += 1
            continue
        body = fetcher.fetch_event(slug)
        if body is None:
            stats.unavailable += 1
            continue
        stats.fetched += 1
        try:
            data = extract_decklists_data(body.decode("utf-8", errors="replace"))
            if data is None:
                raise MtgoParseError("no decklists.data payload on event page")
            item = event_to_cacheitem(data)
        except MtgoParseError:
            stats.parse_errors += 1
            stats.parse_error_slugs.append(slug)
            continue
        write_cacheitem(cache_root, slug, item)
        stats.written += 1

    return stats
