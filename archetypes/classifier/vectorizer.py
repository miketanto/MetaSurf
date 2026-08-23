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
    feature_dim: int = 0  # trailing semantic columns, 0 when disabled
    feature_coverage: np.ndarray | None = None  # per-deck share of copies with features


def vectorize(
    decks: list[tuple[int, dict[int, int]]],
    exclude_card_ids: frozenset[int] = frozenset(),
    card_features: dict[int, np.ndarray] | None = None,
    feature_weight: float = 0.0,
) -> DeckVectors:
    """decks: [(deck_id, {card_id: mainboard count})], already filtered to the
    zone of interest. Rows keep input order; columns are sorted card ids.

    With `card_features` supplied and `feature_weight` (beta) > 0, a second
    channel of semantic columns is appended (see `_append_feature_channel`).
    At beta = 0 — the default — this function is byte-for-byte the original
    card-identity vectorizer, which is what makes the ablation honest: the
    V1 suite at beta = 0 must reproduce the committed M1 report exactly.
    """
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

    base = DeckVectors(
        deck_ids=tuple(d for d, _ in decks),
        card_ids=tuple(vocab_ids),
        matrix=normalized.tocsr(),
        idf=idf,
    )
    if not card_features or feature_weight <= 0.0:
        return base
    return _append_feature_channel(base, counts, vocab_ids, card_features, feature_weight)


def _append_feature_channel(
    base: DeckVectors,
    counts: sparse.csr_matrix,
    vocab_ids: list[int],
    card_features: dict[int, np.ndarray],
    beta: float,
) -> DeckVectors:
    """Append the semantic channel: [ L2(tfidf) || beta * L2(feature profile) ].

    The profile is `sum over cards of (raw copies * feature vector)`, using RAW
    counts rather than tf-idf weights: the tf-idf term exists to down-weight
    format-ubiquitous *identities*, and re-applying it here would double-count
    that correction against what a deck mechanically contains.

    Cards absent from `card_features` contribute nothing, as do the 763 known
    all-zero rows. A deck whose profile is entirely zero (no covered card with
    any scripted mechanic) keeps a zero feature channel rather than being
    normalized by zero, so it is compared on card identity alone.

    The concatenation is re-normalized to unit length, so cosine similarity is
    (cos_cards + beta^2 * cos_features) / (1 + beta^2) — one interpretable knob.
    """
    dim = len(next(iter(card_features.values())))
    basis = np.zeros((len(vocab_ids), dim), dtype=np.float64)
    covered = np.zeros(len(vocab_ids), dtype=np.float64)
    for col, card_id in enumerate(vocab_ids):
        vector = card_features.get(card_id)
        if vector is not None:
            basis[col] = vector
            covered[col] = 1.0

    profile = counts @ basis  # (n_decks, dim), dense
    norms = np.linalg.norm(profile, axis=1)
    norms[norms == 0.0] = 1.0  # all-zero profiles stay all-zero
    profile = (profile / norms[:, None]) * beta

    copies = np.asarray(counts.sum(axis=1)).ravel()
    copies[copies == 0.0] = 1.0
    coverage = np.asarray(counts @ covered).ravel() / copies

    combined = sparse.hstack([base.matrix, sparse.csr_matrix(profile)], format="csr")
    combined_norms = sparse.linalg.norm(combined, axis=1)
    combined_norms[combined_norms == 0] = 1.0
    combined = sparse.diags(1.0 / combined_norms) @ combined

    return DeckVectors(
        deck_ids=base.deck_ids,
        card_ids=base.card_ids,
        matrix=combined.tocsr(),
        idf=base.idf,
        feature_dim=dim,
        feature_coverage=coverage,
    )
