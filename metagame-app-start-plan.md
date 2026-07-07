# Constructed Metagame Platform — Start Plan (Brief for Claude Code)

**Version:** 1.0 — July 2026
**Working name:** TBD (“the platform”)
**Owner’s vision:** An all-in-one mobile-first TCG metagame product (inspiration: mtgdecks.net) with strictly better data analysis, centered on modeling metagame *evolution* per day/week from winrates and card choices per archetype. Freemium: free snapshot views, paid trend/prediction/alert features.

-----

## 1. Guiding principles

1. **Provable before pretty.** Every model layer ships with a falsifiable backtest and a numeric acceptance criterion. No model graduates to the product until it beats its baseline on held-out data. The validation suite is a permanent part of the repo, not a one-off notebook.
1. **Raw data is sacred.** Every scrape is archived raw (JSON/HTML) before parsing. Parsers and classifiers will improve; reprocessing history must always be possible.
1. **No single point of data failure.** WotC has twice moved to restrict MTGO decklist publication (late 2023; February 2026 — reversed after community backlash). Architecture must tolerate any one source dying.
1. **Phase 0 needs no app.** The entire model stack is validated on historical data as a research repo before any product code exists.

## 2. Scope

**In scope now (Phase 0–1):** Constructed MTG metagame. One launch format: **Modern**. Data ingestion, archetype classification, winrate estimation, evolution modeling, validation suite, then a read API.

**Explicit backlog (do NOT build yet, but don’t architect it out):**

- Additional constructed formats (Standard, Pioneer, Legacy, Pauper) — should be config, not code.
- Limited/draft metagame tool built on 17Lands public datasets (archetype discovery in draft decks; premium feature). Requires checking 17Lands data license terms for commercial use before build.
- EDH/Commander popularity product (EDHREC-like). Note: requires data partnership with Moxfield/Archidekt — bulk scraping violates their ToS. No winrate data exists for casual EDH; different analytics, same infra.
- Other TCGs: Pokémon (Limitless TCG has a real API), Yu-Gi-Oh (YGOPRODeck), Lorcana/One Piece (mostly on Melee/TopDeck — the Melee pipeline is reusable).
- **Local meta logger.** Users log decks/archetypes they see at FNM/RCQs (<5-second archetype-picker flow, offline-capable). Personal local-meta dashboard + “how to metagame against it” recommendations combining local log with global data. Strategically important: proprietary paper-local data nobody can scrape; per-store/region network effects. Privacy stance: personal-first; aggregated regional views only via opt-in (avoid “scouting tool” backlash).

## 3. Data sources (verified July 2026)

|Source                                                    |Status                                          |Use                                                               |Notes                                                                                                                                                                                                                       |
|----------------------------------------------------------|------------------------------------------------|------------------------------------------------------------------|----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
|`github.com/Badaro/MTGODecklistCache`                     |**Shut down June 2025** (mtgo.com scraper broke)|Historical backfill + backtesting corpus                          |Years of MTGO/Melee/Manatraders/TopDeck tournaments as JSON. mtgo.com data from 2024-06-20 onward is more limited (site change). Clone once; treat as frozen.                                                               |
|`mtgo.com/decklists`                                      |Live                                            |Primary live source: Leagues (5-0s), Challenges, Prelims          |We build and own this scraper. Decklist pages embed structured data. Leagues = card-choice signal only (winner-censored); Challenges = winrate-capable (standings/brackets).                                                |
|Melee.gg                                                  |Live                                            |Paper tournament decklists + **round-by-round pairings/standings**|Pairings are the only large-scale source of true matchup winrates. Their public API/scraping situation is unstable (scrapers broke March 2025) — budget time for a robust scraper AND pursue a data partnership in parallel.|
|TopDeck.gg                                                |Live                                            |Paper events, data-friendly org                                   |Secondary paper source; check their API/export options first, scrape second.                                                                                                                                                |
|`github.com/Badaro/MTGOFormatData` + `MTGOArchetypeParser`|Unmaintained but public                         |**Seed for the rules layer of archetype classification**          |Open-source, human-curated archetype definitions (key-card conditions) per format. Port the definition format; do not depend on the .NET runtime.                                                                           |
|Scryfall API                                              |Live, free, stable                              |Canonical card database                                           |Key all cards to Scryfall **oracle IDs**. Respect their rate-limit guidance; cache bulk data files locally.                                                                                                                 |
|mtgtop8                                                   |Live                                            |Optional backfill only                                            |It’s an aggregator like us; lowest priority.                                                                                                                                                                                |

**Legal/ethics stance:** decklists as facts aren’t copyrightable, but be a polite scraper everywhere: identify with a UA string, throttle, cache aggressively, honor robots.txt where feasible, and prefer partnerships (Melee, TopDeck) as soon as there’s traction.

## 4. Architecture

```
[Scrapers: mtgo | melee | topdeck]      (one worker per source, own schedule)
        │  raw JSON/HTML
        ▼
[Object storage: raw archive, immutable, keyed by source/date/event]
        ▼
[Normalizer] ──► canonical schema (games, cards, events, decks, deck_cards, matches, standings)
        ▼                    cards resolved to game-neutral card_id (MTG resolver: Scryfall oracle_id)
[Postgres]
        ▼
[Archetype classifier]  rules layer (MTGOFormatData-style) + clustering layer
        ▼               every deck stores archetype_id + classifier_version
[Analytics jobs (nightly)]
        meta share ▪ shrunk winrates ▪ matchup matrix ▪ card-choice drift ▪ forecasts
        ▼
[Read API] ──► mobile app reads ONLY precomputed rollups (fast, cheap)
```

**Stack:** Python 3.12, Postgres 16, object storage (S3-compatible; local MinIO in dev), Prefect or plain cron+systemd for scheduling (keep it boring), FastAPI for the read API. Mobile client decision deferred to Phase 2 (likely React Native or Flutter — do not decide now).

### Canonical schema (minimum)

All entities carry a `game` dimension from day one, even while only MTG exists — retrofitting a game column onto a live schema is exactly the migration pain we’re avoiding.

- `games(id, name)` and `formats(id, game_id, name, config)` — formats are rows + config, never code branches
- `cards(id, game_id, canonical_ref, name, attrs_jsonb)` — the game-neutral card identity table. For MTG, `canonical_ref` = Scryfall oracle_id; other games plug in their own resolver (Pokémon/Limitless IDs, YGOPRODeck IDs). All internal code joins on `cards.id`, never on game-specific IDs.
- `events(id, game_id, source, source_event_id, format_id, date, event_type, player_count, raw_ref)`
- `decks(id, event_id, player, finish_rank, wins, losses, draws, archetype_id, classifier_version)`
- `deck_cards(deck_id, card_id, count, board)` — board is per-game config (MTG: main/side; Pokémon: single board; etc.)
- `matches(id, event_id, round, deck_id_a, deck_id_b, result)` — populated only from pairing-capable sources (Melee, Challenge brackets)
- `archetypes(id, format_id, name, status, parent_id, created_at)` — parent_id supports archetype splits
- `archetype_labels(deck_id, archetype_id, classifier_version, method, confidence)` — full relabeling history

### 4.1 Multi-game portability rules

1. **Source adapters behind one interface.** Every scraper implements `fetch_events(since) -> raw refs` and every normalizer implements `normalize(raw) -> canonical entities`. Adding a TCG = new adapter + card resolver + archetype rule files. Zero changes to models, jobs, or API code.
1. **The model stack is already game-neutral.** Layers 1–3 operate only on canonical entities (card vectors, match results, time series). They must never import anything MTG-specific; MTG knowledge lives exclusively in adapters, card resolvers, and rule/config files. Enforce with a lint rule or import check in CI.
1. **API namespaced by game/format from v1:** `/v1/{game}/{format}/meta`, etc. MTG-only at launch, but clients never bake in “MTG is the only game.”
1. **Per-game config, not constants:** deck size, board zones, basic-land-equivalent exclusion lists, staple down-weighting — all in `formats.config` / rule files.

### 4.2 Extension seams (how each backlog feature lands without breaking the live app)

Each backlog item maps to a reserved seam; building it later means *adding* modules, tables, and jobs — never modifying live ones.

- **New MTG format** → new rule files + a `formats` row + scheduler entry. No code.
- **New TCG** → new source adapter + card resolver + rule files. Schema and API already shaped for it (§4.1).
- **Limited/17Lands tool** → entirely separate ingestion domain (17Lands dataset importer) writing to its own tables (`limited_*`), reusing the clustering code as a shared library and the same card table. New API namespace `/v1/mtg/limited/...`. Constructed pipeline untouched.
- **EDH product** → same deck/card tables via a new source adapter (partner API), `event_type='casual'`, and popularity/synergy rollup jobs added alongside (not inside) the constructed rollups. Winrate/evolution models simply don’t run where matches don’t exist.
- **Local meta logger** → first user-generated *write* path. Lives in its own tables (`user_sightings`, keyed to archetypes/cards) behind new authenticated endpoints; read-side “local vs global” views are new rollup jobs joining user data to existing rollups. Ingestion pipeline never touched.
- **Weekend pass / pricing changes** → all gating goes through one entitlements module (`user -> set of entitlement flags`) from day one, so new products are new flags, not scattered tier checks.

### 4.3 Change-safety rules for the live app (binding once anything is live)

- **Additive-only migrations:** new tables/columns/indexes are fine; renames, drops, and type changes require an expand–migrate–contract plan.
- **Versioned API:** breaking response changes = new version, old version deprecated on a schedule; mobile clients update slowly.
- **Feature flags on every new surface:** ship dark, enable gradually, kill-switch instantly.
- **New features add rollup jobs; they don’t modify existing job outputs.** Existing rollup tables are contracts with the clients.

## 5. The model stack (the provable core)

### Layer 1 — Archetype classifier

**Representation:** each deck = sparse vector of mainboard card counts on oracle IDs; drop basic lands; apply TF-IDF-style down-weighting of format-ubiquitous staples. Similarity: cosine (also evaluate weighted Jaccard).

**Two-stage classification:**

1. *Rules stage:* port Badaro’s MTGOFormatData definition format (conditions like “contains ≥N of card X”). Deterministic, explainable, versioned in-repo as data files.
1. *Clustering stage:* HDBSCAN over the unlabeled remainder. Outliers = “Rogue”. New dense clusters not matching any rule = **candidate new archetype** → flagged for human naming (this is the future “emerging deck alert” feature).

**Verification (acceptance criteria):**

- V1.1 Hold out ≥1 month of labeled Modern decks (labels from MTGOFormatData rules applied to MTGODecklistCache history, spot-checked by hand). Report per-archetype precision/recall/F1 and Adjusted Rand Index for the clustering stage. **Target: ≥95% agreement on established archetypes; no major archetype below 90% F1.**
- V1.2 Emergence backtest: pick ≥2 historical events where a genuinely new deck appeared (e.g., post-ban or post-set-release week in the cache). **Target: clusterer flags a new cluster within 7 days of the deck’s first ≥5 appearances, before/at the time community sites named it.**
- V1.3 Stability: re-running the classifier on the same data with the same version must be deterministic (fixed seeds).

### Layer 2 — Winrate model

**Model:** hierarchical Bayesian beta-binomial. Archetype winrates drawn from a format-level prior; updated only with match data from full-standings sources (Challenges with brackets/standings, Melee pairings). Exponential time-decay on match evidence (half-life a tuned hyperparameter, initial guess 14–21 days). Matchup matrix = same hierarchy one level deeper: pair winrates shrink toward archetype overall winrate when pair samples are thin. **League 5-0 data is NEVER used for winrates** (winner-censored); it feeds card-choice trends only.

**Verification (acceptance criteria):**

- V2.1 Calibration backtest over ≥12 months of cache data: weekly walk-forward (train on data before each Saturday, test on that weekend’s matches). Metrics: log-loss and calibration curve (reliability diagram). **Target: beat the raw pooled-winrate baseline on log-loss in ≥80% of test weeks; calibration slope within [0.9, 1.1].**
- V2.2 Interval honesty: of all “winrate = p ± CI” claims, empirical coverage of the 90% interval must be 85–95%.
- V2.3 Ablations: report log-loss with/without shrinkage and with/without time-decay. Each component must earn its complexity or be removed.

### Layer 3 — Evolution model

**State per archetype per day:** meta share, latent winrate (from Layer 2), card-inclusion frequency vector. **Model:** Holt’s linear exponential smoothing per series, plus one behavioral coupling term: share regressed on lagged winrate (hypothesis: players flock to last weekend’s winners). Keep it simple; fancier models only after this baseline is beaten.

**Verification (acceptance criteria):**

- V3.1 Forecast next weekend’s meta share per archetype; score MAE. Baseline: persistence (“same as last week”). **Target: ≥10% MAE improvement over persistence, sustained over a ≥6-month walk-forward.** (Persistence is hard to beat; if we can’t, the *product* falls back to descriptive trends, which are still valuable — but we don’t market “prediction”.)
- V3.2 Test the lag hypothesis explicitly: is the lagged-winrate coefficient significant and stable across formats/periods? Report it; if not significant, drop the term.
- V3.3 Tech-drift forecast: predict next week’s mean copies of the 20 fastest-moving cards; same persistence baseline, same ≥10% target.

## 6. Repository layout

```
metagame/
  README.md                  # this plan, kept updated
  data/                      # gitignored; raw + processed local data
  ingest/
    mtgo_scraper/            # live scraper for mtgo.com/decklists
    melee_scraper/
    cache_import/            # one-shot importer for MTGODecklistCache clone
    normalize/               # source JSON -> canonical schema
  db/
    migrations/              # SQL migrations (alembic)
  archetypes/
    definitions/modern/      # rule files, ported MTGOFormatData format
    classifier/              # vectorizer, rules engine, HDBSCAN stage
  models/
    winrate/                 # Bayesian beta-binomial + matchup matrix
    evolution/               # Holt + lag coupling, forecasting
  validation/
    v1_archetypes/           # V1.1–V1.3 backtests, report generation
    v2_winrates/             # V2.1–V2.3
    v3_evolution/            # V3.1–V3.3
    reports/                 # generated HTML/MD reports with metrics, committed
  api/                       # FastAPI read layer (Phase 1b)
  jobs/                      # nightly rollup jobs
  tests/                     # unit tests; validation suites are separate above
```

## 7. Milestones and definitions of done

**M0 — Corpus online (week 1–2)**
Clone MTGODecklistCache; build `cache_import` + `normalize`; load ≥3 years of Modern into Postgres; Scryfall bulk data ingested; row counts and data-quality report generated. *DoD: reproducible one-command rebuild of the historical DB.*

**M1 — Layer 1 validated (week 2–4)**
Port Modern archetype rules; build classifier; run V1.1–V1.3; commit validation report. *DoD: acceptance criteria met or a written analysis of why targets were adjusted.*

**M2 — Layer 2 validated (week 4–6)**
Match extraction from Challenges + Melee history; winrate model; run V2.1–V2.3; commit report. *DoD: beats baseline per V2.1.*

**M3 — Layer 3 validated (week 6–8)**
Evolution model; run V3.1–V3.3; commit report. *DoD: honest verdict — “prediction” or “descriptive trends” positioning decided by the numbers.*

**M4 — Live ingestion (parallel from week 3)**
Own mtgo.com scraper running daily; Melee scraper best-effort; raw archive + normalize + nightly classify/rollup. *DoD: 14 consecutive days of unattended daily ingestion with alerting on failure.*

**M5 — Read API (week 8–10)**
FastAPI endpoints: current meta, archetype detail (share/winrate time series, card drift), matchup matrix + cell detail, emerging-deck feed, on-demand deck classification, alert subscriptions, projected weekend meta (see §8 for the product-driven endpoint list). All read endpoints served from precomputed rollups. *DoD: p95 < 200ms on all read endpoints; OpenAPI spec committed.*

**Phase 2 (separate plan):** mobile app, auth, freemium gating, alerts/notifications.

## 8. Product spec (drives API design; app build is Phase 2)

Design principle: every free screen showcases a locked premium widget in context — tease, don’t hide. Design API endpoints now with a `tier` concept so gating is trivial later.

**S1. Meta Snapshot (home, free).** Format picker → archetype list by meta share; each row: name, share %, shrunk winrate ± CI, 7-day sparkline. Sparkline visible free; full trend history is paid. “Biggest movers this week” carousel shown blurred to free users.

**S2. Matchup Matrix (free, flagship UX).** A genuinely explorable winrate matrix — this is a deliberate acquisition feature because every existing matrix UI online is an unreadable table dump. Free: full current-week matrix; tap any cell → sample size, confidence interval, trend arrow; filter/sort (“best positioned vs current meta”), pinch to focus your archetypes. Paid (inside the same screen): historical matchup evolution (“this matchup flipped when they adopted card X”) and matchup-specific card-choice breakdowns. The freemium line runs *through* the matrix (depth), not around it (access).

**S3. Archetype Detail (mixed).** Free: description, current share/winrate, 3 recent representative lists, average list. Paid: 30/90-day share + winrate time series, card-choice drift, matchup row detail.

**S4. Decklists & Events (free).** Recent tournament results feed with finishes and lists. Table stakes; matches incumbents’ free offering so nobody churns for basics; drives daily traffic.

**S5. Trends (paid — the subscription screen).** Rising/falling archetypes with statistical confidence; spiking tech cards across archetypes; emerging-archetype feed (“new cluster detected 3 days ago, 12 lists, 61% winrate, unnamed”).

**S6. My Deck (paid).** Paste list or Moxfield link → auto-classify → matchup spread vs current meta, expected weekend winrate, “lists like yours are adopting X”. Target user: grinder the night before an RCQ.

**S7. Alerts (paid, retention engine).** Configurable push: archetype share thresholds, new-archetype detection, card spikes, weekly meta digest.

**Onboarding:** pick formats (drives home + alert defaults), optional “decks I play” (feeds S6). No account required until a paywall or alert setup is hit.

**Additional API surface implied (add to M5 scope):** on-demand deck classification for user-submitted lists; alert subscription CRUD + nightly alert-evaluation job; “projected weekend meta” rollup; matchup-cell detail endpoint (sample size, CI, trend, history).

## 9. Target user & monetization (decided July 2026)

**Target user: the competitive grinder** — RCQ/RC paper players and MTGO league/Challenge regulars. This segment is proven price-insensitive relative to their existing spend (paper decks routinely $500–1000+, MTGO collections, event travel/fees) and has demonstrated willingness to pay for competitive edge via Metafy coaching, paid guides, and premium team content. A ~$6/mo tool is negligible against that stack. **Positioning: a tournament-prep tool, not a stats website** — the always-on complement to coaching, framed around “show up Saturday knowing the meta.” Product, copy, and premium gating decisions should all be tested against one persona question: *does this help someone win an event this weekend?*

**Market context:** a niche tool built to expand. Competitive constructed MTG alone is a modest market (rough model: 30k free users at 4–5% conversion ≈ $75–90k ARR), but incumbent traffic (mtgdecks.net) proves strong demand for this data; multi-TCG expansion is what raises the ceiling.

**Pricing:** single premium tier. $5.99/month, $47.99/year (~33% annual discount — annual smooths between-set churn lulls). Competitor anchors at decision time: untapped.gg Premium $7.99/mo, MTGGoldfish Premium ~$6/mo. Launch-cohort “founding member” annual deal (~$39/yr, price-locked) to seed the paid base and feature-usage data. No multi-tier pricing until thousands of subscribers exist.

**Conversion mechanics:** 7-day free trial; monthly + annual only at launch. Conversion pressure is *moment-based* (Thursday before an RCQ weekend → “My Deck vs projected meta”), so surface upgrade prompts contextually, not as nag walls. Fast-follow if trial conversion is weak: contextual “weekend pass” one-off purchase (~$2.99).

**Payment channels (Phase 2 architectural input):** web-first subscriptions via Stripe (~3% fees) as the primary channel; app-store IAP (15–30% platform cut) offered as the convenience path. Since the 2025 US rulings, apps may link out to web payment — do so. This is an additional argument for shipping the web app before the mobile app: it validates the product and is the high-margin payment rail.

**Ads (later, web free tier):** light, non-overbearing ad monetization on the free web experience is acceptable once traffic justifies it — never interstitials or anything degrading the core data views, and never in the paid tier. Not a launch concern; note it so the web app’s layout reserves sane placement.

**Day-one metrics to instrument:** trial-start rate, trial→paid conversion (target >30%), monthly churn (target <7%), feature-level usage among payers.

## 10. Risks

1. **WotC/Daybreak data policy.** They attempted to restrict decklist publication in Feb 2026 and reversed under pressure. Mitigations: raw archives (history is ours forever), Melee/TopDeck paper pipelines, partnership outreach early.
1. **Melee scraper fragility.** Their site broke third-party scrapers in March 2025. Treat Melee ingestion as best-effort until a partnership exists; never let its failure block the MTGO pipeline.
1. **Archetype label drift.** Mitigated by classifier_version on every label and cheap full relabeling.
1. **Persistence baseline may win (Layer 3).** Acceptable outcome — the product degrades gracefully to descriptive trends; marketing claims follow the validation reports, never precede them.
1. **17Lands / Moxfield licensing (backlog items).** Both require explicit permission checks before commercial use. Do not build on assumptions.

## 11. Instructions to Claude Code

- Start at M0. Work milestone by milestone; do not skip ahead to the API or app.
- Every validation run writes a dated report into `validation/reports/` and it gets committed. Metrics in reports are the source of truth for go/no-go decisions.
- Keep scrapers polite: custom UA, ≤1 req/sec per host, exponential backoff, cache everything, never re-fetch archived events.
- Config over code for formats: adding Pioneer later should mean adding rule files and a config entry, not new modules.
- Enforce game-neutrality of the model stack (§4.1 rule 2): `models/`, `jobs/`, and `api/` must not import MTG-specific code or reference game-specific IDs; add a CI import check for this from M0.
- All migrations additive-only per §4.3; every deliberate exception gets a written expand–migrate–contract plan.
- Route all premium gating through the single entitlements module from the first gated endpoint; never inline tier checks.
- Fixed random seeds everywhere; validation suites must be exactly reproducible.
- When a target in §5 is missed, do not silently lower it — write the analysis, propose the adjustment, and surface it to the owner.