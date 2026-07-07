# Metagame Platform

Constructed TCG metagame research platform. **Read
[`metagame-app-start-plan.md`](metagame-app-start-plan.md) first** — it is the
source of truth for scope, schema, model specs, acceptance criteria, and
milestones. Engineering ground rules live in [`CLAUDE.md`](CLAUDE.md).

Current milestone: **M2 — Layer 2 validated** (batch archetype labeling,
match extraction from pairing-capable sources, hierarchical Bayesian winrate
model; V2 report in `validation/reports/m2-v2-winrates.md`).

## Layout

```
config/formats.json    formats are config, not code (slug tokens, board zones, size expectations)
db/migrations/         alembic migrations (additive-only)
ingest/cache_import/   one-shot importer for the frozen MTGODecklistCache clone
ingest/normalize/      source JSON -> canonical schema (pure functions) + card resolver
ingest/scryfall/       Scryfall bulk data -> game-neutral cards table
ingest/match_extract/  (M2) Rounds in cached files -> matches table
archetypes/            (M1) rule files + classifier; (M2) batch labeler
models/winrate/        (M2) hierarchical beta-binomial winrate + matchup model
models/  jobs/  api/   game-neutral by CI-enforced check
validation/m0_corpus/  M0 data-quality report generator
validation/v1_archetypes/  V1 suites (M1)
validation/v2_winrates/    V2 suites + tuner (M2)
validation/reports/    dated, committed validation reports (source of truth for go/no-go)
tests/fixtures/        real saved source files; all parser tests run against these
docs/notes/            observed-schema notes (what the data actually looks like)
```

## Setup

```bash
make setup                          # pip install -e ".[dev]"
sudo -u postgres psql -c "CREATE ROLE metagame LOGIN PASSWORD 'metagame' CREATEDB" \
                   -c "CREATE DATABASE metagame OWNER metagame"
export DATABASE_URL=postgresql://metagame:metagame@localhost:5432/metagame  # (default)
```

Data prerequisites (both gitignored under `data/`):

```bash
git clone --depth 1 https://github.com/Badaro/MTGODecklistCache data/MTGODecklistCache
# Scryfall bulk data (oracle cards, JSONL) -> data/scryfall/oracle-cards.jsonl
```

## One-command rebuild (M0 definition of done)

```bash
make rebuild
```

Drops and recreates the database, applies migrations, ingests Scryfall cards,
imports every import-enabled format from the cache clone, runs post-import
data-quality gates, and writes the data-quality report to
`validation/reports/`. Deterministic: two consecutive rebuilds produce
byte-identical reports.

## Checks

```bash
make lint typecheck checks test
```

`make checks` runs the two custom CI gates: the game-neutrality import check
(nothing in `models/`, `jobs/`, `api/` may reference game-specific modules or
literals, plan §4.1) and the normalization determinism check.
