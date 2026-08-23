# Card semantics from CardGuru — integration design

**Status:** spike complete, integration not started. Owner decision pending.
**Measured evidence:** `validation/reports/cardsem-coverage.md` (2026-08-23).

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

## What this unlocks beyond the classifier

One integration, three payoffs — this is the argument for doing it first:

- **Classifier stability.** Functional card swaps stop registering as new decks.
- **Explainable emergence (S5).** A new cluster can be described by the
  dimensions on which its centroid differs from its nearest neighbour — "new
  cluster, 12 lists" becomes "new cluster running graveyard exile and ETB
  triggers". `dims.py` carries the names that make this readable. No LLM.
- **Semantic tech drift (V3.3 / S5).** Card-level spikes aggregate into
  format-level statements ("the format added 23% more graveyard exile this
  week"), which is a far better alert than twenty card names.

## Open questions for the owner

1. **Licensing.** CardGuru operates under the Fan Content Policy
   (non-commercial, no paywalls on rules content); MetaSurf plan §9 is a paid
   product. These vectors are derived mechanical descriptors rather than card
   text, but the posture difference must be settled before anything derived
   from this file ships in a paid surface.
2. **Milestone placement.** This is Layer 1 work and M1 is closed. It is either
   an M1 amendment (re-validated, new report) or deferred behind M2. It should
   not land silently mid-M2.
3. **Pin cadence.** New sets require re-extraction upstream. Feature staleness
   becomes a rebuild input, same lifecycle as the Scryfall snapshot.
