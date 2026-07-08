# Tech Finder — design & research (backlog BL-1)

**Thesis: this is buildable.** The tech signal is real — the open problem is
*method*, not existence. When an archetype has a distinctive structural
weakness, the data already surfaces its answer cleanly: vs **GenericTron** the
matchup-conditioned signal's top hit is **Molten Rain** ("Destroy target
land… if nonbasic…", +0.225 differential, 75.8% realized winrate vs Tron),
with **Ghost Quarter** alongside — textbook anti-Tron land destruction, found
with zero prior knowledge. The task is to make that work *reliably* and
*generalise it to undiscovered cards*, while controlling the confounds that
muddy it elsewhere.

This note is the standing design; it supersedes the scattered pieces in
`research-log.md` §4a–4d, which remain the evidence trail.

## 1. What the research established (this session, all reproducible)

| finding | evidence | implication for the design |
|---|---|---|
| Naive share-correlation ≠ tech | vs Eldrazi it returns board wipes (Pyroclasm r=0.69) — generic creature answers | must condition on the **matchup**, not the meta-state |
| Matchup difference-in-differences helps but isn't enough | removes board wipes; surfaces **Storm signature** cards (Past in Flames) because the *deck* beats Eldrazi | must control **archetype identity** |
| Embeddings are a weak identity control | `1−maxcos(card, centroid)` kept Burn engines; co-occurrence compresses cards toward their archetype | prefer **archetype-play entropy** (data) over embedding for the flexibility control |
| It works for distinctive archetypes | vs Tron: Molten Rain / Ghost Quarter (land destruction) surface cleanly | ship first for archetypes with a **functional weakness**; degrade gracefully elsewhere |
| It's muddy for creature decks | vs Eldrazi survivors are generic-good (Duress) or false positives (Burrenton Forge-Tender = pro-red) | pooling by **function** (not raw card) is required to cut through |
| Functionally-identical cards span the whole play-count range | "counter target triggered ability": Consign to Memory 22,531 decks → Trickbind 168 → Disruption Protocol 0 | a **content** representation generalises to unplayed cards; co-occurrence cannot |

**Conclusion the evidence forces:** the winning method is *function-first*.
Represent each card by what it **does**, pool the matchup signal by function,
control confounds by design, and only then rank cards — played or not.

## 2. The design

### Layer A — card "understanding" (functional roles)
Assign each card a set of functional roles from `oracle_text` / `keywords` /
`type_line` / `cmc` / `colors` (all held in the committed Scryfall snapshot).
Starter role vocabulary (config, game-neutral, fixture-tested per CLAUDE.md):

```
removal-creature-single   sweeper-creature        removal-artifact
removal-enchantment       removal-planeswalker     land-destruction / mana-denial
counter-spell             counter-ability          graveyard-hate
hand-disruption           bounce                   protection / hexproof
taxation / stax           lifegain                 damage-prevention
```
Plus scalar features: cmc, colour identity, instant-speed, sideboard-rate.
Build options, increasing cost: **(a)** oracle-text regex rules with a fixture
suite (start here — deterministic, auditable); **(b)** a learned text
embedding (generalised card representation, arXiv:2407.05879); **(c)** licensed
Scryfall Tagger `otag:` (best coverage, licensing must clear first). Roles are
multi-label and versioned like the archetype definitions.

### Layer B — confound-controlled role↔matchup estimation
For each (role R, archetype A), estimate **the role's A-specific effect**,
controlling both confounds:

- **Within-archetype** (kills the identity confound): compare decks of the
  *same* base archetype X that do vs don't carry a card of role R, on their
  realized winrate against A. Pool over all X and all cards carrying R — this
  pooling is what makes the estimate feasible where the per-card version had
  no sample (§4c).
- **Matchup-conditioned difference-in-differences** (kills the meta-state
  confound): the effect is (WR vs A | has R) − (WR vs A | no R) minus the same
  quantity against non-A opponents. A generic role (sweeper) nets ~0; an
  A-specific role (mana-denial vs Tron) nets positive.
- Output: a small, interpretable **tech profile** per archetype = the roles
  that specifically beat it, each with an effect size + CI.

### Layer C — rank cards, including undiscovered ones
Score every card (played or not) = fit to A's tech profile (does it carry the
high-effect roles?) × castability for A's opponents (colours/cost) × inverse
current play-rate. Surface the top *underplayed* matches as **hidden tech**;
oracle text explains each. This is the step co-occurrence embeddings cannot do
(an unplayed card has no co-play vector) — the content roles carry it.

## 3. Why it degrades gracefully (honest scope)
The method works in proportion to how *distinctive* an archetype's weakness is.
Tron (attack their nonbasic mana), Storm (hand disruption / graveyard hate),
Affinity (artifact removal) have sharp functional answers → strong, specific
signal. Fair creature decks (Eldrazi) are beaten by *generic* creature answers,
so the A-specific component is genuinely small — the model should **report low
confidence** there rather than manufacture false tech. That is a feature: the
tech profile's effect-size CIs tell the user when there *is* dedicated tech and
when the answer is just "play good cards."

## 4. Build phases & data needs
1. **Layer A role parser** — frozen data; fixture-tested; ships a `roles`
   table keyed to `cards.id`. *Doable now.*
2. **Layer B on frozen data** — within-archetype role effects for the
   distinctive archetypes that have enough matches (Tron, Storm, Affinity,
   Titan). *Doable now, but sample-thin for smaller archetypes.*
3. **Pre-registered validation** (below). *Doable now for the big archetypes;
   full coverage wants M4 live volume.*
4. **Layer C hidden-tech ranking + temporal backtest** — needs the most
   sample; **pairs with M4** for a clean forward test.

## 5. Validation (pre-registered, falsifiable)
- **B1 role-effect reproducibility:** a role's A-specific effect estimated on
  one time-block predicts its sign/rank on a disjoint block (not overfit).
- **B2 known-tech recovery:** for a held-out set of archetypes with
  community-known tech (Tron↔land destruction, Dredge↔graveyard hate), the
  profile ranks the correct role in its top-k. Precision@k vs a
  frequency-only baseline.
- **C1 hidden-tech temporal precision:** for cards underplayed at time t that
  became established tech vs A by t+Δ, did the profile rank them at t, before
  adoption? Precision@k vs a play-count-momentum baseline, on withheld
  archetypes/periods. This is the headline "we predicted the tech" gate.

Targets are set once and not tuned to; a miss is reported, not lowered
(CLAUDE.md).

## 6. Risks / open questions
- Oracle-text role parsing is heuristic — needs a real fixture suite and an
  unresolved-roles report (same discipline as card resolution / archetype
  rules).
- Scryfall Tagger licensing is unresolved; the regex path avoids it.
- "Brought in for the matchup" (true sideboard plans) is data the cache lacks —
  we approximate with 75-card presence; a future sideboard-guide source would
  sharpen Layer B.
- Small-archetype sample: honestly gated on M4.

## 7. Status
Backlog **BL-1**, high value / high effort.

**Phases 1–2 + validation B2/B1 are BUILT and produced first positive evidence
(2026-07-08).** Report: `validation/reports/tech-finder-b1b2-2026-07-08.md`.
- **Layer A** — `archetypes/roles` + `config/card_roles.json`: fixture-tested
  oracle-text role parser (40 tests vs real Scryfall text; interaction roles
  only). Materialize with `scripts/materialize_card_roles.py`.
- **Layer B (roles)** — `validation/tech_finder/estimate.py`: the
  within-archetype, matchup-conditioned DiD (card-agnostic → game-neutral seam).
- **Card-level tech ("what card is good vs archetype A")** —
  `validation/tech_finder/cards.py` + `card_report.py`: the SAME within-archetype
  DiD with the treatment = a single card in the 75 (not a role). Per-archetype
  ranked card sheets for both formats:
  `validation/reports/tech-cards-{modern,standard}-2026-07-08.md`. Cards annotated
  with their role(s) and flagged when they are pure manabase/deck-identity proxies
  (a Land with no interaction role — rides deck-type correlation, imperfectly
  controlled at thin strata). Sensible & useful in both formats — e.g. vs Tron:
  Obsidian Charmaw / Spreading Seas / Void Mirror; vs Living End: The Stone Brain
  (names it) / Karn (fetches the cage); vs Boros Convoke (Std): Sunfall /
  Depopulate / Temporary Lockdown. Card-level can be SHARPER than the role view
  (the specific best sweeper is A-specific vs Convoke even when the pooled
  `board_sweeper` role is muddy). Only cards with enough sample are scored; the
  thin/unplayed ones are what Layer C would infer from the role profile.
- **B2 recovery (Modern): 5/7 gated PASS (10/13 across all targets).** On the
  rebuilt Modern corpus (347,438 decided non-mirror match rows) the
  within-archetype DiD ranks the known tech role in the top-3 for most of 13
  pre-registered archetypes, and at a rank ≤ the naive prevalence baseline
  everywhere it passes — often far better (Tron 1 vs 5, Titan 2 vs 5, Ruby Storm
  2 vs 5, Aggro 2 vs 8). It surfaces correct nuance: vs Titan it ranks
  `mana_denial` above `land_destruction` (Amulet floods lands, so Blood Moon
  bites but land destruction doesn't). Three honest misses: HammerTime (artifact
  removal ranks near-last — Hammer is resilient / a-priori wisdom wrong); Affinity
  (artifact removal fell to rank 4 after the role vocab was broadened to fold
  flexible any-permanent removal in for Standard — functionally correct but
  dilutes artifact-specificity); Yawgmoth (graveyard hate not A-specific — it's a
  battlefield engine, our label was likely wrong).
- **B1 reproducibility: 2/7 gated.** Only graveyard_hate vs the graveyard decks
  (LivingEnd, GoryoReanimator) is positive+top-k across two disjoint eras
  (2022–23 / 2024–25). Every narrow tech (land destruction, mana denial, artifact
  removal, counters, discard) shifts across eras → graveyard hate is a persistent
  structural tech, most other tech is metagame-contingent. Reported, not lowered.
- **Standard transfer test: the method does NOT transfer (gated 0/3).** Report:
  `validation/reports/tech-finder-standard-2026-07-08.md`. Standard 2024–25 has
  ~62k directed rows and few archetypes, so the within-archetype DiD has only
  1–3 contributing strata (vs Modern's 15–31) — single-archetype noise outranks
  the genuine (weak) graveyard-hate signal; and the go-wide aggro targets are
  §4d's muddy creature-deck case (sweepers are generic, not A-specific). The tool
  needs both large match volume AND a distinctive non-generic weakness — Modern
  supplies both, Standard neither.
- **Layer C** (rank *unplayed* hidden tech) and **C1** (temporal precision@k)
  remain future work; want more live volume (§4b phase 4).

Reproduce: `python -m validation.tech_finder` (this milestone). Earlier negative
probes: `python -m validation.embedding_tech_explore` and `python -m
validation.v3_evolution.macro_tech_explore`.
