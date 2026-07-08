"""First-party TopDeck.gg source (plan §3: "data-friendly org").

TopDeck exposes a free, documented Tournament Data API
(https://topdeck.gg/docs/tournaments-v2): tournament search + per-tournament
standings, rounds (pairings + game/match results), and decklists. It drops
into the same CacheItem -> canonical pipeline as MTGO, behind the best-effort
seam (never blocks the MTGO pipeline).

Access: a free API key (Authorization header). Attribution is REQUIRED — any
surface using this data must show "Data provided by TopDeck.gg" with a link
(see ATTRIBUTION_HTML). Rate limit: 100 req/min on standard endpoints.

STATUS: VALIDATED against real captured responses (2026-07-08). Real fixtures
live under tests/fixtures/topdeck.gg/; on the live corpus an 8-tournament
Modern search imported to 93 decks with 0 unresolved cards and 184 extracted
matches (full swiss pairings — more match signal per event than MTGO's Top-8
brackets). The daily chain still keeps the source behind an explicit opt-in
(TOPDECK_API_KEY + METASURF_TOPDECK_ENABLED) as a best-effort source that
never blocks MTGO.
"""

from __future__ import annotations

SOURCE = "topdeck.gg"
ATTRIBUTION_HTML = (
    '<p>Data provided by '
    '<a href="https://topdeck.gg" target="_blank">TopDeck.gg</a></p>'
)
