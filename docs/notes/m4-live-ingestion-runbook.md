# M4 — Live ingestion: operations runbook

How the daily MTGO ingestion runs unattended, how to watch it, and how the
14-day DoD is measured. Milestone: plan §7 M4 — *"14 consecutive days of
unattended daily ingestion with alerting on failure."*

## What runs each day
`python -m ingest.mtgo_scraper.daily --game mtg --format modern` runs the
chain (`ingest/mtgo_scraper/daily.py`):

| step | required | what it does |
|------|----------|--------------|
| melee_scrape | best-effort | Melee.gg (plan §10 risk 2). Off unless `METASURF_MELEE_ENABLED`; a failure warns and NEVER blocks MTGO. |
| mtgo_scrape | ✅ | fetch new mtgo.com/decklists events → raw HTML archive → CacheItem JSON |
| import | ✅ | `run_import(skip_existing)` — normalize into canonical tables; DQ gates inside |
| match_extract | ✅ | challenge brackets → `matches`; DQ gates inside |
| label | ✅ | `archetypes.labeler` relabels every deck |
| rollups | ✅ | `jobs.rollups` rebuilds `rollup_*` (what the API serves) |

A **required** step failure alerts and aborts the rest of the chain (never
roll up a DB whose import failed). A **best-effort** failure warns and
continues. Every run appends one record to `daily_status.jsonl`.

Politeness (built in): custom UA, ≤1 req/sec/host, exponential backoff,
`data/raw` archive written before parsing, already-archived events never
re-fetched, already-imported events skipped (`(source, source_event_id)`).

## Deploy
1. Python 3.11+ venv with the project installed (`make setup` into a venv).
   NB: the plain-cron/systemd/launchd units call the venv interpreter
   explicitly — do not rely on a system `python`.
2. Postgres reachable via `DATABASE_URL`; migrations applied
   (`alembic upgrade head`); `cards` populated (`python -m ingest.scryfall …`).
3. Copy `deploy/metasurf-daily.env.example` → your env file and set the paths
   + (optionally) `METASURF_ALERT_CMD`.
4. Schedule one of:
   - **Linux**: `deploy/metasurf-daily.{service,timer}` →
     `systemctl enable --now metasurf-daily.timer`
   - **macOS**: `deploy/com.metasurf.daily.plist` → `~/Library/LaunchAgents/`,
     `launchctl load …`
   - **any Unix**: `deploy/crontab.example`

Run it once by hand first and confirm a green status line for every step.

## Monitoring
- **DoD verdict / streak:** `python -m ingest.mtgo_scraper.soak --state-dir <dir>`
  prints the current consecutive-successful-day streak (`N/14`), whether the
  DoD is met, and the last failures. Exit code 0 iff met — wire it to a check
  if you like. A day counts as successful iff its **last** run that day
  succeeded (a fixed re-run rescues a day; a later breakage spoils it).
- **Per-run history:** `data/state/daily_status.jsonl`, one JSON record per
  run (`started_at`, `ok`, per-step `status`).
- **Alerts:** `data/state/alerts.jsonl` (+ stderr, + `METASURF_ALERT_CMD`).
  `error` = the MTGO chain failed and aborted; `warning` = a best-effort step
  (Melee) failed, MTGO unaffected.

Healthy day looks like: `[ok]` for all six steps, `mtgo_scrape` written/
already-have counts add up to the day's events, `import` skipped-existing
growing, no new `alerts.jsonl` line.

## When an alert fires
1. Read the alert body (full traceback) in `alerts.jsonl`.
2. Common causes & responses:
   - **DQ gate: "events dated more than 2 days in the future"** → a real
     parse/date bug (not the normal next-day boundary, which is tolerated).
     Inspect the offending event's raw HTML in `data/raw/…`; fix the parser;
     the raw archive lets you reprocess without re-fetching.
   - **DQ gate: deck-size / referential / count<1** → malformed event; inspect
     the archived raw HTML; add a fixture + parser fix (TDD).
   - **import "cards table is empty"** → run the Scryfall ingest.
   - **DB unreachable** → the `startup` step records the failure and alerts;
     fix Postgres and the next run recovers (idempotent, skip_existing).
   - **many new `ingest_unresolved_cards`** → a new set released;
     refresh the Scryfall bulk and re-run (names are logged, never guessed).
   - **site structure changed** (parse_errors climbing in the scrape summary)
     → capture the new page under `tests/fixtures/mtgo.com/`, update the
     parser against it (TDD), reprocess from the raw archive.
3. Re-run the chain by hand; a same-day success rescues the day's streak.

## Recovering / reprocessing
The raw HTML archive (`data/raw`) is immutable and complete, so any parser
improvement can be re-applied to history: delete the affected CacheItem JSON
under the cache root and re-run — `fetch_event` serves the archived HTML (no
re-fetch), re-parses, and the importer picks up the corrected event.

## DoD tracking (14 consecutive days)
Start date: run the chain daily; check `soak` each morning. The milestone is
met when `soak` reports `current streak: 14/14 … DoD: MET`. Keep the
`daily_status.jsonl` from the soak window as the evidence artifact.
