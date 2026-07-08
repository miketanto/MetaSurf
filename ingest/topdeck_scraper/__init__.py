"""First-party TopDeck.gg source (plan §3: "data-friendly org").

TopDeck exposes a free, documented Tournament Data API
(https://topdeck.gg/docs/tournaments-v2): tournament search + per-tournament
standings, rounds (pairings + game/match results), and decklists. It drops
into the same CacheItem -> canonical pipeline as MTGO, behind the best-effort
seam (never blocks the MTGO pipeline).

Access: a free API key (Authorization header). Attribution is REQUIRED — any
surface using this data must show "Data provided by TopDeck.gg" with a link
(see ATTRIBUTION_HTML). Rate limit: 100 req/min on standard endpoints.

STATUS: built against the documented API schema (2026-07-08). Per CLAUDE.md
(inspect before you parse) the parser MUST be validated against 2-3 real
captured responses before it is trusted — the daily chain keeps this source
DISABLED until that validation lands and real fixtures replace the
documentation-derived ones under tests/fixtures/topdeck.gg/.
"""

from __future__ import annotations

SOURCE = "topdeck.gg"
ATTRIBUTION_HTML = (
    '<p>Data provided by '
    '<a href="https://topdeck.gg" target="_blank">TopDeck.gg</a></p>'
)
