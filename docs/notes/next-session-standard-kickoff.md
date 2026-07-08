# Kickoff prompt — next session: additional constructed formats (Standard)

Paste the block below into a new session. It mirrors the M4 kickoff. Chosen
next milestone: **enable Standard** (plan §2/§4.1 "formats are config"), the
pattern then generalizes to Pioneer/Legacy/Pauper/Vintage. Full context:
[`m4-live-ingestion-handoff.md`](m4-live-ingestion-handoff.md).

---

Start the next milestone — **Additional constructed formats: Standard**
(plan §2 backlog "additional formats = config, not code"; §4.1 portability) for
the Metagame Platform.

REPO SETUP:
- Continue on THIS machine from the local branch `m4-live-ingestion` (the prior
  session's work: M4 live ingestion + TopDeck source + variant/color archetype
  granularity + deck map — **not yet pushed to a remote**). From a fresh clone,
  push that branch first.
```
cd MetaSurf
git checkout m4-live-ingestion
git checkout -b formats-standard
make setup                     # Python 3.11 — bare `python` is pyenv 3.9 w/o deps; use python3
export DATABASE_URL=postgresql://metagame:metagame@localhost:5432/metagame
# Scryfall cards must be ingested (format-agnostic; already done if the DB is warm):
#   python -m ingest.scryfall --file data/scryfall/oracle-cards.jsonl
# Optional: MTGODecklistCache clone for Standard historical backfill (README).
```
- Verify green before writing code: `make lint typecheck checks test` (180 tests).

CONTEXT / REQUIRED READING (in order):
1. CLAUDE.md — binding. Especially rule 4: archetype definitions come from the
   ported rule files, NOT authored from your own knowledge of the metagame;
   flag gaps for the owner.
2. metagame-app-start-plan.md §2 ("additional formats = config"), §4.1
   (formats are rows + config; game/format neutrality).
3. docs/notes/m4-live-ingestion-handoff.md — full current state + why Standard
   is the recommended next milestone.
4. archetypes/definitions/PROVENANCE.md — exactly how the Modern rules were
   ported from `github.com/Badaro/MTGOFormatData` (`Formats/Modern/`). Do
   Standard the identical way (`Formats/Standard/`).
5. docs/notes/mtgoformatdata-observed-schema.md — rule-file structure +
   condition semantics.
6. docs/research-log.md §6 — the backlog decision (Standard = near-term config;
   MTG Arena = a separate, licensing-gated SOURCE, BL-5, do NOT start).

STARTING STATE:
- config/formats.json: modern import=true; standard/pioneer/legacy/pauper/
  vintage import=false.
- archetypes/definitions/ has only `modern/` (130 rule files). Other formats
  have NO rules → their decks all fall to Rogue/fallback.
- The live mtgo.com scraper already SEES Standard (~15 events/day in the
  listing); the daily chain just filters to import-enabled formats. The TopDeck
  adapter takes format as a param.
- labeler / rollups / daily-chain all take `--format` already; the cards table
  is format-agnostic (resolution works for any format).

SCOPE (Standard first; the steps generalize to the other formats):
1. Enable the source: set `standard` `import: true` in config/formats.json;
   verify its slug_tokens / board_zones / deck-size expectations.
2. Port Standard archetype rules UNMODIFIED from Badaro/MTGOFormatData
   `Formats/Standard/` → `archetypes/definitions/standard/` (Archetypes,
   Fallbacks, metas.json, color_overrides.json). Update PROVENANCE.md with the
   Standard entry + the pinned commit.
3. Ingest a real slice: scrape live Standard events (mtgo + TopDeck) and/or
   historical backfill from the cache clone; label (parent granularity first,
   then variant/color).
4. Validate FOR STANDARD: run V1-style archetype validation (per-archetype
   precision/recall/F1 vs a hand-spot-checked holdout; V1.1 target ≥95%
   agreement, no major archetype <90% F1). Write a dated report to
   validation/reports/ and commit it. NB: check whether
   `validation/v1_archetypes` is Modern-hardcoded — parameterize it by format
   if so (do NOT hand-tune to pass).
5. Serve: rollups already key on format_id — verify `/v1/mtg/standard/…` works.

HARD RULES:
- Archetype definitions are DATA ported from MTGOFormatData — NEVER authored
  from your own knowledge of current Standard (CLAUDE.md rule 4). MTGOFormatData
  is unmaintained and Standard ROTATES, so the ported rules may lag the current
  card pool: FLAG stale/missing archetypes to the owner and validate against
  real current Standard decks — do not invent archetypes to fill holes.
- Inspect before you parse: confirm a couple of real current Standard event
  pages match the CacheItem path already used for Modern (save fixtures if any
  new parsing is needed).
- If a V1 target is missed, do NOT lower it, tweak the test, or cherry-pick the
  window — write the failure analysis and stop for owner review.
- Migrations additive-only. Keep the game-neutrality gate green (models/jobs/api
  stay format-agnostic; format arrives as a row/param, never a literal).
- No fabricated numbers: every metric in a report or commit message is printed
  output of code that ran this session.
- Card resolution goes through the existing cards table; unresolved names are
  logged, never guessed.

SUGGESTED ORDER: (1) read + verify green; (2) port Standard rule files +
PROVENANCE; (3) enable config + ingest a real Standard slice; (4) label +
hand-spot-check; (5) V1 validation for Standard + dated committed report;
(6) rollups/API check; (7) if time, repeat the pattern for the next format.

DO NOT start: MTG Arena (BL-5, licensing-gated source), the emerging-deck feed,
or M6 insight features — one milestone at a time.

---
