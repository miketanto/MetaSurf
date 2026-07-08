# M5 — Read API: handoff

Pick-up doc for building **M5 (plan §7)**: the FastAPI read layer that serves
the validated model stack from precomputed rollups. Nothing here needs M4
(live ingestion) — the frozen corpus is a complete, valid dataset to build and
validate the whole API against; M4 later just refreshes the same tables.

## 0. TL;DR — where to start
1. Add a rollup migration (`0002_rollups.py`, additive) — tables in §4.
2. Build `jobs/rollups/` — game-neutral jobs that read canonical tables + call
   the `models/` functions in §5 and write the rollup tables. Test on the
   fixture DB like the ingest/label/match suites do.
3. Build `api/` — FastAPI, namespaced `/v1/{game}/{format}/…`, reading ONLY
   rollup tables. Endpoints + tiers in §3.
4. First slice: **meta snapshot + matchup matrix + recommended decks** — all
   from M2/V-REC, all validated, all frozen-data-ready.

## 1. What is ready to serve (the validated stack)

| Product surface | Backing model | Where | Status |
|---|---|---|---|
| Matchup matrix (cell winrate, CI, sample size) | M2 winrate | `models/winrate` | ✅ validated |
| Meta snapshot (share, shrunk winrate ± CI) | M2 winrate + archetype_labels | `models/winrate` | ✅ |
| Recommended "best decks this weekend" | V-REC recommender | `models/recommender` | ✅ validated (0.564 WR) |
| Archetype detail (share/winrate history) | M2 + share panel | `models/winrate`, `validation/v3_evolution/data` | ✅ |
| Deck similarity / classify a pasted list | M3.8 embeddings + classifier | `models/embeddings`, `archetypes/classifier` | 🔬 embedding validated (0.773) |
| Contrarian "overextended" trend flag | M3.6-3 mean-reversion | descriptive | 🔬 honest framing |
| Macro strategy-family grouping | M3.8 clusters | `models/embeddings` | 🔬 navigation only |
| Share *prediction* | — | — | ❌ do not ship |

See `docs/research-log.md` for the full ledger and the load-bearing numbers.

## 2. Architecture (plan §4: rollups → API)

```
canonical tables (decks, matches, archetype_labels, deck_cards, cards)
        │  read by
        ▼
jobs/rollups/*   ── call models/{winrate,recommender,embeddings} ──►  rollup tables
        │                                                              (precomputed)
        ▼
api/  (FastAPI, /v1/{game}/{format}/…)  ── reads ONLY rollup tables ──►  clients
```

- **`jobs/` and `api/` stay game-neutral** (CI gate `scripts/check_game_neutrality.py`,
  scope = `models/ jobs/ api/`): no `import ingest`/`archetypes`, no literal
  `"mtgo"/"scryfall"/"oracle_id"/"mainboard"/"sideboard"/"mtg"/"modern"`. This
  is already satisfied by reading the *persisted* canonical tables (which key
  on `game_id`/`format_id`/`archetype_id`) and calling the game-neutral model
  functions. `game`/`format` arrive as **URL path variables**, never as
  hardcoded strings.
- **The one wrinkle — on-demand classification.** Classifying a user-pasted
  list needs the MTG classifier + card resolver (`archetypes/`, `ingest/`),
  which `api/` may not import. Put it behind a boundary: define a game-neutral
  `ClassifierService` Protocol in `api/`, implement it in an MTG adapter
  (e.g. `archetypes/service.py` or a new `adapters/`), and inject the impl at
  app startup (FastAPI dependency). `api/` depends on the Protocol only. The
  embedding-similarity half ("lists like yours") is game-neutral and can live
  in a rollup + `models/embeddings`.

## 3. Endpoints (mapped to plan §8 screens)

`tier`: free / premium (gate through ONE entitlements module — plan §4.2 —
never inline checks). `source`: rollup (precomputed) or live (computed per
request). All frozen-data-OK.

| endpoint | screen | tier | source | backing |
|---|---|---|---|---|
| `GET /v1/{g}/{f}/meta` | S1 | free | rollup | share + shrunk WR±CI + 7d sparkline |
| `GET /v1/{g}/{f}/matchups` | S2 | free | rollup | full matrix, each cell WR/CI/n |
| `GET /v1/{g}/{f}/matchups/{a}/{b}` | S2 | free→premium history | rollup | cell detail: n, CI, trend; history = premium |
| `GET /v1/{g}/{f}/archetypes/{id}` | S3 | mixed | rollup | current free; 30/90d series = premium |
| `GET /v1/{g}/{f}/best-decks` | S2/S6 | free | rollup | ranked best-positioned (V-REC) |
| `GET /v1/{g}/{f}/events` | S4 | free | rollup | recent results feed |
| `GET /v1/{g}/{f}/trends` | S5 | premium | rollup | movers + contrarian flag |
| `POST /v1/{g}/{f}/classify` | S6 | premium | live | classify pasted list → archetype + "lists like yours" |
| `GET /v1/{g}/{f}/emerging` | S5 | premium | rollup | clustering new-cluster feed (M1 stage) |

DoD (plan §7): **p95 < 200 ms on every read endpoint** (trivially met by
serving rollups) and a **committed OpenAPI spec**.

## 4. Rollup tables (proposed; additive migration `0002_rollups.py`)

All keyed by `format_id` + an `as_of` date so a nightly job appends a new
snapshot without mutating old ones (plan §4.3: rollups are client contracts;
additive only).

```
rollup_meta(format_id, as_of, archetype_id, share, winrate, wr_ci_lo, wr_ci_hi, n_decks)
rollup_matchups(format_id, as_of, arch_a, arch_b, p_a_beats_b, ci_lo, ci_hi, n_matches)
rollup_archetype_ts(format_id, archetype_id, week, share, winrate, wr_ci_lo, wr_ci_hi)
rollup_best_decks(format_id, as_of, rank, archetype_id, exp_winrate_vs_field)
rollup_card_similarity(format_id, card_id, neighbor_card_id, rank, cosine)   -- from embeddings
rollup_events(format_id, event_id, date, name, source, top_archetype_id)     -- feed
```
(Card drift / matchup history series are premium; add `rollup_card_drift`,
`rollup_matchup_ts` when building S3/S5.)

## 5. Model APIs the rollup jobs call (concrete)

```python
# winrate + matchups (as-of the latest corpus date)
from validation.v2_winrates.data import load_match_data, n_archetype_slots  # DB→MatchData
from models.winrate import WinrateModel
data, names, _ = load_match_data(conn, format_name)     # names: {archetype_id: name}
post = WinrateModel().fit(data, as_of_day, n_archetype_slots(names))
post.archetype_mean()                                    # winrate per archetype id
post.archetype_interval(0.90)                            # (lo, hi) arrays
post.match_prob(a_ids, b_ids)                            # P(a beats b), vectorized
post.matchup_interval(a_ids, b_ids, 0.90)                # cell CI

# recommended decks (over the current universe)
from models.recommender import rank_by_best_response      # ranked indices
from validation.v3_evolution.walkforward import universe_mask  # trailing-1% universe
from validation.v3_evolution.data import load_share_panel      # weekly shares/counts

# card similarity ("lists like yours")
from models.embeddings import embed, nearest              # PPMI-SVD (deterministic)
# build cooc = D.T @ D over the vocab (see validation/embeddings_explore.build)
```
These are the exact calls the exploratory scripts use — lift the DB-loading
patterns from `validation/v3_evolution/data.py`, `v_recommender/run.py`, and
`embeddings_explore.py`; the model calls are already game-neutral.

## 6. Constraints & gotchas
- **Additive migrations only** (plan §4.3): new `rollup_*` tables, never alter
  canonical ones. Alembic, following `0001`.
- **Game-neutrality gate** runs on `jobs/` + `api/` — keep MTG behind the
  classifier Protocol (§2). Run `python scripts/check_game_neutrality.py`.
- **Determinism**: rollup jobs must be reproducible (all model calls are;
  fix any ordering). Consider a determinism check on a rollup snapshot.
- **Entitlements**: build `api/entitlements.py` first; every premium field
  gates through it. Design endpoints with `tier` from day one (plan §8).
- **Testing discipline** (CLAUDE.md): rollup jobs get fixture-DB tests like
  `tests/test_labeler.py`; API endpoints get contract tests (FastAPI
  `TestClient`) asserting shape + tier gating on a seeded rollup.
- **`as_of` semantics**: on the frozen corpus, "current" = the latest event
  date (2025-06-09). Parameterize it; don't hardcode `date.today()`.

## 7. Frozen-data-OK vs needs M4
- **All read endpoints in §3 are fully buildable and testable on the frozen
  corpus.** The API's correctness does not depend on live data.
- M4 only changes *freshness*: once the live scraper runs, the nightly rollup
  job reruns against new events and the same endpoints serve current data.
  Build M5 now; wire M4 to the rollup refresh later.

## 8. Suggested build order
1. `0002_rollups.py` + `jobs/rollups/meta.py` + `jobs/rollups/matchups.py` →
   `rollup_meta`, `rollup_matchups`. Fixture-DB test.
2. `api/` app + `entitlements.py` + `GET /meta`, `/matchups`,
   `/matchups/{a}/{b}` (free). `TestClient` contract tests. Commit OpenAPI.
3. `jobs/rollups/best_decks.py` + `GET /best-decks` (the V-REC feature).
4. `jobs/rollups/archetype_ts.py` + `GET /archetypes/{id}` (free + premium tier).
5. Embedding similarity rollup + `POST /classify` behind the classifier
   Protocol (the one non-trivial architecture piece).
6. Trends/emerging (premium) last.

## 9. Dependencies to add (`pyproject.toml`)
`fastapi`, `uvicorn[standard]`, `httpx` (TestClient). None are game-specific.

## 10a. Build-out addendum (2026-07-07, M5 session)

Build order items 1–5 are implemented on this branch:

- `0002_rollups.py` — five additive tables (`rollup_meta`, `rollup_matchups`,
  `rollup_archetype_ts`, `rollup_best_decks`, `rollup_events`).
  `rollup_card_similarity` was NOT created yet — add it with the
  "lists like yours" feature (see below).
- `jobs/rollups/` — one builder per table + `python -m jobs.rollups` CLI.
  Definitions reuse the validated protocols (Sat-keyed weekend buckets,
  trailing-8-week pooled share, >= 1% universe, V-REC best-response scoring).
- `api/` — all §3 read endpoints except `/emerging`; entitlements module;
  committed `api/openapi.json` + freshness test. Measured worst p95 =
  17.0 ms over 200 reqs/endpoint on a real uvicorn with fixture-corpus
  rollups (DoD < 200 ms; PK-indexed reads, result sizes scale with
  archetypes × weeks, not deck count).
- `POST /classify` — done via `api/classifier.py` (Protocol + DTOs),
  `archetypes/service.py` (adapter over the labeler's exact stack), and
  `serve.py` (composition root; `uvicorn serve:app`). A contract test
  asserts the on-demand path reproduces the batch label on a real corpus
  deck. The "lists like yours" half is NOT built: it needs the embedding
  rollup (`rollup_card_similarity`) and a recent-deck-vector story — design
  it with the S6 feature.
- `GET /trends` — movers only (share delta between the last two data weeks,
  descriptive). The contrarian "overextended" flag is deliberately NOT
  shipped: BL-4 in the research log requires a forward test on live (M4)
  data first.

Deliberately not built, for the owner to sequence:

- `/emerging` — the M1 clustering stage is not part of batch labeling and
  lives in `archetypes/` (game-specific), so the feed needs either a second
  Protocol seam like classify or a game-specific rollup writer outside
  `jobs/`. Design decision required. **RESOLVED + BUILT** on branch
  `feature-emerging`: both, actually — read side serves `rollup_emerging`
  game-neutrally (no seam), build side goes through the `EmergingBuilder`
  Protocol to a game-side writer outside `jobs/`. See
  `next-features-handoff.md` §4.
- Alert subscriptions (plan §8 "add to M5 scope") — the first user *write*
  path; belongs with auth (Phase 2 seam §4.2), not in the read layer.
- "Projected weekend meta" — ruled out by the M3 verdict (do not ship share
  prediction).

## 10. State at handoff
Branch `claude/metagame-m2-layer-2-tulgzm`, 18 commits, all gates green (98
tests, ruff, mypy, game-neutrality, determinism). `make rebuild` reproduces
the corpus + labels + matches. Validated models: `models/winrate`,
`models/recommender`, `models/embeddings`. Reports under
`validation/reports/`; research trail in `docs/research-log.md` and
`docs/notes/`.

