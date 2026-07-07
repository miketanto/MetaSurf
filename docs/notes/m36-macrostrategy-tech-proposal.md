# M3.6 investigation — macro strategy structure, tech cards, multi-week share

**Status: exploratory, strong positive results on both of the owner's ideas.**
All numbers are printed output of
`python -m validation.v3_evolution.macro_tech_explore` (2026-07-07);
reproduce with that module. These are descriptive analyses (structure +
correlation), not predictive acceptance gates — framed as such below.

## The three questions

1. **Multi-week share** — is share more tractable at longer horizons?
2. **Macro "kind beats kind"** — is there systematic strategy-type structure
   in matchups (aggro-control beats all-in combo), separate from raw strength?
3. **Tech cards** — can we model "what's good tech" given a meta (affinity
   meta → artifact hate)?

## Literature (external, cited — not independently reproduced)

- **Card/deck embeddings are precedented and text-free.** *card2vec*
  (afreefaw, GitHub) learns MTG card vectors purely from decklist
  co-occurrence — no colour, cost, or text — and recovers meaningful card
  similarity; Hearthstone work does the same from text embeddings. So "an
  embedding/understanding of cards and tech" is a known, buildable object.
- **Matchup structure decomposes into transitive + cyclic.** HodgeRank /
  combinatorial Hodge theory (Jiang, Lim, Yao, Ye, *Math. Programming* 2011,
  arXiv:0811.1067) orthogonally splits a pairwise-comparison flow into a
  *gradient* (a global power ranking) and a *cyclic* residual (rock-paper-
  scissors). This is the exact tool for goal 2, and pairs with the
  spinning-tops / α-Rank results already cited in `m35-`.
- **Scryfall bulk has NO functional tags.** The committed oracle-cards
  snapshot carries `type_line`, `oracle_text`, `keywords`, `colors`, `cmc` —
  but not "removal / counterspell / artifact-hate". Those live in the
  separate crowd-sourced **Scryfall Tagger** (`otag:`) project, which is not
  in the bulk file and has coverage + commercial-use questions. Two clean
  routes avoid it: mine `oracle_text`, or **discover tech empirically** (below)
  and use text only to *explain* it.

## Experiment 1 — macro strategy structure is real and dominant (goal 2)

HodgeRank on the top-25 archetypes' Layer-2 matchup matrix (log-odds space,
weighted by pair match count):

| component | share of matchup "energy" |
|---|---|
| TRANSITIVE (a global power ranking) | **33.4%** |
| CYCLIC (kind-beats-kind / rock-paper-scissors) | **66.6%** |

**Two-thirds of matchup structure is NOT explained by "which deck is
better" — it is type-interaction.** The transitive ranking is still
meaningful (top: Nadu, GrindingBreach, Belcher, Energy; bottom: Mill, Aggro,
GenericTron), but it is the minority of the signal. The strongest cyclic
triangles are concrete and sensible, e.g. `Energy → Merfolk → Titan → Energy`
and `Titan → HammerTime → Belcher → Titan`. This directly supports the owner's
premise: macro strategy-type reasoning ("aggro-control beats all-in combo") is
capturing the dominant 2/3 of what determines a matchup.

*Caveat:* some cyclic energy is estimation noise in thin pairs (mitigated by
match-count weighting; the top triangles all have >30 matches per edge). A
clean version would fit strategy-axis labels and report cyclic energy after
denoising.

## Experiment 2 — tech cards are real AND auto-discoverable (goal 3)

For each top archetype A, correlate A's weekly share with each card's weekly
**sideboard-inclusion rate among decks that are NOT A** (the field teching
*against* A). Top hits, discovered with zero pre-tagging, then explained by
`oracle_text`:

**vs GenericTron** (big colorless ramp):
- `Ceremonious Rejection` r=+0.70 — *"Counter target colorless spell."*
- `Disdainful Stroke` r=+0.66 — *"Counter target spell with mana value 4 or greater."*
- `Grafdigger's Cage`, `Anger of the Gods` …

**vs GenericMidrange** (artifact-heavy):
- `Ancient Grudge` r=+0.49 — *"Destroy target artifact."*
- `Destructive Revelry` — *"Destroy target artifact or enchantment."*
- `Seal of Primordium` — *"…Destroy target artifact or enchantment."*
- `Spellskite`, `Crumble to Dust` …

**vs Titan** (Amulet land-ramp):
- `Ashiok, Dream Render` — *"…opponents can't search their library"* (hoses fetch/tutor)
- `Veil of Summer`, `Mystical Dispute`, `Blast Zone` …

**vs Aggro**: `Flusterstorm`, `Sanctifier en-Vec` (*graveyard + protection from
black/red*), `Hushbringer` …

This is the owner's exact hypothesis, confirmed and then some: when a deck
rises, the field packs identifiable hate, and **the card text names why**
("counter colorless" ↔ Tron; "destroy artifact" ↔ the artifact midrange
bucket). The signal is strong (r up to 0.70) and, crucially, **discovered from
co-movement alone** — we never told the model what any card does. Text is the
*explanation* layer, not a prerequisite.

*Caveat:* contemporaneous correlation, not causation; a lead-lag / partial-
correlation version (controlling for the card's own trend and shared
seasonality) is the proper next step before shipping a "recommended tech"
number. `GenericMidrange`/`GenericTron` are fallback buckets, but the tech
found against them is coherent.

## Experiment 3 — multi-week share: persistent level, mean-reverting direction (goal 1)

| horizon | share autocorr(t, t+h) | trend-continues accuracy | n |
|---|---|---|---|
| 1 wk | 0.926 | 38.6% | 3267 |
| 2 wk | 0.904 | 40.3% | 3231 |
| 4 wk | 0.854 | 40.7% | 3165 |
| 8 wk | 0.788 | 40.7% | 3024 |

**Level is sticky** (autocorrelation stays high out to 8 weeks — which is
exactly why persistence is such a hard forecasting baseline, per M3/M3.5).
But **direction mean-reverts at every horizon**: a deck that rose over the
last h weeks keeps rising only ~40% of the time — *below* a coin flip. That is
anti-momentum, the time-domain fingerprint of the 66%-cyclic matchup
structure (Exp 1) and the negative share-coupling (V3.2). Multi-week share is
not more *point*-predictable, but it carries a real **contrarian** signal:
hyped decks recede.

## Synthesis and recommendation

The three results are one coherent story: matchups are 2/3 rock-paper-scissors
(Exp 1) → so overrepresented decks get teched and beaten down (Exp 2) → so
metagame shares mean-revert rather than trend (Exp 3). This is a genuine,
defensible product surface — and notably it is all **descriptive/analytic**,
which is the positioning M3 already forced us into, now with real teeth.

Buildable features, in priority order:

1. **Empirical tech finder (highest value, ship-ready signal).** "When X is
   this popular, the field is teching {cards}; here is what's trending into
   sideboards against it." Powers S5 (spiking tech cards) and S6 (My Deck:
   "lists like yours are adopting …"). Needs the lead-lag/partial-correlation
   hardening and a pre-registered check, then it is a paid-tier feature. No
   card tags required.
2. **Macro strategy-type view.** Cluster archetypes into a few strategy axes
   (from card2vec embeddings and/or the matchup matrix's cyclic structure) and
   surface the type-level rock-paper-scissors ("aggro-control is favored into
   the current combo-heavy field"). Powers S2 depth and the "why" behind the
   best-response recommender (M3.5b).
3. **Contrarian trend flag.** "This deck is overextended and historically
   recedes" — an honest, validated framing for S5 trends that does not
   overclaim prediction.

Card embeddings (card2vec on our 450k decks) are the shared substrate for 1
and 2 and are cheap to build; a functional-tag layer (oracle-text mining, or
licensed Scryfall Tagger) is optional polish for interpretability, not a
blocker.

Recommended next step: promote **Experiment 2** into a proper `models/tech/`
milestone — lead-lag tech-response model with a pre-registered backtest
(does "trending tech vs A" actually gain share/winrate when A is up, on
withheld data). It is the first of these with a clear paid-feature shape and a
falsifiable target.

## Artifacts

- `validation/v3_evolution/macro_tech_explore.py` — all three experiments
  (clearly marked exploratory; descriptive, not an acceptance gate).
- No new model code committed to `models/` yet (would land with the proposed
  `models/tech/` milestone).
