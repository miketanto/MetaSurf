# M3.8 investigation — card2vec embeddings & macro strategy axes (BL-3)

**Status: card2vec validated as a substrate; macro clusters coherent; but the
"macro type-level rock-paper-scissors" is weaker than hoped.** All numbers are
printed output of `python -m validation.embeddings_explore` (2026-07-07),
deterministic (identical across reruns). Descriptive/exploratory, not a gate.

## Method

Card embedding from deck co-occurrence only — no card text, colour, or cost
(the card2vec idea; afreefaw/MTG-card2vec). Implemented as **PPMI-SVD**
(`models/embeddings/`, game-neutral): Levy & Goldberg (2014) proved SVD of a
positive-PMI matrix approximates skip-gram word2vec, and it is *deterministic*
(no negative-sampling RNG), which the repo's determinism discipline requires.
Vocabulary: 1,851 cards appearing in ≥100 Modern mainboards (basics excluded);
449,941 labelled decks; 50 dimensions; context-distribution smoothing 0.75.

## 1. Card neighbours — coherent, from co-occurrence alone

Nearest cosine neighbours (zero card content used):

| card | nearest neighbours | reads as |
|---|---|---|
| Urza's Tower | Urza's Mine, Urza's Power Plant, Kozilek, Warping Wail, Ugin | Tron |
| Amulet of Vigor | Simic Growth Chamber, Gruul Turf, Vesuva, Golgari Rot Farm | Amulet Titan (bounce lands) |
| Goblin Guide | Vexing Devil, Eidolon of the Great Revel, Shard Volley | Burn |
| Griselbrand | Ghalta, Terastodon, Borborygmos, Nourishing Shoal | Reanimator targets |
| Counterspell | Murktide Regent, Dress Down, Minor Misstep | blue tempo/control |

## 2. Archetype recovery — strong quantitative validation

Deck vector = mean of its card vectors; classify each deck by its nearest
archetype centroid (built with **zero label supervision** from the embedding):

- **top-1 accuracy 0.773** over 11,247 sampled decks, vs a majority-class
  baseline of **0.124** — a ~6× lift. The embedding has recovered the archetype
  structure purely from which cards are played together.

## 3. Macro strategy axes — coherent clusters, owner to name

KMeans (k=6, fixed seed) over archetype centroids. Names are **not** assigned
from memory (CLAUDE.md rule 4); clusters + measured features are for the owner:

| cluster | avg cmc | creature share | member archetypes (top) | signature cards |
|---|---|---|---|---|
| 0 | 1.37 | **0.46** | Yawgmoth, Humans, Infect, Devoted/Heliod Combo | Chord of Calling, green fetches |
| 1 | 1.43 | 0.23 | Aggro, Titan, Energy, LivingEnd | Lightning Bolt, red duals |
| 2 | 1.76 | 0.25 | GenericTron, HammerTime, Eldrazi, Affinity, HardenedScales | Urza's Saga, Expedition Map, Tron lands |
| 3 | 1.39 | 0.28 | GenericMidrange, Shadow, Dredge, Scam | Thoughtseize, Fatal Push, black fetches |
| 4 | 1.50 | **0.16** | GenericControl, Azorius Control, Mill, Merfolk | blue fetches/duals |
| 5 | **2.41** | 0.18 | Belcher, Neobrand, AdNauseam, OopsAllSpells | Pact of Negation, Lotus Bloom, rituals |

These map recognisably onto strategy families (cluster 2 = artifact/big-mana,
cluster 5 = all-in ritual combo with the highest curve, cluster 4 = blue
control with the fewest creatures, cluster 0 = creature-combo with the most)
— all from co-occurrence, and coherent enough to name and navigate by.

## 4. The honest twist — macro RPS is weak; the cycles are fine-grained

Aggregating the Layer-2 matchup matrix to the 6 macro clusters
(size-weighted) and Hodge-decomposing it:

- **Macro 6×6 matchup: 87.4% transitive, 12.6% cyclic.** Cluster 1 is mildly
  favoured across the board; the matrix is close to a weak strength ranking,
  and macro types sit near 50% against each other (spread 0.47–0.53).

This *contrasts* with the archetype-level result (M3.6-1: **66.6% cyclic**).
The owner's premise — "aggro-control beats all-in combo" as a macro triangle —
is only weakly present: the rock-paper-scissors is a **fine-grained,
archetype-vs-archetype** phenomenon that largely **cancels when pooled into
broad strategy types**. So the macro-type view is genuinely useful for
*organisation and navigation* (and the clusters are real), but a clean
type-level RPS triangle is not what the data shows; the exploitable cyclic
structure lives at the specific-archetype level, where the matchup matrix (M2)
and the recommender (V-REC) already operate.

## Recommendation

- **Ship the embedding as infrastructure.** card2vec is validated (0.773
  recovery) and cheap; it powers: deck similarity ("lists like yours"),
  on-the-fly classification of pasted lists (S6), and the macro-cluster
  navigation view (S2/S3 grouping). It is also the co-occurrence half of the
  future tech work (the content half — BL-1 §4b — still needs card text).
- **Frame the macro view as navigation, not prediction.** "Strategy families
  and how they're doing," not "aggro beats combo this week." The cyclic edge
  is archetype-level and is already surfaced by the matchup matrix.
- Promote `models/embeddings/` (done, tested) toward a card-similarity rollup
  when the API (M5) lands.

## Artifacts
- `models/embeddings/cooccurrence.py` — deterministic PPMI-SVD (4 property tests).
- `validation/embeddings_explore.py` — this exploration (deterministic).
