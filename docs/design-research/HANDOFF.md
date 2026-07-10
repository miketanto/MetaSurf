# DESIGN HANDOFF — canonical Pit-Wall Console system (as of 2026-07-10)

**This is the entrypoint for implementing the MetaSurf frontend.** Everything referenced here is
in `docs/design-research/2026-07-09/` unless noted. Browse it all visually via
[`2026-07-09/index.html`](2026-07-09/index.html) (open in a browser).

## 1. Read these specs first, in order

| # | File | What it governs |
|---|---|---|
| 1 | [`2026-07-09/pit-wall-tokens.md`](2026-07-09/pit-wall-tokens.md) | Design tokens + component recipes (colors, type, DSEG numeral rules, press states, riso grain, misprint-veil premium gate, motion/reduced-motion) |
| 2 | [`2026-07-09/extension-spec.md`](2026-07-09/extension-spec.md) | Multi-game rules: pip/swatch grammar per game, archetype naming tiers (T1 curated / T2 structural / T3 unnamed-emerging), degradation/caveat chrome, attribution slot |
| 3 | [`2026-07-09/attention-art-spec.md`](2026-07-09/attention-art-spec.md) | Focal hierarchy: one hero zone per page, density budgets (measured), art-anchor tiers, per-page audit |

Non-negotiable rules baked into every mockup (keep them when wiring):
chart data-ink is crisp vector (retro flavor in framing only); DSEG numerals never get an "88"
ghost underlay; winrates always show n + CI; premium = depth-in-screen via the veil (fields
absent, not zeroed); unnamed clusters never styled like curated archetypes; unresolved card
names reported, never auto-corrected; visible TopDeck attribution where its data appears;
NO WotC/Bandai/Riot official glyphs; NO One Piece or Riftbound card images (ToS pending/banned).

## 2. Route → canonical mockup (the agreed set, all attention-spec compliant where marked ✦)

| Route / feature | Canonical mockup | Notes |
|---|---|---|
| `/` home + game switcher | `2026-07-09/home-game-switcher.html` ✦ | active-game hero, registry-driven theming |
| `/{game}/{format}` meta overview | `2026-07-09/pit-wall-console/s1-meta-snapshot.html` ✦ | hero art band, sort/filter console, rep-card art + color pips from `s1-archetype-visuals.json` |
| `/{game}/{format}/matchups` | `2026-07-09/pit-wall-console/s2-matchup-matrix.html` | MTG matrix; docked pair-report at wide |
| — One Piece variant | `2026-07-09/op-matchup-matrix.html` | 13×13 from real matches; share-only degradation toggle; **wire this first** (per wave-2 report §6) |
| `/{game}/{format}/archetypes/{id}` | `2026-07-09/pit-wall-console/s3-archetype-detail.html` | deck-focused: staples gallery, star-graded finishes, latest-decks feed |
| `/{game}/{format}/decks/{deck}` | `2026-07-09/pit-wall-console/s-deck-viewer.html` ✦(density) | prices, card inspector dock, Terminal-derived list layout |
| — visual mode | `2026-07-09/deck-visual.html` | POSTER / CONSOLE(default) / TEXT modes, sideboard PIT BOX |
| — One Piece variant | `2026-07-09/op-deck-viewer.html` ✦ | leader color-field hero, NO card images (ToS) |
| deck import (new) | `2026-07-09/deck-import.html` | intake console, FAULT LOG, scrutineering lamps |
| `POST /classify` widget | `2026-07-09/deck-classify.html` | honest ties + unresolved reporting |
| tournament report / local logger (new) | `2026-07-09/tournament-report.html` | lap cards, UNKNOWN first-class, local-vs-global panel, CSV export |
| `/events` | `2026-07-09/events-browser.html` ✦ | featured-event hero, star plaques |
| `/best-decks` | `2026-07-09/best-decks.html` | winners ledger |
| `/trends` + tech-watch | `2026-07-09/card-trends.html` ✦ | top-mover art hero, premium veil |
| `/emerging` (premium flagship) | `2026-07-09/emerging-feed.html` ✦ | locked/unlocked states; zero value leaks in locked markup |
| deck map (roadmap) | `2026-07-09/deck-map.html` | synthetic geometry labeled; needs real HDBSCAN layout |
| meta forecast (roadmap) | `2026-07-09/meta-forecast.html` | FC mode + descriptive fallback, one layout |

✦ = revised to the attention-art-spec budgets (hero + measured density). The nine unmarked
pages have prescribed fixes in attention-art-spec §3 (audit) — apply during implementation.

## 3. Grounding data files (real, mined — reuse rather than re-mining)

`2026-07-09/deck-viewer-data.json` (74-card Izzet Wizards, Scryfall images+prices),
`archetype-page-data.json` (717-deck Murktide sample: staples/finishes/avg price),
`s1-archetype-visuals.json` (26 archetypes: rep-card art + pip-mined colors),
`onepiece-ground.json`, `riftbound-games-ground.json` (registry values, OP events/decks/matrix,
Riftbound catalogue). Research: `research-deck-import-visual.md`, `research-tournament-report.md`.

## 4. Superseded — do NOT implement from these

- `2026-07-08/` (wave-1: three exploratory directions; Overprint Bulletin dropped, useful only as riso-technique reference)
- `2026-07-09/grinder-terminal/` (direction folded into Pit-Wall; its deck-list layout already ported into `s-deck-viewer.html`)

## 5. Open owner decisions (flagged in-page and in `2026-07-09/README.md`)

Free-teaser row count (1 vs 3); 849-vs-889 OP match recount; One Piece card-image hosting/ToS;
Riftbound legend-index + catalogue pages (unbuilt; grounding ready); MTGOFormatData rule-file
port (rep cards/hull names marked "PORT PENDING"); token-spec row-grammar amendment
(rows use quiet bold mono, DSEG reserved for hero/tile readouts — two agents converged on this).

Full context: [`2026-07-09/README.md`](2026-07-09/README.md) (wave-2 report) and
[`2026-07-08/README.md`](2026-07-08/README.md) (direction choice rationale).
