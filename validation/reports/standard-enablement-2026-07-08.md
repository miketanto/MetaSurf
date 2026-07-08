# Standard format enablement — 2026-07-08

Enabling **Standard** as a second constructed format via the "formats are
config" design (plan §2/§4.1). Every number below is printed output of code
that ran this session (CLAUDE.md rule 5).

## What was done
1. **Config**: `config/formats.json` → `standard` `import: true` (was false).
2. **Rules**: ported `Formats/Standard/` from `github.com/Badaro/MTGOFormatData`
   (pinned commit `71af318018d51ea590b16775433ae92ce34a8000`, the same as
   Modern) → `archetypes/definitions/standard/` — **59 Archetypes, 8 Fallbacks,
   metas.json, color_overrides.json**, byte-identical to upstream. Provenance
   updated. The active `Standard/` set is current (the source repo keeps dated
   historical folders for past rotations).
3. **Loader**: one upstream data quirk — `standard/Archetypes/UWMomo.json` has
   condition type `"OneorMoreInMainboard"` (lowercase `or`). The ported data is
   kept pristine; `archetypes/classifier/definitions.py` now canonicalizes
   condition-type casing (pure case typos resolve; genuinely-unknown types
   still fail), matching the loader's existing policy of tolerating upstream
   quirks. Modern classifier tests unaffected (28 passed).

## Live-data classification health (the real check)
On a real current-Standard slice scraped from mtgo.com (16 events,
**287 decks**, 8,440 deck_cards):

| label method | decks | share |
|---|---|---|
| rules | 256 | 89.2% |
| fallback | 29 | 10.1% |
| **Rogue** | **2** | **0.7%** |

**Only 0.7% Rogue** — the ported rules classify current Standard, i.e. the
rules are current (a rotated-out ruleset would show a high Rogue rate). Top
archetypes are plausible current-set decks: Ouroboroid 64, Prowess 46,
Lessons 42, Jeskai Control 40, Excruciator 18, Landfall 15, Midrange 15,
Spellementals 13. 1 rule conflict, resolved PreferSimpler.

Rollups built and the **read API serves it with zero API code changes**
(format is a URL path variable): `GET /v1/mtg/standard/meta` → 200, 17
archetypes (Ouroboroid 0.23, Jeskai Control 0.16, Lessons 0.14, Prowess 0.14);
`/v1/mtg/standard/events` → 16 events.

## Unresolved cards (data freshness, not a bug)
9 distinct names / 73 occurrences unresolved, all **brand-new cards absent from
the on-disk Scryfall bulk snapshot** (Leyline Weaver ×34, Detect Intrusion ×13,
Kavaero Mind-Bitten ×17, Belion the Parched, Desecrex, The Scouring Stormsoul,
The Terminus of Return, Wrench Speedway Saboteur, Zora Spider Fancier). Logged
to `ingest_unresolved_cards`, never guessed. **Fix: refresh the Scryfall bulk**
(`data/scryfall/oracle-cards.jsonl`) — the on-disk snapshot predates the latest
Standard set.

## What is NOT yet done (honest scope)
- **Full V1 gate for Standard is not run.** V1.1 (clustering-recovery
  agreement) and V1.2 (emergence backtest) need (a) a **historical Standard
  corpus** (a holdout month with enough decks — a `MTGODecklistCache` clone;
  the live slice is ~1 week, too thin), and (b) **parameterizing
  `validation/v1_archetypes`** — `run_v11`/`run_v12` currently call
  `load_definitions(conn)` / `load_decks(...)` with no format arg, so they
  default to Modern. Both are follow-ups before Standard has a validated V1
  claim; this report is the live-data classification-health check, not the V1
  gate.
- Refresh Scryfall bulk to clear the 9 new-card unresolveds.

## Reproduce
```
# standard import:true in config/formats.json
python -m ingest.mtgo_scraper --cache-root <cache> --raw-root <raw>   # scrapes standard too
python -m archetypes.labeler --format standard --granularity parent
python -m jobs.rollups --game mtg --format standard
```
