"""Deck vectorization for the clustering stage (plan §5 Layer 1).

Representation: sparse vector of mainboard card counts on cards.id, with
config-driven exclusions (basic lands via type_line prefixes from
formats.config) and TF-IDF-style down-weighting of format-ubiquitous staples,
then L2 normalization so that dot product = cosine similarity.

IDF uses the smoothed formula ln((1 + N) / (1 + df)) + 1 (the same shape as
sklearn's TfidfTransformer with smooth_idf=True), computed on the corpus
passed in — deterministic for a given deck list.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
from scipy import sparse


@dataclass(frozen=True)
class DeckVectors:
    deck_ids: tuple[int, ...]  # row -> decks.id
    card_ids: tuple[int, ...]  # column -> cards.id
    matrix: sparse.csr_matrix  # L2-normalized tf-idf weights
    idf: np.ndarray


def vectorize(
    decks: list[tuple[int, dict[int, int]]],
    exclude_card_ids: frozenset[int] = frozenset(),
) -> DeckVectors:
    """decks: [(deck_id, {card_id: mainboard count})], already filtered to the
    zone of interest. Rows keep input order; columns are sorted card ids."""
    vocab_ids = sorted(
        {cid for _, cards in decks for cid in cards if cid not in exclude_card_ids}
    )
    col = {cid: i for i, cid in enumerate(vocab_ids)}

    rows: list[int] = []
    cols: list[int] = []
    vals: list[float] = []
    for r, (_, cards) in enumerate(decks):
        for cid, count in sorted(cards.items()):
            c = col.get(cid)
            if c is not None:
                rows.append(r)
                cols.append(c)
                vals.append(float(count))
    counts = sparse.csr_matrix(
        (vals, (rows, cols)), shape=(len(decks), len(vocab_ids)), dtype=np.float64
    )

    n = max(len(decks), 1)
    df = np.asarray((counts > 0).sum(axis=0)).ravel()
    idf = np.log((1.0 + n) / (1.0 + df)) + 1.0

    weighted = counts.multiply(sparse.csr_matrix(idf)).tocsr()
    norms = sparse.linalg.norm(weighted, axis=1)
    norms[norms == 0] = 1.0
    normalized = sparse.diags(1.0 / norms) @ weighted

    return DeckVectors(
        deck_ids=tuple(d for d, _ in decks),
        card_ids=tuple(vocab_ids),
        matrix=normalized.tocsr(),
        idf=idf,
    )
