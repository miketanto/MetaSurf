# Metagame Platform — Research Log & Feature Roadmap

The running record of every model investigation, its result, and the feature
decisions that follow. Numbers here are summaries; the authoritative figures
live in the dated files under `validation/reports/` and the notes under
`docs/notes/`, each reproducible by its named command. Nothing in this log is
a number that wasn't printed by code that ran (CLAUDE.md rule 5).

**Status legend:** ✅ VALIDATED (met a pre-set gate) · ❌ REJECTED (missed its
target, honest verdict recorded) · 🔬 EXPLORATORY-POSITIVE (strong signal,
not yet a pre-registered gate) · 📋 PROPOSED (designed, not built).

## 1. Findings ledger

| # | Investigation | Question | Result | Status | Source |
|---|---|---|---|---|---|
| M1 | Archetype classifier | Recover archetype labels? | 0.9949 holdout agreement; both emergence events day-0 | ✅ | `validation/reports/m1-v1-archetypes.md` |
| M2 | Winrate model | Calibrated matchup winrates? | beats baseline 54/65 wks, slope 0.964, 90% coverage 0.884 | ✅ | `validation/reports/m2-v2-winrates.md` |
| M3.1 | Share forecast (Holt) | Predict next-week share? | +2.48% vs persistence (target +10%) | ❌ | `validation/reports/m3-v3-evolution.md` |
| M3.2 | Flocking hypothesis | Do players flock to winners? | γ significant but **negative** — field counter-adapts | ❌(hyp) | same |
| M3.3 | Tech-card drift (Holt) | Predict card copies? | −1.77% vs persistence | ❌ | same |
| M3.5 | Replicator share forecast | Does matchup-driven evolution predict share? | no — best η=0 (persistence); field too slow weekly | ❌ | `docs/notes/m35-replicator-proposal.md` |
| M3.5b | Deck recommender | Does a best-positioned deck win more? | **0.580 realized winrate, p<1e-6** | 🔬 | same |
| M3.6-1 | Macro structure (HodgeRank) | Is matchup "kind-beats-kind"? | **66.6% cyclic** vs 33.4% transitive | 🔬 | `docs/notes/m36-macrostrategy-tech-proposal.md` |
| M3.6-2 | Empirical tech finder | Does the field tech identifiable cards? | signal r≤0.70 but **CONFOUNDED** — see §4c | ⚠️ | same |
| M3.6-3 | Multi-week share | More predictable at longer horizons? | level sticky (ac 0.79–0.93), direction mean-reverts (~40%) | 🔬 | same |
| M6 | Content tech finder | Find *undiscovered* tech by function? | designed; feasibility strong (see §4) | 📋 | this doc |

## 2. Established empirical facts (the load-bearing numbers)

- **Match outcomes are near-coinflips but calibrated.** Model log-loss 0.682
  vs 0.693 chance; winrates cluster tightly (matchup spread ±0.059 off 50%).
  Winrate half-life tuned to **182 days** — winrates decay far slower than the
  plan's 14–21d guess.
- **The metagame is 2/3 rock-paper-scissors.** HodgeRank on the top-25
  archetype matchup matrix: 66.6% of structure is cyclic, 33.4% transitive.
- **Winrate persists; popularity mean-reverts.** As-of winrate ↔ realized
  next-weekend winrate r=0.37 (774 deck-weeks); a rising deck keeps rising
  only ~40% of the time.
- **A best-positioned deck wins ~58% of its real matches** (p<1e-6), mostly
  from deck-strength persistence plus a small positioning bonus.
- **Tech isolation is hard (correction — see §4c).** Share-correlation of
  opposing sideboard cards (M3.6-2) conflates true anti-A tech with cards
  that are merely good in the meta-state where A is popular (board wipes
  topped the list because A was a creature deck, not because they answer A).
  A matchup-conditioned difference-in-differences removes that confound but
  introduces a second one (archetype-identity: a combo deck's signature cards
  score high because the *deck* beats A). Clean tech isolation is an open
  problem here, not a shipped signal.

## 3. Feature roadmap (mapped to plan §8 product screens)

| Feature | Screen | Depends on | Readiness |
|---|---|---|---|
| Meta snapshot: share + shrunk winrate ± CI | S1 | M2 ✅ | ready |
| **Matchup matrix** (calibrated, CI, sample size) | S2 | M2 ✅ | ready |
| **Best-positioned deck** ("best vs current meta") | S2/S6 | M2 + M3.5b 🔬 | needs pre-registered backtest |
| Macro strategy-type view ("aggro-control favored now") | S2 | M3.6-1 + card2vec | prototype → milestone |
| Archetype detail: share/winrate history | S3 | M2 ✅ | ready |
| Trends: contrarian "overextended, likely to recede" | S5 | M3.6-3 🔬 | honest framing ready |
| **Tech watch**: "field is teching {cards} vs X" | S5/S6 | M3.6-2 ⚠️ | confounded — needs within-archetype design (§4c) |
| **Hidden-tech finder** (undiscovered cards by function) | S5/S6 | M6 (content cards) 📋 | proposed but gated on §4c; hardest item |
| Share *prediction* | — | — | ❌ do not ship; positioning is descriptive |

The through-line: **descriptive/analytic, not predictive** — every green item
above is a measurement or a best-response, none is a share forecast. That is
the verdict the numbers forced (M3) and it is a strong product on its own.

## 4. Proposed milestone — M6: card semantics & the tech finders

Two distinct features share one new substrate (a card-meaning layer). Keep
them separate; they have different data needs and difficulty.

### 4a. Empirical tech finder (near-ready, descriptive)
What M3.6-2 already does: surface cards **already being teched** against a
rising archetype, from opposing-sideboard co-movement. Ship-blocking work:
replace raw correlation with a **lead-lag / partial correlation** (control for
each card's own trend and shared seasonality), and a pre-registered backtest —
*when archetype A rises, does the flagged tech's inclusion rise the following
week, on withheld data?* Needs no card tags.

### 4b. BACKLOG — function-first tech finder (owner design)
Goal: flag cards — including ones **few lists run yet** — that fit the
historical functional profile of good tech vs an archetype, e.g. "Consign to
Memory is good vs Eldrazi" inferred from *what the card does*, before the
field adopts it. Owner's key design refinement: **build a layer of
"understanding" of what each card does FIRST, then correlate that
understanding with historical matchup data** — correlate *functions*, not raw
card presence. This is what makes the problem tractable and is the direct
answer to the §4c confounds.

**Why the function layer is the fix (not just a nicety).** §4c showed both
raw-card methods fail: share-correlation confounds with meta-state (board
wipes), matchup-DiD confounds with archetype identity (Storm signatures).
Abstracting cards to functions attacks both:
- **Pooling by function buys sample size** — one "counter target triggered
  ability" role aggregates Consign to Memory + Disallow + Voidslime + Tale's
  End + Tishana's Tidebinder + …, so the within-archetype / matchup-conditioned
  estimate the per-card version couldn't support becomes feasible.
- **Role-level A-specificity discounts generic answers** — a "board sweep"
  role helps vs *every* creature deck, so its effect-vs-A minus average-effect-
  vs-others is ~0; a "deny colorless / nonbasic mana" role helps specifically
  vs Eldrazi. The function layer makes generic-vs-specific measurable.
- **Restricting to interaction roles excludes identity noise** — Storm's
  graveyard-recursion / ritual roles are not "interaction", so they never
  enter the tech search; the archetype-identity confound is filtered by design.

**Pipeline:**
1. **Card-understanding layer** — assign each card a set of functional roles
   from `oracle_text` / `keywords` / `type_line` / `cmc` / `colors`
   (creature-removal, sweeper, artifact/enchant removal, graveyard-hate,
   counter-spell, counter-ability, hand-disruption, mana-denial, bounce,
   protection, taxation/stax, lifegain, …). Three build options, in
   increasing cost: (a) fixture-tested oracle-text rules (CLAUDE.md parser
   discipline; start here); (b) a learned text embedding (generalised card
   representation, arXiv:2407.05879); (c) licensed Scryfall Tagger `otag:`
   (best coverage, but separate project — licensing/coverage must clear
   first). Roles are game-neutral config, not code.
2. **Correlate function ↔ matchup, confound-controlled** — for each (role,
   archetype A) estimate the role's A-specific effect using the §4c
   *within-archetype, matchup-conditioned* design (does adding a card of this
   role to a deck of archetype X improve X's realized winrate vs A more than
   vs the field?), pooled across all cards carrying the role. Output: a small,
   interpretable "tech profile" per archetype = the roles that specifically
   beat it.
3. **Rank cards, including unplayed, by profile fit × inverse play-rate** →
   hidden-tech candidates, filtered to legal/castable colors and costs for the
   decks that face A. Card text explains each suggestion.
4. **Validation (falsifiable, pre-registered):** (i) role-level effect
   estimates hold out across archetypes/periods; (ii) temporal precision@k —
   for cards underplayed at t that became established tech vs A by t+Δ, did the
   profile rank them at t, beating a play-count-momentum baseline. Needs more
   sample than the frozen corpus gives per (role,A) cell → pairs naturally
   with **M4 live ingestion**.

**Feasibility evidence (measured this session):** the "counter target
activated or triggered ability" family — functionally near-identical cards —
spans the entire play-count range: Consign to Memory 22,531 decks, Stern
Scolding 16,514, Tishana's Tidebinder 9,025, Trickbind 168, `Consign //
Oblivion` 207, **Disruption Protocol 0**. A function layer groups these where
co-occurrence cannot; the underplayed members are exactly the hidden-tech
output. Consign to Memory being real Eldrazi tech is independently plausible
(it counters Eldrazi's ETB/cast triggers) — but note it is NOT proven by the
§4c probe, which is confounded; the function-first + within-archetype design
is what would prove it.

**Prerequisites / risks:** gated on §4c (within-archetype estimation) and
realistically on M4 (sample volume); the oracle-text role layer is itself a
fixture-tested parser with its own accuracy bar; Scryfall Tagger licensing is
unresolved. Highest-value but hardest and last of the tech items.

**Caveats / risks:** functional tags are not in Scryfall bulk (the Tagger
`otag:` project is separate, partial, licensing-unclear) — so features must be
mined from oracle text or learned; oracle-text mining is heuristic and needs
a fixture-tested rule set (CLAUDE.md parser discipline). The profile learned
from *adopted* tech may miss genuinely novel answers (survivorship) — the
backtest measures exactly this. **And it inherits the §4c confound**: the
"effective tech vs A" training labels must themselves be confound-free, so 4c
is a hard prerequisite for 4b.

### 4c. Why "tech" is genuinely hard to measure (owner correction, verified)
The owner flagged that sideboards are built against the *whole* field with
bias toward the top decks, so a card correlating with archetype A's *share*
need not be anti-A tech. Verified on Eldrazi:
- **Naive share-correlation** (M3.6-2) top hits were board wipes — Pyroclasm
  (r=0.69), Whipflare, Wrath of the Skies — generic small-creature answers,
  good because Eldrazi is *a* creature deck, not because they target Eldrazi.
- **Matchup-conditioned difference-in-differences** (does C improve the A
  matchup *more than* it improves other matchups; 9,551 vs-Eldrazi deck-match
  rows, global WR vs Eldrazi 0.504) removes the board wipes entirely — but the
  new top list is polluted by **archetype-identity** cards: Storm signatures
  (Past in Flames, Galvanic Relay, Empty the Warrens, Exquisite Firecraft)
  score high because Ruby Storm structurally beats Eldrazi, not because those
  cards are tech. Plausible real tech does surface (Aether Spellbomb DiD
  +0.224 WRvsA 0.717; Hurkyl's Recall; Bloodchief's Thirst) but mixed with the
  identity noise.
- **Conclusion:** neither method isolates tech cleanly. The honest design is
  **within-archetype**: among decks of the *same* base archetype, does adding
  C to the 75 improve their A matchup differentially? That controls both
  confounds but is sample-hungry. The ideal data — which cards are *brought in*
  for the A matchup — is sideboarding data the cache does not contain. Tech
  isolation is therefore a real research milestone (needs within-archetype
  design + more/live data, or a new sideboard-plan source), not a near-term
  ship. Reproduce: matchup-DiD probe in this session's transcript.

## 5. How this maps to the plan's milestones

M0–M2 are the plan's committed milestones (schema, classifier, winrates), all
green. M3 (evolution) returned the honest **descriptive-trends** verdict per
plan §7. The M3.5 / M3.6 investigations are research *beyond* M3 that the owner
directed; their product-bearing outputs (best-positioned deck, tech watch,
strategy-type view, hidden-tech finder) are proposed as **M6 — Insight
features**, to be built with pre-registered backtests after the Read API (M5)
exists to serve them. This document is the milestone record for that research;
each new investigation appends a ledger row and, if it produces a shippable
signal, a roadmap entry.

## 6. Backlog register

Ideas parked deliberately (plan §2 style: don't build yet, don't architect
out). Each has a designed path and a gating dependency.

| Item | What | Design | Gated on | Priority |
|---|---|---|---|---|
| **BL-1 Function-first tech finder** | Understand what each card *does*, then correlate function (not raw card) with matchup history to find real + hidden tech | §4b | §4c within-archetype estimation + M4 live data + oracle-text role layer | high value / hard |
| BL-2 Empirical tech-watch (descriptive) | Surface cards the field is teching into vs a rising deck | §4a | lead-lag hardening; still shows §4c confound — label as "co-moving", not "counters" | medium |
| BL-3 Macro strategy-type view | Cluster archetypes to strategy axes; type-level RPS | §4 / M3.6-1 + card2vec | card2vec build | medium |
| BL-4 Contrarian trend flag | "Overextended, likely to recede" | M3.6-3 | forward test (M4) | low, near-ready |

BL-1 is the owner's function-first tech finder. Its correctness rests on doing
the card-understanding layer *before* correlating — that is what turns the
confounded raw-card signal (§4c) into a poolable, generic-vs-specific,
identity-filtered function signal. Build order within BL-1: (1) oracle-text
role layer with fixtures → (2) role×archetype within-archetype matchup effects
→ (3) unplayed-card ranking → (4) pre-registered temporal precision@k, ideally
on live data.

## 7. Reproduce everything

```
make rebuild                                   # corpus + labels + matches
python -m validation.v2_winrates               # M2 report
python -m validation.v3_evolution              # M3 report
python -m validation.v3_evolution.replicator_explore      # M3.5
python -m validation.v3_evolution.recommendation_explore  # M3.5b
python -m validation.v3_evolution.macro_tech_explore      # M3.6 (all 3 experiments)
```
