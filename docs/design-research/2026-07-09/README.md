# MetaSurf Wave-2 Design Report — Pit-Wall Console, Full Product Surface

**Date:** 2026-07-10 (covering the 2026-07-09 wave-2 run)
**Audience:** MetaSurf owner
**Base direction:** Pit-Wall Console (chosen in the [wave-1 report](../2026-07-08/README.md), 2026-07-08). Wave 2 extracted the winning direction into a formal token spec, extended it to multi-game, and built 10 new page mockups against real grounding data.
**Browse everything:** open [index.html](index.html) — a gallery linking every wave-2 mockup plus the four v3 base screens.

---

## 1. What wave 2 covers

Wave 2 produced **two specs** and **10 page mockups**, all in this directory:

| Artifact | File |
|---|---|
| Design tokens & component spec (v3, extracted from the revised wave-1 screens) | [pit-wall-tokens.md](pit-wall-tokens.md) |
| Design-language extension spec (multi-game + wave-2 pages, S4–S13) | [extension-spec.md](extension-spec.md) |
| 4 base screens re-cut as v3 | [pit-wall-console/](pit-wall-console/) (s1 meta snapshot, s2 matchup matrix, s3 archetype detail, deck viewer) |

**Coverage vs the extension spec's own page plan (§6, S4–S13)** — honest mapping, because the build diverged from the plan in places:

| Spec slot | Built as | Status |
|---|---|---|
| S4 Game Console Home | [home-game-switcher.html](home-game-switcher.html) | built as spec'd |
| S5 One Piece Meta Snapshot | — (nearest: [op-matchup-matrix.html](op-matchup-matrix.html)) | **not built as spec'd**; the OP matrix covers the matchup surface, not the timing tower |
| S6 One Piece Leader Detail | — (nearest: [op-deck-viewer.html](op-deck-viewer.html)) | **not built as spec'd**; deck viewer covers list-level detail, not the leader page |
| S7 One Piece Event Page | [events-browser.html](events-browser.html) | built broader — a multi-game events browser rather than a single event page |
| S8 Riftbound Legend Index | — | **not built** |
| S9 Riftbound Catalogue Browser | — | **not built** (Riftbound appears only as tiles on S4 and the events browser) |
| S10 Emerging Scanner | [emerging-feed.html](emerging-feed.html) | built as spec'd |
| S11 Movers Board | [card-trends.html](card-trends.html) | built as spec'd |
| S12 Archetype Cluster Map | [deck-map.html](deck-map.html) | built as spec'd |
| S13 Meta-Share Forecast | [meta-forecast.html](meta-forecast.html) | built as spec'd |
| (not in spec plan) | [best-decks.html](best-decks.html), [deck-classify.html](deck-classify.html) | additional builds: winners feed and the classify-console (the classify endpoint exists in the API grounding) |

So: 10 pages built, 8 of the 10 spec slots covered directly or by a near neighbor, **two genuinely missing surfaces (both Riftbound: legend index, catalogue browser)**, and two extra pages the spec didn't plan. The Riftbound pages are the cheapest remaining builds — the grounding (36 legends, 1,064-card catalogue, deck shape) is already mined and sitting in [riftbound-games-ground.json](riftbound-games-ground.json).

Every page went through a critique → revision → in-browser verification loop (headless Chromium at 390×844 and 1440×900, console-clean, no horizontal overflow — each file's revision notes state exactly what was verified).

---

## 2. The 10 pages

Scores are the critique's five dimensions, 0–10: **SYS** system consistency · **HON** data honesty · **LEG** legibility · **MOB** mobile-390px · **FIT** persona fit. Every page was revised against its critique before these notes; "remaining weaknesses" below are what is *still* true after revision — deliberate skips, grounding limits, and flags for you — not the already-fixed critique list.

### 2.1 Game Console Home — [home-game-switcher.html](home-game-switcher.html)
The S4 hub: three equal press-tiles (MTG / One Piece / Riftbound) in the console idiom, each carrying its livery keel, wordmark, data-maturity chip (`FULL TELEMETRY` / `LIMITED SAMPLE` / `CATALOGUE ONLY — NO MATCH DATA`), per-game DSEG headline counts, bright/dim format chips keyed to ingestion status, and a wire ticker. Whole-tile press targets, roll-ups that survive background-tab loading, canonical MTG pip fills per tokens §1.4.

**SYS 8 · HON 9 · LEG 9 · MOB 9 · FIT 9**

Remaining weaknesses:
- The tokens-§1.4-vs-extension-spec-§1.4 wording conflict on MTG pip fills was resolved **in-page by the documented precedence rule** (tokens canon wins) rather than stopped-and-asked — review the call.
- "LARGEST OBSERVED" field stat is scoped honestly, but the majors corpus behind it is shallow (coverage starts Dec 2025).
- Stat-cell DSEG runs 24px vs the §5.3 30px reference — a documented, deliberate drift (30px clips "14 404" in 3-across tiles).

### 2.2 Emerging Scanner — [emerging-feed.html](emerging-feed.html)
The S10 discovery feed: T3 unnamed-cluster rows in full (dashed frames, `EMERGING` tags, provisional descriptors at `--provisional` weight, `AUTO-CLUSTERED · n · FIRST SEEN` chips, signature-card lift lines), tier-ladder chips with the promotion rule printed on them, WR readouts with render-time CIs, and a V-FEED veil over the locked tail with server-side-masked payloads mirrored faithfully (locked rows carry no true values, even in aria-labels).

**SYS 9 · HON 8 · LEG 8 · MOB 9 · FIT 9**

Remaining weaknesses:
- **Open spec conflict, flagged in-page for you:** extension-spec §5/§6 says first 3 rows free; the page brief said 1 teaser row. The page ships 1 and quotes both clauses in its honesty ledger. Needs your call.
- Two fields (`events` count, prior-7d baseline) are **proposed API extensions, not in the grounded emerging shape** — declared in four places on the page, but they don't exist server-side yet.
- All winrates placeholder (page-level caveat covers it); micro type-size drifts documented as defensible.

### 2.3 One Piece Matchup Matrix — [op-matchup-matrix.html](op-matchup-matrix.html)
A 13-leader matrix computed from **real data**: 889 decided matches recounted this session from the raw play.limitlesstcg.com archive (12 online events, 2026-07-01→08), leader colors joined from the punk-records catalogue, Wilson CIs in the drilldown. Split-octagon OP pips, T2 structural naming, an online/offline mode toggle where offline mode degrades honestly (`SHARE-ONLY FEED — NO PAIRINGS PUBLISHED`, unlit readouts), and the §4.2 provenance microline in canonical form.

**SYS 9 · HON 9 · LEG 7 · MOB 9 · FIT 9**

Remaining weaknesses:
- **849 vs 889:** your brief said 849 online matches; this session's recount of the same archive returned 889 decided matches. The computed figure is shown; the discrepancy is flagged in the footer and header comment. Needs reconciling.
- Every lit cell is below the N<50 low-sample standard (max cell N=32, floor=5) — echoed in the matrix note, but raising the floor is your data call, deliberately not taken by the design side.
- `.caveat` stays `inline-block` vs the spec's `inline-flex` — deliberate skip with documented wrap rationale.

### 2.4 One Piece Deck Viewer — [op-deck-viewer.html](op-deck-viewer.html)
Real Bielefeld top-cut lists (leader + exactly 50 main, every card resolved to catalogue name/colors/cost), deck switcher, USD/EUR toggle whose totals match the source-printed totals, top-cut field panel with canonical provenance line, and — because no card images exist in local grounding — a complete color-framed placeholder system with graceful `onerror` degradation on every image slot. Livery confined to the sanctioned 4px grainband.

**SYS 8 · HON 10 · LEG 8 · MOB 8 · FIT 9**

Remaining weaknesses:
- The `/decks/list/6509` deep link rests on the task's citation of the t431 saved capture, which is **not present in this worktree** — not independently re-verified.
- No card images anywhere by policy (Bandai hosts are remote, no ToS decision recorded) — the page is honest about it, but visually it is placeholder-frames-only until you make an image call.

### 2.5 Events Browser — [events-browser.html](events-browser.html)
Multi-game event feed: real event rows with official player counts (Bielefeld 1,541 down to World Finals 34), min-field filter that discloses when it hides unknown-size leagues, podium panels that honestly label their scope (`FINISHES ON FILE` when grounding only carries archetype-limited finishes), maturity chips per game, `NOT CAPTURED` chips for gaps instead of fabricated placings. A real double-render race bug in the stat-tile roll-up was found and fixed during verification.

**SYS 8 · HON 9 · LEG 7 · MOB 8 · FIT 8**

Remaining weaknesses:
- MTG podiums are Murktide-only — a grounding constraint, documented in-page as such; production podiums need full standings.
- MTG switcher tile stays unliveried because no MTG accent hue exists in grounding (deliberate, commented).
- Deliberate keeps you may want to review: WIRE badge on purple (`--acc`, tokens §5.1 chrome), LEAGUE 5-0 badge on `--win`.

### 2.6 Best Decks / Winners Feed — [best-decks.html](best-decks.html)
Winner-per-event ledger built from the real One Piece tournaments fixture: **all 25 listed events, every winner named** (re-parsed this session; 7 rows carry archetype labels from the source, and the page says exactly which). Deck spotlights (Purple Enel; MTG lists with pip percentages recomputed on a stated mainboard basis), PRO veil over the feed tail, reparenting rail at wide, canonical §3 caveat strings.

**SYS 8 · HON 7 · LEG 8 · MOB 7 · FIT 9**

Remaining weaknesses:
- Deck labels exist for only 2 of 25 events in grounding — the page's biggest honest hole; rows carry `DECK LABEL NOT CAPTURED` chips.
- 29+-character event names still ellipsize at 390px against the full column width (legitimate overflow, not chip squeeze).
- Housekeeping: a temporary `best-decks-verify` launch config was left in `.claude/launch.json`.
- Free-tier shows 6 crisp rows vs the spec's 3 — cited in-page as a deviation; same owner call as the emerging feed.

### 2.7 Card Trends / Movers — [card-trends.html](card-trends.html)
The S11 copies-per-week ledger: risers/fallers boards, 1W/4W window toggle, per-card drilldown with sparkline, and a tech tab whose adoption counts were recomputed against the real archetype-page data this session (the one miscount the critique caught was fixed by re-derivation, not adjustment). Purple confined to the single top-lift row; N column earns the wide layout its width.

**SYS 8 · HON 8 · LEG 8 · MOB 8 · FIT 9**

Remaining weaknesses:
- All trend *series* are placeholder (labeled per-row and in the floorkey); only the adoption counts are computed from real lists.
- 1 free teaser row vs spec's 3 — documented deviation, same owner reconcile as §2.2.
- Deferred roll-ups render "0" until scrolled into view — intended IntersectionObserver behavior, but worth knowing when screenshotting.

### 2.8 Deck Classify Console — [deck-classify.html](deck-classify.html)
The classify endpoint as a terminal: paste a list, get T1 (rule-file) or T3 (cluster) classification with confidence band, alternatives, unresolved-card reporting verbatim (`Lightnig Bolt` stays misspelled — never corrected from memory), FREE→403→PRO round trip, and a veiled "spread this result seeds" preview. Score ties render honestly — shared rank, A–Z, explicitly labeled "no card-level ranking computed" — because grounding has no card-level data for tie-breaking and the page refuses to invent a term.

**SYS 9 · HON 9 · LEG 8 · MOB 9 · FIT 9**

Remaining weaknesses:
- EXP WR is computed at render but from **placeholder winrates** — labeled in three places, still not a real number.
- Tie-breaking beyond alphabetical needs real card-overlap data; the honest tie rendering is a stopgap, not the end state.
- The verification harness couldn't fire real window-resize events; the wide reparent was exercised manually (CSS media query verified independently).

### 2.9 Archetype Cluster Map — [deck-map.html](deck-map.html)
The S12 map: canvas point field with curated hulls, emerging clusters as dashed-halo T3 marks, timing-tower rail, tooltip with noise-floor guards (below-N clusters read `--.-` instead of a winrate), drag-latch touch model so the map never hijacks page scroll, bottom sheet with full modal contract, anti-over-reading caption, and a `LAYOUT COMPILED` stamp.

**SYS 8 · HON 7 · LEG 8 · MOB 7 · FIT 9**

Remaining weaknesses:
- The 10 hull names are namesake picks labeled `CURATED (PORT PENDING)` — **the MTGOFormatData rule files are not on disk**; this is the standing owner flag, not resolved.
- Point geometry and the noise count are synthetic demo data, now labeled `SYNTHETIC` on both tiles — the real HDBSCAN layout pipeline is unbuilt.
- The coarse-pointer 44px label rule is present in CSS but unverifiable headlessly; check once on a real phone.
- A fabricated `TOPDECK.GG` attribution was removed during revision (no topdeck rows feed the page) — noting it here because it is exactly the failure class this project polices.

### 2.10 Meta-Share Forecast — [meta-forecast.html](meta-forecast.html)
The S13 module: stepped hard-edged fan chart with band-edge strokes measured to clear WCAG 3:1, FC/DT mode switch whose ticker never says "PROJ" in observed-data mode, FAN/CDF toggle gated per-archetype on sample size, low-N archetypes swapping bands for event-tick strips, PRO resolution gate, and a listbox-semantic trend board.

**SYS 8 · HON 8 · LEG 8 · MOB 8 · FIT 9**

Remaining weaknesses:
- **Flagged trade-off:** lightening `--band90` for band-vs-plate contrast dropped 50%-vs-90% *fill* contrast to 1.19:1 — the distinction is now carried entirely by the boundary stroke (WCAG-acceptable mechanism, explicitly offered by the critique). If you want fill-level distinction too, the only lever left is a hatch pattern on the 90% steps.
- All forecast numbers are placeholder — no forecasting model exists yet (M3 territory); the page's honesty chrome is real, its bands are not.
- S13's right-edge DSEG band labels were relocated below the plate at phone widths — recorded as a spec deviation in the header comment.

---

## 3. Owner-decision items the extension spec resolved by design lead

Three calls you had open were made in [extension-spec.md](extension-spec.md) so wave 2 could build. Each is reversible; the alternative is stated. (§7 of the spec lists five further items deliberately *not* decided — livery hues, the `shortLabel` registry extension, K-vs-2-char, top-cut share semantics, same-name leader merging.)

**1. Pip / swatch system (spec §1).**
**Decision:** one proprietary chip grammar for all games — flat hue field, 1px rim, optional letter, hard shadow — with a per-game *silhouette*: MTG keeps its circles, One Piece gets cut-corner octagons (duals = one 50/50 split octagon, the pair is the atom), Riftbound gets fused rectangular plates carrying 2-char domain codes (`BO CA CH FU MI OR`). One Piece letters are `R G B P K Y`, with **K** for Black (CMYK key-plate convention) to break the Black/Blue collision. No official mana/color/domain glyphs anywhere, ever — WotC Fan Content Policy restricts them and a paid product can't shelter under it; the same posture applies to Bandai symbols and Riot icons.
**Alternative:** 2-char One Piece codes (`RD GN BU PU BK YW`) if K reads too print-nerd — costs 6px per chip. Also on file: separate dots per color instead of split octagons (rejected: the community tracks the pair as the unit, per Lorcana convention and the observed "Red/Black Koby" source labels).

**2. Archetype naming tiers (spec §2).**
**Decision:** three visual registers encoding *how the name was produced*: **T1 CURATED** (rule-file names — full weight, art tile, CODE badge; the reference register nothing else may imitate), **T2 STRUCTURAL** (card-is-name: OP leaders, Riftbound legends — full weight because the name is a real product name, distinguished by a `LEADER`/`LEGEND` axis chip and a dim set-id), **T3 UNNAMED/EMERGING** (machine clusters — dashed frame, reduced-contrast mono descriptor, persistent `AUTO-CLUSTERED · n · FIRST SEEN` telemetry chip, never an art tile or display face; graduates to T1 with a one-shot glitch when a rule file lands).
**Alternative:** the rejected path was dimming T2 names like provisional content — rejected because "Purple Enel" is a real permanent name, not editorial guesswork; and conversely, ever letting T3 borrow T1 styling (including for marketing screenshots) is banned outright.

**3. Degradation chrome (spec §3).**
**Decision:** a single `.caveat` component — 9px dim mono, orange keel, load-bearing numbers in ink — with a **canonical message catalog** (`SHARE-ONLY FEED…`, `LOW SAMPLE · N=12 / FLOOR 40`, `ONLINE POPULATION ONLY · N=…`, `TOP-CUT SHARE — TOP 64 PUBLISHED OF 1,541 ENTRIES`, `NO MATCH DATA FEED — CATALOGUE ONLY`). Placement rules fixed (page-level once + short module echoes, max two chips per module); layout never collapses in a degraded state, readouts go unlit `--.-` instead of vanishing.
**Alternative:** bespoke per-condition widgets/empty-states (the NN/G-style per-widget approach) — rejected so every data-quality condition is the *same species of furniture* and new conditions are a string, not a design project.

---

## 4. Grounding provenance — what's real, what's placeholder

### Real, mined from the `multi-tcg-wave1` repo (and this worktree's raw archives)

- **Per-game UI registry** — pip palettes, pip orders, colorless codes, type-group orders for all three games, copied verbatim from `web/lib/games/*.ts` into [riftbound-games-ground.json](riftbound-games-ground.json), plus API shapes (`/v1/games`, classify request/response with its 501-for-non-MTG behavior, emerging cluster shape, required-attribution credits) from `api/routes.py` / `api/schemas.py`, and deck shapes from `config/formats.json`.
- **Riftbound catalogue** — 1,064-card Riftcodex capture: all 8 sets, all 36 base legends (every one exactly 2 domains), 6 runes, battlefields (all 57 Colorless), attribute semantics.
- **One Piece meta** — 13 real archetype labels over 1,054 decks in 37 cached events (0 unresolved leaders); 3 full winning decklists (every card resolved); 13 event rows with official player counts scraped from cached raw HTML; a real-but-sparse matchup matrix from the online archive (51 of 78 top-13 cells have real N and Wilson CIs).
- **MTG** — archetype visuals, archetype-page card data, and deck-viewer lists in [s1-archetype-visuals.json](s1-archetype-visuals.json), [archetype-page-data.json](archetype-page-data.json), [deck-viewer-data.json](deck-viewer-data.json); the best-decks and card-trends pages recomputed their pip percentages and adoption counts from these files this session.

### Placeholder (always labeled on-page)

All MTG/emerging winrates and CIs' underlying values, all card-trend time series, all forecast bands and CDFs, the cluster-map point geometry and noise count, the 27 unpopulated OP matrix cells, and every Riftbound performance number (zero Riftbound match data exists anywhere — `import:false`).

### Gaps the grounding agents reported (their words, condensed)

- No live DB archetype ids; no rollup snapshots.
- OP matchups come from **one week of online events only**; offline events publish no pairings, so offline winrates are structurally unavailable (this is why share-only mode exists as chrome).
- Offline majors publish Top-64 only → denominators are top-cut share, not field share (owner decision §7.4 still open).
- No local card images for any game. One Piece images exist only on Bandai's remote hosts (no ToS decision recorded); **Riftbound images are Riot CDN and must never be hotlinked** (owner ToS decision). Hence the color-framed placeholder system everywhere.
- `play.limitlesstcg` details carry `format=null` — "OP16 window" labels are editorial derivations, disclosed on-page.
- Riftbound palette hues are provisional project choices; Riftcodex has no legality field and no license statement on file.

### Discrepancies to know about

- The OP grounding agent wrote `onepiece-ground.json` to the session scratchpad rather than this directory, so the extension spec (which noted its absence) sourced OP registry values from `riftbound-games-ground.json`'s shared registry instead, and the OP pages inline data recomputed directly from `data/onepiece-raw/`. The file has now been recovered into this directory as [onepiece-ground.json](onepiece-ground.json) (validated JSON: registry, top-13 archetypes with provenance, colors, decklists, events).
- **849 vs 889 online matches:** the brief's figure vs this session's recount of the same archive. Flagged on the matrix page; unresolved.

---

## 5. Research sources

Wave 2's new research (the extension spec cites each at point of use):

- **Multi-game architecture:** untapped.gg hub-and-spoke + companion surfaces (untapped.gg/en, /en/installed); op.gg maturity badges (op.gg); melee.gg game-as-enum floor (melee.gg/Home/About); TeamColors token dataset (teamcolors.jim-nielsen.com).
- **Pips & identity coding:** Lorcana ink shape+hue dual coding (wiki.mushureport.com/wiki/Ink); inkdecks.com Lorcana meta pair-as-atom convention; F1 TV team-color bar + 3-letter codes (mattbirkett.co.uk); WotC Fan Content Policy (company.wizards.com/en/legal/fancontentpolicy); Mana font copyright status (mana.andrewgioia.com).
- **Provenance-as-weight / AI labeling:** iA Writer greyed-AI-text pattern via shapeof.ai/patterns/disclosure; IBM Carbon AI label (carbondesignsystem.com); trust-caveat study PMC12166545.
- **Honest degradation:** NN/G empty-states pattern (nngroup.com); Google Trends' refusal to print unstable values (support.google.com/trends/answer/4365533).
- **Trust chrome & markets:** Kalshi/prediction-market patterns (avark.agency); Polymarket volume-under-every-market; Metaculus resolution criteria + depth-on-demand (metaculus.com/faq).
- **Feeds & thresholds:** MTGGoldfish Movers (mtggoldfish.com/movers); untapped.gg 500+-game floors (mtga.untapped.gg); Google Trends Rising/Top/Breakout; ThoughtWorks Radar rings (thoughtworks.com/radar).
- **Maps & density:** Nomic Atlas data-map captions (docs.nomic.ai); Map of GitHub precomputed tiles + mobile model (anvaka.org); Scott Logic million-point renderer benchmarks (blog.scottlogic.com).
- **Uncertainty display:** Bank of England fan charts (visualizing.org/fan-chart); hurricane cone-of-uncertainty misreading literature (WCAS-D-21-0173); paywall "see just enough" (ui-patterns.com/patterns/Paywall).

The wave-1 technique library (~50 sources: DSEG, F1 timing towers, riso/dither canon, terminal-brand chrome, reduced-motion architecture, etc.) is in the [2026-07-08 report's appendix](../2026-07-08/README.md) and still applies — the token spec is built on it.

---

## 6. Next steps

**Wire to the real API first (in this order):**

1. **[op-matchup-matrix.html](op-matchup-matrix.html)** — the `MatchupsResponse` shape (p_a_beats_b / ci_lo / ci_hi / n_matches) already exists in the API grounding and the page's data is already real; this is the shortest path to a true end-to-end screen. Resolve 849-vs-889 while wiring.
2. **[events-browser.html](events-browser.html) + [best-decks.html](best-decks.html)** — events, standings, and the required-attribution `credits` contract are all grounded; these exercise the attribution slot for real.
3. **[emerging-feed.html](emerging-feed.html)** — the endpoint shape exists; but first decide the two proposed API extensions (per-cluster event count, prior-7d baseline) — build them or strip the UI fields.
4. **[home-game-switcher.html](home-game-switcher.html)** — needs only per-game rollup counts.
5. Forecast, cluster map, and card-trend series wait on their models (M3 pipeline work) — their chrome is done, their numbers don't exist yet.

**Build next (design side):** the two missing Riftbound pages (S8 legend index, S9 catalogue browser) — grounding is fully mined, both are catalogue-only pages with no model dependency.

**Needs an owner call (consolidated):**

1. The five open items in extension-spec §7: livery accent hues; the `shortLabel` registry extension (shared-file seam change); OP Black K vs 2-char codes; top-cut share semantics; same-name leader merging.
2. **Free-teaser depth:** spec says 3 crisp rows, two pages shipped fewer per their briefs (emerging: 1, best-decks: 6) — pick one number and make the spec and pages agree.
3. **849 vs 889** OP online-match count.
4. Matrix noise floor (all lit cells N<50 — accept with the echo caveat, or raise the floor).
5. Card-image policy for One Piece (Bandai remote hosts — no ToS decision on file; everything currently ships color-framed placeholders).
6. Forecast 90%-band fill distinction (stroke-only today; hatch pattern is the remaining lever).
7. The in-page resolution of the tokens-vs-extension-spec MTG pip wording conflict (home switcher) — bless or overrule.
8. Housekeeping: remove the leftover `best-decks-verify` launch config (`onepiece-ground.json` has been recovered into this directory during report assembly).

---

*Every number in this report is either quoted from the per-page revision/verification notes (which state what was actually run and measured) or from the grounding agents' mining reports. Critique scores were issued during the wave-2 critique pass; the revision notes claim fixes verified in-browser afterward, so treat scores as floors.*
