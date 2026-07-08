# tests/fixtures/topdeck.gg/

**Real captured responses** from the TopDeck Tournament Data API v2
(https://topdeck.gg/docs/tournaments-v2), captured 2026-07-08 via a
`POST /api/v2/tournaments` search (game "Magic: The Gathering", format Modern,
`last: 21`, full columns + `rounds: true`). Each file is one real tournament
object exactly as the API returned it (standings + rounds inline).

- `real-modern-with-decklists.json` — a real 15-player Modern event with 14
  submitted decklists and 4 swiss rounds; exercises decklist-text parsing
  (incl. the API's literal-`\n` / escaped-apostrophe quirk), rank-from-order,
  W-L-D records, and Player1-perspective round results.
- `real-no-decklists-edge.json` — a real small event where players submitted
  no lists; exercises the empty-decklist edge (decks with empty boards,
  record-based Result, no crash).

The parser was validated against these plus a live end-to-end import (8 real
tournaments -> 93 decks, 0 unresolved cards, 184 matches). Player names are
real (public TopDeck data; attribution required — see ingest/topdeck_scraper
ATTRIBUTION_HTML).
