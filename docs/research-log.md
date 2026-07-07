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
| M3.6-2 | Empirical tech finder | Does the field tech identifiable cards? | yes, r up to 0.70, text-coherent | 🔬 | same |
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
- **Tech is real, strong, and auto-discoverable.** Opposing sideboard
  inclusion correlates with a rising archetype's share at r up to 0.70, and
  the cards' oracle text names the reason.

## 3. Feature roadmap (mapped to plan §8 product screens)

| Feature | Screen | Depends on | Readiness |
|---|---|---|---|
| Meta snapshot: share + shrunk winrate ± CI | S1 | M2 ✅ | ready |
| **Matchup matrix** (calibrated, CI, sample size) | S2 | M2 ✅ | ready |
| **Best-positioned deck** ("best vs current meta") | S2/S6 | M2 + M3.5b 🔬 | needs pre-registered backtest |
| Macro strategy-type view ("aggro-control favored now") | S2 | M3.6-1 + card2vec | prototype → milestone |
| Archetype detail: share/winrate history | S3 | M2 ✅ | ready |
| Trends: contrarian "overextended, likely to recede" | S5 | M3.6-3 🔬 | honest framing ready |
| **Tech watch**: "field is teching {cards} vs X" | S5/S6 | M3.6-2 🔬 | needs lead-lag hardening |
| **Hidden-tech finder** (undiscovered cards by function) | S5/S6 | M6 (content cards) 📋 | proposed, §4 |
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

### 4b. Content-based hidden-tech finder (the owner's vision, harder)
Goal: flag cards that **few lists run yet** but that fit the historical
functional profile of good tech vs an archetype — e.g. "Consign to Memory is
good vs Eldrazi" inferred from *what the card does*, before the field adopts
it.

**Why co-occurrence embeddings alone can't do this:** card2vec learns a card
from the decks it appears in, so an *unplayed* card has no vector. To
generalise to undiscovered cards you need a **content representation** — the
card's function from `oracle_text` / `keywords` / `type_line` / `cmc` (we hold
all of these in the committed snapshot). This is exactly the "generalised card
representation" idea in the MTG ML literature (arXiv:2407.05879).

**Design:**
1. **Content features per card** — interpretable oracle-text signals
   (counters-spell, counters-ability, destroys-artifact, exiles-graveyard,
   board-sweep, mana-denial, hexproof/protection, "can't"-stax), plus cmc,
   colors, type, instant-speed. Optionally a learned text embedding later.
2. **Learn a tech profile per archetype** from history: the effective tech
   vs A is the M3.6-2 empirical set (cards whose opposing-sideboard inclusion
   tracks A's share). Fit "is-good-tech-vs-A" as a function of content
   features over those positives vs a staple-card baseline.
3. **Score every card** (including unplayed ones) by profile fit × inverse
   current play-rate → ranked **hidden-tech candidates**.
4. **Validation (falsifiable, pre-registered):** temporal backtest — for cards
   that were underplayed at time t and became established tech vs A by t+Δ,
   did the profile rank them highly *at t*, before adoption? Precision@k of
   early flags vs a play-count-momentum baseline. Report on withheld archetypes/
   periods.

**Feasibility evidence (measured this session):** the "counter target
activated or triggered ability" family — functionally near-identical cards —
spans the entire play-count range in our corpus: Consign to Memory 22,531
decks, Tishana's Tidebinder 9,025, Stern Scolding 16,514, Trickbind 168,
`Consign // Oblivion` 207, **Disruption Protocol 0**. A content representation
groups these by function where co-occurrence cannot; the underplayed members
are exactly the hidden-tech output. And the profile is real: for **Eldrazi**,
the top empirical tech (opposing-SB corr with Eldrazi share) is a coherent
"sweep small creatures + deny colorless mana + counter triggers" cluster —
Pyroclasm (r=0.69), **Consign to Memory (r=0.66)**, Harbinger of the Seas
(0.64), Whipflare, Into the Flood Maw, The Meathook Massacre — the owner's
exact example sitting at #2. (Reproduce: the Eldrazi query in this session /
`macro_tech_explore.py` generalised per-archetype.)

**Caveats / risks:** functional tags are not in Scryfall bulk (the Tagger
`otag:` project is separate, partial, licensing-unclear) — so features must be
mined from oracle text or learned; oracle-text mining is heuristic and needs
a fixture-tested rule set (CLAUDE.md parser discipline). The profile learned
from *adopted* tech may miss genuinely novel answers (survivorship) — the
backtest measures exactly this.

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

## 6. Reproduce everything

```
make rebuild                                   # corpus + labels + matches
python -m validation.v2_winrates               # M2 report
python -m validation.v3_evolution              # M3 report
python -m validation.v3_evolution.replicator_explore      # M3.5
python -m validation.v3_evolution.recommendation_explore  # M3.5b
python -m validation.v3_evolution.macro_tech_explore      # M3.6 (all 3 experiments)
```
