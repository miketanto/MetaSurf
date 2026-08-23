# Card semantics from CardGuru — integration design

**Status: ABLATION RUN — hypothesis not supported. Do not enable. Owner review.**

The bridge is built, the coverage is excellent (96.45% of the card universe,
100% of the decklist corpus), and the channel is implemented and tested. It
does **not** improve the classifier on either V1 gate, and degrades both at
higher weights. The feature channel ships **disabled** (`feature_weight=0.0`
default, byte-identical to the pre-existing vectorizer) as an instrument, not
as a change to the pipeline.

**Measured evidence:**
- `validation/reports/cardsem-coverage.md` (2026-08-23) — coverage
- `validation/reports/cardsem-ablation.md` (2026-08-23) — the ablation

**Results summary (tuning month 2023-03; holdout deliberately NOT spent):**

| | baseline (β=0) | best swept β (0.5) |
|---|---:|---:|
| V1.1 agreement | 0.9925 | 0.9926 (+0.0002) |
| Weakest established F1 | 0.9328 | 0.9225 (worse) |
| Azorius Control F1 (predicted to improve) | 0.9661 | 0.9574 (**falsified**) |
| V1.2 min cluster purity | 0.833 | 0.714 (worse) |
| V1.2 max detection lag | 0 days | 4 days at β=1.0 (worse) |

See "Outcome" below for the diagnosis.

## The problem

`archetypes/classifier/vectorizer.py` represents a deck as a sparse vector of
mainboard counts over `cards.id`, TF-IDF weighted and L2-normalized. Every card
is an **orthogonal dimension**, which has two consequences:

1. Two functionally identical removal spells are exactly as far apart as a
   removal spell and a land. A deck that swaps four removal spells after a set
   release moves four dimensions and can fracture into a "new" cluster.
2. A newly printed card has `df = 1`, so smoothed IDF gives it near-maximal
   weight. It is simultaneously the **loudest** and the **least meaningful**
   dimension in the space — the worst combination for V1.2 emergence detection,
   which is the backtest behind the S5 premium feed.

The classifier knows card *identity*. It does not know card *function*.

## What CardGuru supplies

`rl/e2_extract.py` reads Forge card scripts into an ability graph and emits a
68-dimension mechanical vector per card: 9 answer classes, 20 effect APIs, 18
keywords, 21 structural features (trigger modes, static/replacement/activated
presence, target domains, damage magnitude, pump direction, supertypes,
recursion, multi-face). All binary except `num_dmg`.

The table is committed here as pinned data (`ingest/cardsem/features.tsv.gz`,
provenance in `PROVENANCE.md`) — **not** a code dependency. MetaSurf never
imports CardGuru, never needs a Forge or XMage checkout, and never reaches the
network for it. Same posture as `archetypes/definitions/` and the Scryfall
snapshot.

## Measured coverage (see the report for the full tables)

| | |
|---|---:|
| Card universe with a feature vector | **96.45%** (33,000 / 34,213) |
| Corpus distinct names with features | **100.00%** (1,966 / 1,966) |
| Corpus copies with features (weighted) | **100.00%** (133,232 / 133,232) |

The corpus figure is over a fixture sample of 12 files / 1,618 decks, 375 of
which are Limited. It must be re-measured against the full MTGODecklistCache
clone before the integration is committed to — but 100% on a sample that
*includes* a Limited pool is a strong signal, because obscure commons are
exactly where coverage would be expected to fail.

**The gap between 96.45% and 100% is the useful finding:** the 3.55% of the
universe with no features is concentrated in cards nobody plays. Coverage is
excellent precisely where it matters.

## The one real caveat

763 rows (2.16%) are all-zero. That set **conflates two different things**, and
they cannot be told apart from the vector alone:

- genuinely vanilla creatures, where zero is correct (`Axebane Beast`)
- cards whose only ability is a mechanic outside the extractor's 18-keyword
  list, where zero is a **lie** (`Glistener Elf` / infect, `Gurmag Angler` /
  delve, `Street Wraith` / cycling — all verified all-zero in the shipped table
  by `tests/test_cardsem.py`)

`infect`, `cycling`, `delve`, `cascade`, `storm`, `dredge`, `evoke`,
`affinity`, `convoke` and `madness` have no dimension. Several of those *name
Modern archetypes*. Two consequences:

1. **Masking is a correctness requirement, not an optimization.** A deck whose
   feature coverage falls below a threshold must fall back to the card-identity
   channel rather than be scored against a vector of false zeros.
2. Extending `KEYWORDS` in `rl/e2_extract.py` upstream is cheap — it is a list
   literal — and is the highest-value follow-up on the CardGuru side.

## Proposed integration

Concatenate a second channel; do not replace the first:

```
deck_vector = [ α · L2(tfidf_counts) ‖ β · L2(feature_profile) ]
feature_profile = Σ_card  count × f(card)      # masked cards contribute nothing
```

Cosine over the concatenation decomposes to `α²·cos_cards + β²·cos_features`,
so there is exactly one knob. Chosen over the alternatives because:

- **β = 0 must reproduce today's output byte-for-byte.** V1.3's determinism
  check already enforces byte-identity, so the safety proof is free.
- It preserves the card-identity signal carrying the current 0.9949 agreement.
  Replacing counts with features outright would collapse rules-stage agreement.
- It is a clean ablation, which plan §V2.3 demands of every other component
  ("each component must earn its complexity or be removed").

Follow-up if the concatenation wins: card-similarity smoothing
(`v' = v·(I + λS)`, `S` = thresholded card-card cosine in feature space).
Denser, but restricted to corpus vocabulary it is a few thousand columns, not
35k. Not first.

## Validation sequence (binding)

1. Run V1.1–V1.3 at β=0. **Must byte-match the committed
   `validation/reports/m1-v1-archetypes.md`.** If it does not, the plumbing is
   wrong — stop.
2. Sweep β on the **tuning month 2023-03 only**. The 2024-01 holdout stays
   untouched; that separation was established in M1 and must not be spent here.
3. One holdout run at the frozen β. New dated report.

**Pre-committed prediction, recorded before the sweep is run:** the two
archetypes below 0.95 F1 in the M1 holdout are Azorius Control (0.9231) and
Scam (0.9286). Control decks are precisely those whose lists differ by flexible,
functionally interchangeable answer suites. If the feature channel does anything
real, it lifts Azorius Control. If aggregate agreement improves while that cell
does not move, the mechanism is not working and the aggregate should not be
trusted.

Per CLAUDE.md, if a target is missed the analysis goes in the report and the
work stops for owner review — the target is not adjusted.

## Outcome

The sequence above was executed in full. Step 1 passed: the V1 suite at β=0
reproduces `validation/reports/m1-v1-archetypes.md` byte-for-byte, both before
and after the vectorizer change, so every number below is attributable to the
feature channel alone. Steps 2 and 3 produced a negative result, and per
CLAUDE.md the holdout was **not** spent: no β was worth freezing.

### The prediction was falsified

Azorius Control F1 declines monotonically with β (0.9661 → 0.9641 → 0.9574 →
0.9554). The pre-committed rule was that this cell moving is what distinguishes
a real mechanism from aggregate noise. It moved the wrong way. The target is
not adjusted and the window is not re-picked.

### Diagnosis: V1.1 cannot reward functional abstraction

The ground truth for V1.1 is the **rules-stage labels**, and those rules are
defined by *card identity* ("contains ≥N of card X"). A channel whose entire
purpose is to see past card identity necessarily moves the clusterer away from
that oracle. V1.1 is scored against a card-identity ground truth, so it is
structurally incapable of rewarding this change — the metric and the hypothesis
are misaligned. This is a flaw in the experiment design, not only in the result.

### There was almost no headroom

Baseline agreement is 0.9925 and V1.2 already detects both emergence events on
day zero (purity 1.000 and 0.833). A second channel can realistically only
dilute a signal that is already near-saturated on these gates.

### Correction to the motivating argument

The design above claimed a newly printed card is "loud and meaningless" because
`df = 1` gives it near-maximal IDF. The V1.2 numbers say the opposite: that
maximal weight is exactly *why* decks sharing a brand-new card cluster together
immediately and at perfect purity. For emergence detection, high IDF on a new
card is the mechanism working, not a defect — and the feature channel dilutes
it (Nadu detection slips from day 0 to day 4 at β=1.0). That part of the
rationale was wrong.

### The one real effect

Noise decks collapse from 85 to 1 as β rises. The channel makes everything look
more alike, absorbing outliers into existing clusters. That is also the
mechanism behind the V1.2 purity drops — it is a cost here, not a benefit,
since "outliers are Rogue" is deliberate semantics.

### What is NOT yet falsified

The stability claim — that functional card swaps should not re-label a deck
across set releases — is untested, because **no V1 gate measures it**. V1.1 is
a single month; V1.2 is two fixed events. Testing it needs a metric this repo
does not have: label churn for the same deck population across consecutive
months, with a controlled comparison across a set-release boundary. That is a
new validation suite, not a tuning run, and it should be the owner's call
whether it is worth building. It is the only surviving hypothesis.

## What this unlocks beyond the classifier

These were the arguments for doing it first. The classifier payoff is now
measured and did not materialize; the other two are **untested** and do not
depend on the vectorizer change, since they consume the feature table directly
rather than through deck vectors:

- ~~**Classifier stability.**~~ Measured, not supported — see Outcome. The
  narrower stability claim (cross-month label churn) remains untested.
- **Explainable emergence (S5).** A new cluster can be described by the
  dimensions on which its centroid differs from its nearest neighbour — "new
  cluster, 12 lists" becomes "new cluster running graveyard exile and ETB
  triggers". `dims.py` carries the names that make this readable. No LLM.
- **Semantic tech drift (V3.3 / S5).** Card-level spikes aggregate into
  format-level statements ("the format added 23% more graveyard exile this
  week"), which is a far better alert than twenty card names.

## Open questions for the owner

1. **Is the stability suite worth building?** The only surviving hypothesis
   (cross-month label churn across a set-release boundary) needs a new
   validation suite. Given that both existing gates came back negative, this is
   a real cost with an uncertain payoff — owner's call.
2. **Keep or revert the instrument?** The bridge and the disabled channel are
   inert (β=0 is byte-identical to the previous vectorizer) and are what make
   any future re-test cheap. The alternative is reverting and re-deriving later.
   Recommendation: keep, precisely because the negative result is only
   trustworthy while the instrument that produced it still exists.
3. **Upstream keyword fix.** Extending `KEYWORDS` in CardGuru's
   `rl/e2_extract.py` (infect/cycling/delve/cascade/storm/dredge/…) is cheap and
   would remove the largest known distortion. Worth doing before any re-test,
   since several of those mechanics *name* Modern archetypes.
4. **Pin cadence.** New sets require re-extraction upstream. Feature staleness
   becomes a rebuild input, same lifecycle as the Scryfall snapshot.

**Licensing:** owner has set this aside for now (2026-08-23). Noted in
`ingest/cardsem/PROVENANCE.md` and not a blocker for the work above.
