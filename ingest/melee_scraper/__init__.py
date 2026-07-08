"""Melee.gg scraper — BEST-EFFORT only (plan §10 risk 2).

Melee broke third-party scrapers in March 2025 and its public access is
unstable; the platform treats Melee ingestion as best-effort until a data
partnership exists, and **its failure must never block the MTGO pipeline**
(the daily runner runs this step non-required and swallows its failures).

No parser is implemented here yet: writing one would require real saved Melee
fixtures (CLAUDE.md: never write a parser from memory of what a site probably
looks like), which this milestone did not capture. The seam is in place so a
future adapter is *added* (fetch real pages -> fixtures -> parser ->
CacheItem under Tournaments/melee.gg/…, reusing the same importer) without
touching the MTGO path.

`enabled()` is env-gated (`METASURF_MELEE_ENABLED`), default off, so the
nightly run does not emit a best-effort warning every night for an adapter
that is deliberately not built. Flip it on only once a real adapter lands.
"""

from __future__ import annotations

import os
from pathlib import Path


class MeleeUnavailable(RuntimeError):
    """Melee ingestion could not run (no adapter yet, or the site refused)."""


def enabled() -> bool:
    return os.environ.get("METASURF_MELEE_ENABLED", "").lower() in {"1", "true", "yes", "on"}


def run_scrape(cache_root: Path) -> str:
    """Best-effort Melee scrape. Raises MeleeUnavailable when it cannot run;
    the daily runner treats that as a non-fatal warning."""
    raise MeleeUnavailable(
        "no Melee adapter yet — needs real captured fixtures before a parser "
        "may be written (CLAUDE.md). Best-effort step: MTGO ingestion is "
        "unaffected."
    )
