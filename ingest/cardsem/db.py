"""Database-facing side of the card-semantics bridge.

Kept separate from `loader.py` so that the parser and join logic stay
stdlib-only and testable with no infrastructure. This module is the only place
in `ingest/cardsem` that imports psycopg or numpy.
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
import psycopg

from ingest.cardsem.coverage import DEFAULT_FEATURES
from ingest.cardsem.loader import CardIdentity, JoinResult, join_to_cards, load_feature_table


def load_card_features(
    conn: psycopg.Connection,
    game: str = "mtg",
    features_path: Path = DEFAULT_FEATURES,
    drop_zero_vectors: bool = True,
) -> tuple[dict[int, np.ndarray], JoinResult[int]]:
    """Map `cards.id` -> feature vector for one game.

    Returns the mapping and the full join result, so callers can report
    coverage and unresolved names instead of silently proceeding on a partial
    join (CLAUDE.md rule 3: unresolved names get logged, never guessed).

    `drop_zero_vectors` omits cards whose vector is entirely zero. Those rows
    conflate genuinely vanilla cards with mechanics the extractor cannot see
    (infect, cycling, delve — see PROVENANCE.md), and an all-zero vector adds
    nothing to a deck profile either way; dropping them keeps the distinction
    between "no mechanics" and "not covered" visible in the coverage numbers.
    """
    table = load_feature_table(features_path)
    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT c.id, c.name, c.attrs->'face_names'
            FROM cards c JOIN games g ON g.id = c.game_id
            WHERE g.name = %s
            ORDER BY c.id
            """,
            (game,),
        )
        identities = [
            CardIdentity(key=cid, name=name, face_names=faces or ())
            for cid, name, faces in cur
        ]

    result = join_to_cards(table, identities)
    dropped = set(result.zero_vector_keys) if drop_zero_vectors else set()
    features = {
        card_id: np.asarray(vector, dtype=np.float64)
        for card_id, vector in result.by_card_key.items()
        if card_id not in dropped
    }
    return features, result
