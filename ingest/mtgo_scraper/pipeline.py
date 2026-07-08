"""Write parsed events into the cache layout the existing importer consumes.

The scraper never re-implements normalization: it lands each event as a
CacheItem JSON file under `Tournaments/<source>/<YYYY>/<MM>/<DD>/<slug>.json`
(the same layout the frozen MTGODecklistCache used), so
`ingest.cache_import.importer.run_import` and `ingest.match_extract` ingest
live events with zero changes. `events.raw_ref` points at this JSON; the
immutable raw HTML lives separately (see `fetch.py`).
"""

from __future__ import annotations

import re
from datetime import date
from pathlib import Path
from typing import Any

import orjson

SOURCE = "mtgo.com"
_RE_SLUG_DATE = re.compile(r"(\d{4})-(\d{2})-(\d{2})")


def slug_date(slug: str) -> date:
    """The YYYY-MM-DD embedded in an mtgo.com event slug."""
    m = _RE_SLUG_DATE.search(slug)
    if m is None:
        raise ValueError(f"no date in event slug {slug!r}")
    return date(int(m.group(1)), int(m.group(2)), int(m.group(3)))


def cacheitem_relpath(slug: str, source: str = SOURCE) -> str:
    """Cache-layout path (relative to the cache root) for an event slug.

    This is exactly the value stored in `events.raw_ref`, so `match_extract`
    resolves it against the same cache root.
    """
    d = slug_date(slug)
    return f"Tournaments/{source}/{d.year:04d}/{d.month:02d}/{d.day:02d}/{slug}.json"


def write_cacheitem(
    cache_root: Path, slug: str, item: dict[str, Any], source: str = SOURCE
) -> Path:
    """Write one CacheItem JSON file; returns its absolute path. Deterministic
    bytes (sorted keys) so re-deriving from raw HTML reproduces the file."""
    path = cache_root / cacheitem_relpath(slug, source)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(orjson.dumps(item, option=orjson.OPT_SORT_KEYS | orjson.OPT_INDENT_2))
    return path
