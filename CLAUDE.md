# CLAUDE.md — Metagame Platform

Read `metagame-app-start-plan.md` before doing anything. It is the source of truth for scope, schema, model specs, acceptance criteria, and milestones. Work on exactly one milestone at a time; the current milestone is stated in the task prompt. Do not start work belonging to a later milestone.

## Ground-truth rules (anti-hallucination)

1. **Never invent domain facts.** Card names, archetype names, format legality, event structures, URLs, and site HTML structures must come from real data: the Scryfall bulk files on disk, the cloned MTGODecklistCache, or a page you actually fetched. If you haven’t seen it in real data, you don’t know it.
1. **Inspect before you parse.** Before writing or modifying any scraper/parser, download 2–3 real examples of the target page/file, save them under `tests/fixtures/<source>/`, and write the parser against those saved fixtures. Never write a parser from memory of what a site “probably” looks like.
1. **Card identity is data, not knowledge.** All card references resolve through the `cards` table (Scryfall oracle_id for MTG). If a card name from a decklist fails to resolve, log it to an unresolved-cards report — never “fix” the spelling from memory, never guess an oracle_id.
1. **Archetype definitions come from the rule files**, ported from MTGOFormatData. Do not author new archetype definitions from your own knowledge of the metagame; flag gaps for the owner instead.
1. **No fabricated numbers, ever.** Every metric in a validation report, commit message, or summary must be the printed output of code that actually ran in this session. If you didn’t run it, write “not yet measured.” Reporting a number you didn’t compute is the single worst failure mode in this project.
1. **Quote your evidence.** When you claim something about the data (“Challenges before 2024-06 include full standings”), cite the specific files you inspected. When uncertain about an external fact (a site’s ToS, an API’s existence), say so and ask — do not proceed on a guess.
1. **Library APIs:** if unsure of a function signature or behavior (HDBSCAN params, alembic ops, FastAPI details), check the installed package (`python -c "help(...)"`, read the source in site-packages) instead of guessing from memory.

## Testing discipline

1. **TDD for parsers and models:** fixture → failing test → implementation. Every scraper/normalizer has tests against real saved fixtures, including at least one malformed/edge-case fixture (missing standings, 0-card deck, unknown card, duplicated event).
1. **Never mock the unit under test.** Mock only true externals (network, clock). Parsers are tested on real fixture bytes; models are tested on real historical slices, not synthetic toy data — synthetic data is allowed only for property tests in addition to, never instead of, real-data tests.
1. **Determinism is a test:** all model code takes explicit seeds; the validation suites must produce byte-identical metrics across two consecutive runs, and CI asserts this.
1. **Validation ≠ unit tests.** Unit tests (fast, `tests/`) run on every change. Validation suites (`validation/v1..v3`) are the milestone gates: run them fully, write the dated report to `validation/reports/`, and commit it. A milestone is not done until its report exists and meets the acceptance criteria in plan §5 / DoD in §7.
1. **If a target is missed, do not lower it, tweak the test, or cherry-pick the evaluation window.** Write the failure analysis into the report and stop for owner review.
1. **Data-quality checks are tests too:** after any ingestion run, assert row-count sanity, referential integrity, no-future-dates, and deck-size distributions per format config; fail loudly on anomalies instead of ingesting garbage.
1. **CI gates (set up in M0):** pytest, ruff, mypy on `models/ jobs/ api/`, the determinism check, and the game-neutrality import check (nothing in `models/`, `jobs/`, `api/` may import MTG-specific modules or literals — see plan §4.1).

## Engineering rules

- Migrations: alembic, additive-only (plan §4.3). Any rename/drop needs a written expand–migrate–contract plan first.
- Scrapers: custom UA identifying the project, ≤1 req/sec/host, exponential backoff, cache everything, never re-fetch an archived event. Raw responses go to the raw archive before any parsing.
- All premium gating through the entitlements module; no inline tier checks.
- Config over code: formats, board zones, staple lists, and exclusions live in `formats.config`/rule files.
- Small commits, one logical change each; commit messages state what was verified (“parser passes 14 fixtures incl. 3 edge cases”), not aspirations.

## When to stop and ask the owner

Stop and ask rather than guess when: a data source’s structure differs from the plan’s assumptions; an acceptance target fails; a ToS/licensing question arises; an archetype definition seems missing or wrong; or completing the task would require modifying a live rollup table’s schema or semantics.