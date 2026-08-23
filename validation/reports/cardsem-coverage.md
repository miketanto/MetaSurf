# Card-semantics coverage — 2026-08-23

Owner-directed spike (not a milestone gate): measures whether CardGuru's mechanical feature table covers enough of MetaSurf's cards to be worth wiring into the clustering-stage vectorizer. Design note: `docs/notes/card-semantics-integration.md`.

All numbers are printed output of `python -m ingest.cardsem` against the two committed snapshots. Regenerate with that command; the report is deterministic.

## Feature table

- rows (registered names): **35390**
- dimensionality: **68**
- all-zero vectors: **763** (2.16% of rows)

## 1. Card-universe coverage (the ceiling)

Denominator is every card `ingest.scryfall.parse_cards` would load into `cards` — the same universe the classifier resolves against.

| metric | count | share |
|---|---:|---:|
| playable cards in universe | 34213 | 100.00% |
| **with a feature vector** | **33000** | **96.45%** |
| matched on exact name | 32974 | 96.38% |
| matched on folded name | 0 | 0.00% |
| matched via a face name | 26 | 0.08% |
| no feature vector | 1213 | 3.55% |
| matched but all-zero vector | 748 | 2.19% |

## 2. Corpus coverage (the number that decides it)

Counted over 12 real MTGODecklistCache files (1618 decks) in `tests/fixtures/`. **This is a fixture sample, not the full corpus** — `data/MTGODecklistCache` is gitignored and absent in this environment, so the headline must be re-measured against the full clone before the integration is committed to.

Composition: 377 of 1618 decks have a sub-60-card mainboard, i.e. are **Limited** (the 2019 MOCS Open fixture), not constructed. That inflates the obscure-commons tail — which makes full coverage a *stronger* result, since Limited pools are exactly where marginal cards would be expected to go missing.

| metric | count | share |
|---|---:|---:|
| distinct card names in corpus | 1966 | 100.00% |
| **distinct names with features** | **1966** | **100.00%** |
| total copies across all decks | 133232 | 100.00% |
| **copies with features (weighted)** | **133232** | **100.00%** |
| corpus names with an all-zero vector | 16 | 0.81% |

### Corpus cards present but all-zero (16)

The extractor found no scripted mechanics. Masking these (rather than treating a zero vector as 'this card does nothing') is a correctness requirement, not an optimization.

| copies | card |
|---:|---|
| 228 | Axebane Beast |
| 226 | Spikewheel Acrobat |
| 225 | Coral Commando |
| 220 | Catacomb Crocodile |
| 220 | Prowling Caracal |
| 217 | Rampaging Rendhorn |
| 210 | Feral Maaka |
| 209 | Street Wraith |
| 207 | Debtors' Transport |
| 83 | Ministrant of Obligation |
| 82 | Zhur-Taa Goblin |
| 44 | Glistener Elf |
| 34 | Gurmag Angler |
| 24 | Desert Cerodon |
| 23 | Endless One |
| … | _1 more_ |

## 3. Blind spots in the feature space

The 68 dimensions (names in `ingest/cardsem/dims.py`) cover 9 answer classes, 20 effect APIs, 18 keywords and 21 structural features. Keyword mechanics outside that 18-keyword list have no dimension, so a card whose only ability is one of them extracts to an all-zero vector — indistinguishable from a vanilla creature.

Archetype-defining mechanics with **no dimension**: `infect`, `cycling`, `delve`, `cascade`, `storm`, `dredge`, `evoke`, `affinity`, `convoke`, `madness`.

Empirical check against the shipped table:

| card | mechanic | vector |
|---|---|---|
| Glistener Elf | infect | **all-zero** |
| Gurmag Angler | delve | **all-zero** |
| Street Wraith | cycling | **all-zero** |
| Axebane Beast | _(vanilla — zero is correct)_ | **all-zero** |
| Coral Commando | _(vanilla — zero is correct)_ | **all-zero** |
| Prowling Caracal | _(vanilla — zero is correct)_ | **all-zero** |

**Consequence for the integration:** the zero-vector set mixes correct zeros with extraction gaps, and the two cannot be told apart from the vector alone. Masking (per-deck feature coverage below a threshold ⇒ fall back to the card-identity channel) is therefore a correctness requirement. Extending CardGuru's `KEYWORDS` list upstream is the real fix and is cheap — it is a list literal in `rl/e2_extract.py`.

