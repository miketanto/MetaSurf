# Handoff — next features (post-Standard)

Pick-up doc after the M4 + Standard-enablement session. Branch:
`formats-standard` (off `claude/m5-read-api-handoff-etj6gx`), **22 commits,
local-only / unpushed**. All gates green: **188 tests, ruff, mypy,
game-neutrality, determinism.** Supersedes `m4-live-ingestion-handoff.md` for
what's shipped; read that for the M4 detail.

## 0. State — what's built and validated
- **M4 live ingestion**: own mtgo.com scraper → raw archive → normalize →
  nightly label/rollup chain → failure alerting → monitoring. Validated on
  real data. (14-day soak intentionally deferred by the owner — machinery
  ready; not a blocker.)
- **Sources**: mtgo.com ✅ live. **TopDeck.gg** ✅ built + validated on real API
  (best-effort, opt-in; **rotate the pasted key** before enabling). Melee ⏳
  partnership-gated (email draft: `docs/notes/melee-api-access-email.md`).
- **Classification granularity**: `--granularity variant` surfaces rule
  variants + color groups (Boros Energy / Esper Blink / Broodscale), linked via
  `archetypes.parent_id`.
- **Standard format enabled** (the "formats are config" design): ported rules
  from MTGOFormatData; live legal-only meta; historical corpus imported from
  the (now-on-disk) MTGODecklistCache clone.
- **Legality-aware meta**: card legalities ingested (`cards.attrs.legalities`);
  the served meta/matchups/best-decks exclude rotated/banned-card decks
  (`weekend_archetype_counts`, game-neutral). Historical decks kept for
  backtesting.
- **Era-matched labeling** (`archetypes/classifier/eras.py`, labeler `--era`):
  rotating-format decks are labeled with the rule set current at their event
  date, derived config-free from dated definition folders. Transferable to any
  format.
- **V1 harness format+era-parameterized**: `--format / --holdout-* / --rules-dir`.
  **Standard V1**: era `20240803-20250730` **PASSES** all criteria (V1.1 0.9876,
  V1.2 both Duskmourn emergence events detected, V1.3 deterministic); era
  `20230701-20240802` passes agreement but flags Reanimator F1 0.881
  (clustering recovery, one 64-deck archetype) — documented, owner to accept or
  tune. Reports: `validation/reports/standard-v1-archetypes-era{1,2}-...md`.
- **Deck-map viz** (`validation/deck_map.py --html`): 2D card2vec scatter,
  click a dot → decklist; source-attribution footer.

## 1. Outstanding owner / operational actions
1. **Push the branch / open a PR** — 22 commits are local-only.
2. **Rotate the TopDeck API key** (pasted in chat = exposed), then set
   `TOPDECK_API_KEY` + `METASURF_TOPDECK_ENABLED` to enable it in the chain.
3. **Melee** — send the drafted access email when ready.
4. **Soak** — install a scheduler (`deploy/`) + wire `METASURF_ALERT_CMD` when
   you want the 14-day DoD clock to run.
5. **Standard era1 Reanimator F1 0.881** — accept the documented caveat (era2
   is a clean pass) or spin off a clustering-tune task.
6. **9 Standard cards unresolved** — not in Scryfall yet (new set coverage lag);
   auto-resolve when catalogued. No action.

## 2. Next-features roadmap (owner to sequence)
- **(A) Emerging-deck feed (`/emerging`, plan S5) — ✅ BUILT (branch
  `feature-emerging`).** See §4 for the build-out addendum (seam choice, tests,
  what it surfaced on real data). Detect → characterize → provisional-descriptor
  → promote-to-rule loop is shipped; auto-naming deliberately not built.
- **(B) More formats** — Pioneer / Legacy / Pauper / Vintage. Same battle-tested
  recipe (flip `import`, port that format's rules, V1). Non-rotating formats
  skip the era tooling. Mechanical, high reach.
- **(C) M6 insight features** (research-log §4) — tech-watch / hidden-tech
  finder; higher effort, gated on more live data.
- **(D) Phase 2** (separate plan) — mobile/web app, auth, freemium.
- Backlog: MTG Arena (BL-5, licensing-gated source).

## 3. Kickoff prompt — Emerging-deck feed (paste into a new session)

---
Start the next feature — **Emerging-deck feed (`/emerging`, plan §8 S5)** for
the MetaSurf Metagame Platform. Full context: `docs/notes/next-features-handoff.md`
and `docs/notes/m5-read-api-handoff.md` §10a (which flagged `/emerging` as a
deferred design decision).

REPO SETUP: base on the local branch `formats-standard` (22 commits, unpushed —
push if starting from a fresh clone). `git checkout -b feature-emerging`.
`make setup` (Python 3.11 — bare `python` is a pyenv 3.9 shim; use python3).
Postgres 16; `DATABASE_URL=postgresql://metagame:metagame@localhost:5432/metagame`.
Verify green first: `make lint typecheck checks test` (188 tests).

REQUIRED READING (in order): CLAUDE.md (rule 4: never author archetype names
from your own knowledge — humans name; the system proposes a PROVISIONAL
descriptor only); metagame-app-start-plan.md §5 Layer-1 clustering stage + §8
S5; docs/notes/m5-read-api-handoff.md §2 (the game-neutral ClassifierService
Protocol seam — mirror it) + §10a (`/emerging` deferral); docs/research-log.md
§2; the validated clustering stage `archetypes/classifier/clustering.py` +
`validation/v1_archetypes/run.py::run_v12` (how emergence detection already
works and is tested).

SCOPE:
1. **Detect** — cluster the Rogue/unlabeled pool per format+as_of with the
   validated `cluster_and_attach`; a dense new cluster not matching any rule is
   a candidate emerging archetype.
2. **Characterize** — per cluster: signature cards (TF-IDF-style in-cluster vs
   out), color identity (reuse engine `_GUILD_NAMES`), size, first-seen date,
   growth, and winrate if matches exist. A PROVISIONAL descriptor = color + top
   signature card (clearly marked "unnamed / emerging" — NOT a curated name).
3. **Serve** — additive migration `rollup_emerging` + `GET /v1/{g}/{f}/emerging`
   (premium; gate via the entitlements module). Clustering is MTG-specific
   (`archetypes/`), which `jobs/`/`api/` may not import — put it behind a
   game-neutral seam like the classify Protocol (an emerging-service Protocol in
   `api/`, MTG adapter in `archetypes/`, injected at `serve.py`), OR a
   game-specific rollup writer that lives outside `jobs/`. Pick one; document it.
4. **Promote** — a small helper that scaffolds a rule file from a cluster's
   signature cards for a human to review + name (closes the loop; the named
   rule then classifies future decks deterministically).

HARD RULES: never auto-mint an archetype NAME (rule 4) — provisional descriptors
only, flagged as unnamed. Keep the game-neutrality gate green (clustering behind
the seam; no MTG imports/literals in models/jobs/api). Migrations additive-only.
Determinism: clustering already takes fixed seeds — keep the feed reproducible.
Fixture-DB tests for the rollup + contract tests for the endpoint (tier gating).
No fabricated numbers. Validate on real data (the DB has live + historical
Standard/Modern; the Rogue pool grows with the soak).

SUGGESTED ORDER: (1) read + verify green; (2) emerging-cluster characterizer +
`rollup_emerging` migration + fixture-DB test; (3) the game-neutral seam +
`GET /emerging` + contract test + OpenAPI; (4) the promote-to-rule helper;
(5) run it on the real corpus and report what it surfaces.

DO NOT: auto-name archetypes; start more formats, M6, MTG Arena, or Phase 2 —
one feature at a time.
---

## 4. Build-out addendum (2026-07-08, emerging-feed session)

Built on branch `feature-emerging` (off `formats-standard`). All gates green:
**206 tests, ruff, mypy, game-neutrality (29 files), determinism.**

**The seam choice.** Clustering is MTG-specific (`archetypes/`) and `jobs/`/`api/`
may not import it. Two seams, chosen per direction:

- **Read side — no seam needed.** `GET /v1/{game}/{format}/emerging` serves the
  precomputed `rollup_emerging` tables like any other rollup; `api/` stays
  game-neutral by reading persisted tables only (mirrors how `/meta` reads
  `rollup_meta`). Premium-gated through the entitlements module.
- **Build side — a Protocol seam, like classify.** `api/emerging.py` defines the
  game-neutral `EmergingBuilder` Protocol; `archetypes/emerging_service.py` is
  the MTG adapter; `scripts/build_emerging.py` is the composition root (outside
  the gated packages) that wires it and runs nightly alongside
  `python -m jobs.rollups`. The actual writer,
  `archetypes/emerging.build_emerging`, lives game-side because it clusters card
  vectors — the "game-specific rollup writer outside `jobs/`" option, reached
  through the Protocol. This resolves the design decision flagged in
  `m5-read-api-handoff.md` §10a.

**Pieces.** `0003_rollup_emerging.py` (additive: `rollup_emerging` +
`rollup_emerging_signature` child, snapshot-keyed by format_id+as_of);
`archetypes/emerging.py` (detect via the validated `cluster_and_attach` over the
Rogue/unlabeled pool → characterize: signature-card in-vs-out lift, engine
`deck_color`/`_GUILD_NAMES` color identity, size, first-seen, 7-day growth,
cluster winrate over decided games); `archetypes/promote.py` (scaffold a
ported-shape rule file from a cluster's signatures — placeholder name only,
`assert_named` refuses to promote unnamed). Fixture-DB tests
(`tests/test_emerging.py`, `tests/test_promote.py`) + contract tests in
`tests/test_api.py`; regenerated `api/openapi.json`.

**CLAUDE.md rule 4 held throughout.** The feed never mints a name: every cluster
carries `named=false` + a `provisional_descriptor` = `"Unnamed: <color group>
<top signature card>"`. The promote helper scaffolds key-card conditions but
leaves a loud `RENAME_ME_…` placeholder for a human. The loop-closing test
proves a *human-named* scaffold, loaded by the production engine, then
classifies its own cluster deterministically.

**What it surfaced on the real corpus** (built with `scripts/build_emerging`;
`as_of` = latest event 2026-07-08; 30-day default window; every number is
printed job output). Rebuild is byte-identical (determinism verified):

- **Standard — 3 candidate clusters.** Cleanest arrival: `Unnamed: Bant
  Nature's Rhythm` — **12 lists, all 12 in the last 7 days, 83% winrate over 6
  games**; signature `Nature's Rhythm` at in-cluster freq 1.00 / out 0.00 (lift
  100). Exactly the plan §8 S5 shape ("new cluster detected, N lists, X%
  winrate, unnamed"). Also `Unnamed: MonoWhite Meticulous Archive` (7 lists, no
  match data) and `Unnamed: Izzet Steam Vents` (6 lists, 0/2).
- **Modern — 6 candidate clusters** over the ~3-week live pool, led by
  `Unnamed: MonoBlack Verdant Catacombs` (24 lists, 0.46 over 13 games) and a
  family of MonoBlue tempo/artifact clusters (Relic of Progenitus 12 @ 0.75/4;
  Emry 8; Aether Spellbomb 6; Hall of Storm Giants 6; Preordain 5).

These are *candidates* for a human to name, not validated archetypes; the winrates
are small-sample (shown with n). The Modern MonoBlue split into several small
clusters is expected clustering granularity on a thin live pool — a human names
the real one and `promote.py` scaffolds its rule.

**Not run in this env / follow-ups.** Determinism CI (`scripts/check_determinism.py`)
still hashes only the V1 suite; the emerging feed's reproducibility is covered by
its fixture test + the real-corpus rebuild diff above (owner may fold an emerging
snapshot into the determinism gate later). The nightly scheduler wiring for
`scripts/build_emerging` belongs with the M4 soak (deploy/).
