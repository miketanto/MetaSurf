# M4 — Live ingestion: handoff

Pick-up doc for whoever continues after **M4 (plan §7)**. Written 2026-07-08 at
the end of the M4 build session. Branch: `m4-live-ingestion` (off
`claude/m5-read-api-handoff-etj6gx`), ~13 commits, **local-only / unpushed**.
All gates green: **180 tests, ruff, mypy, game-neutrality, determinism.**

## 0. TL;DR — state
- **M4 is BUILT and running-capable.** Own mtgo.com scraper → raw archive →
  normalize → nightly classify/label/rollup chain → failure alerting →
  monitoring. Validated end-to-end on real live data.
- **M4's formal DoD (14 consecutive unattended days) is intentionally
  DEFERRED** (owner decision, 2026-07-08: "14 days is very conservative; if
  it's working it's OK to build other things"). The machinery is done and a
  scheduler can start the soak any time; the clock just isn't the blocker.
- Beyond strict M4, this session also added a **first-party TopDeck.gg source**,
  **color/variant archetype granularity**, a **deck-map visualization**, and
  **source attribution**. See §3.

## 1. What M4 delivered (all validated on real data)
- `ingest/mtgo_scraper/` — polite fetcher (custom UA, ≤1 req/s, backoff,
  immutable raw HTML archive, never re-fetch), parser (live page →
  CacheItem, TDD on real fixtures under `tests/fixtures/mtgo.com/`), incremental
  import (dedupe on `(source, source_event_id)`), daily chain (`daily.py`:
  scrape → import → match_extract → label → rollups) with failure alerting,
  and a soak monitor (`soak.py`, DoD verdict N/14).
- Reuse-not-rebuild: emits the same **CacheItem** shape the frozen
  MTGODecklistCache used, so `ingest.normalize` / `cache_import` /
  `match_extract` ingest live events unchanged.
- Two evidence-driven fixes the frozen corpus never exercised: future-date DQ
  tolerance (next-day league instances across the UTC↔US boundary) and the
  live `A/B` split-card resolver mapping.
- Deploy: `deploy/` (systemd + launchd + cron units, env example) and the ops
  runbook `docs/notes/m4-live-ingestion-runbook.md`.
- Current-site schema note: `docs/notes/mtgo-com-observed-schema.md`.

## 2. Sources
| Source | Status |
|---|---|
| **mtgo.com** | ✅ live, validated, primary. Owner OK'd polite public fetch (ToS check on record; `[[mtgo-scraper-tos-decision]]`). |
| **TopDeck.gg** | ✅ adapter built + **validated on real API responses** (8-tournament Modern search → 93 decks, 0 unresolved, **184 matches** — full swiss pairings, more match signal than MTGO's Top-8 brackets). Best-effort, opt-in (`TOPDECK_API_KEY` + `METASURF_TOPDECK_ENABLED`). Attribution REQUIRED (wired: `config/sources.json`, deck-map footer, `/events` `credits`). |
| **Melee.gg** | ⏳ partnership-gated. No public feed; bot-hostile. Email draft ready: `docs/notes/melee-api-access-email.md`. |
| mtgdecks.net / mtgtop8 | ❌ skip on principle (aggregators; mtgdecks blocks us by robots.txt). |

## 3. New this session beyond M4 (context for the next builder)
- **Archetype granularity** (`archetypes/labeler`, `--granularity`): `parent`
  (V1 identity, default) or `variant` (the classifier's full display label —
  rule variant + color group where a def opts in via `IncludeColorInName`).
  The live product runs `variant`: e.g. Eldrazi → Broodscale / Ramp Eldrazi;
  Energy → Boros/Jeskai/Mardu Energy; Blink → Esper/Azorius/Jeskai Blink.
  Splits link to their base archetype via `archetypes.parent_id`.
- **Deck map** (`validation/deck_map.py`): 2D card2vec + t-SNE scatter of every
  labeled deck, colored by archetype; `--html` emits a standalone page
  (click a dot → full decklist) with the required source-attribution footer.
- **Attribution** (`api/attribution.py`, `config/sources.json`): config-driven,
  game-neutral `credits` on `GET /events` + the deck-map footer.

## 4. Owner / operational actions outstanding
1. **Start the soak whenever** — install a scheduler (`deploy/com.metasurf.daily.plist`
   for this Mac) + wire `METASURF_ALERT_CMD` to a real channel. Track with
   `python -m ingest.mtgo_scraper.soak`. (Deferred, not blocking.)
2. **Push the branch / open a PR** — 13 commits are local-only.
3. **TopDeck**: the key pasted in chat is exposed — **rotate it**, then set the
   two env vars to enable it in the daily chain.
4. **Melee**: send the drafted access email.

## 5. Validation debt (be honest before marketing)
- **Variant/color granularity is not validated.** V1's 0.9949 was measured at
  *parent* granularity; the product now runs finer. A variant/color-level
  validation pass (per-label precision/recall on a labeled holdout) is owed
  before per-variant or per-color winrates are a *validated* claim. The library
  default stays `parent` to keep V1 honest.

## 6. Recommended next milestone (owner to choose)
Per plan "one milestone at a time", the strong candidates:

- **(A) Additional constructed formats — RECOMMENDED, well-scoped.** The source
  data already flows (live mtgo.com carries Standard 15 / Pioneer 14 / Pauper
  13 / Legacy 13 / Vintage 10 events per day; TopDeck/Melee carry paper). Per
  format: (1) flip `import: true` in `config/formats.json` (trivial — "config
  not code"), (2) **port that format's archetype rule files** from
  MTGOFormatData (the real work; only `archetypes/definitions/modern/` exists
  today — without rules a format's decks fall to Rogue/fallback), (3) run
  V1-style validation for that format. Start with **Standard** (most live
  events). This is the plan §2 backlog "additional formats = config" cashing in.
- **(B) Emerging-deck feed (`/emerging`, plan S5).** The detect → characterize
  → human-name → promote-to-rule loop (design in this session's transcript).
  The clustering stage (`archetypes/classifier/clustering.py`) is already
  V1.2-validated (detects a new cluster within 7 days); the work is
  productizing it behind a game-neutral seam (like the `classify` Protocol),
  characterizing each cluster (signature cards, color, size, growth, winrate),
  and a `rollup_emerging` table + endpoint. **Auto-naming is out** (CLAUDE.md
  rule 4 — humans name; the system proposes a provisional descriptor). Sharpens
  as the corpus grows.
- **(C) M6 insight features** (research-log §4, BL-1/BL-2) — tech-watch /
  hidden-tech finder; gated on more live data.

Backlog decision recorded this session (research-log §6): **MTG Arena is a
backlog *source* (BL-5), gated on untapped.gg/17Lands licensing** — distinct
from "Standard the format," which is near-term config work above.

## 7. Run everything
```
make lint typecheck checks test          # gates (needs Python 3.11 — see [[python-interpreter-gotcha]])
python -m ingest.mtgo_scraper.daily      # full nightly chain
python -m ingest.mtgo_scraper.soak       # DoD verdict
python -m validation.deck_map --html deck-map.html   # deck visualization
uvicorn serve:app                        # read API
```
