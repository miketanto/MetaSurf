"""Card-semantics bridge: CardGuru mechanical feature vectors -> cards.id.

This is an MTG **adapter-layer** module (plan §4.1 rule 2). It carries
MTG-specific data — mechanical features derived from Forge card scripts — in
exactly the same posture as `archetypes/definitions/`: pinned, committed,
provenance-documented data files, never a code dependency on the upstream
project. Nothing here may be imported from `models/`, `jobs/`, or `api/`.

What the features are: 68 dimensions per card, read off CardGuru's ability
graph by `rl/e2_extract.py` — 9 answer classes, 20 effect APIs, 18 keywords,
and 21 structural dims (trigger modes, static/replacement/activated presence,
target domains, damage magnitude, pump signs, supertypes, recursion,
multi-face). All binary except `num_dmg`, which is `min(NumDmg, 6) / 6`.
Provenance and pins: PROVENANCE.md.

Why MetaSurf wants them: the clustering-stage vectorizer treats every card as
an orthogonal dimension, so two functionally identical removal spells are as
far apart as a removal spell and a land. Features give the classifier a second
channel in which those two cards are the *same point*, and give brand-new
cards a meaningful position on the day they are printed (a card with df=1 has
maximal IDF — loud and meaningless — but its feature vector is valid at once).

Stdlib only, and no database access: the join takes `CardIdentity` records so
it can be driven equally from the `cards` table or from `parse_cards()` output,
and stays testable with no infrastructure (same posture as `ingest/normalize`).
"""

from __future__ import annotations

from ingest.cardsem.loader import (
    CardIdentity,
    FeatureTable,
    FeatureTableError,
    JoinResult,
    fold_name,
    join_to_cards,
    load_feature_table,
    parse_feature_table,
)

__all__ = [
    "CardIdentity",
    "FeatureTable",
    "FeatureTableError",
    "JoinResult",
    "fold_name",
    "join_to_cards",
    "load_feature_table",
    "parse_feature_table",
]
