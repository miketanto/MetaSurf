"""Co-occurrence item embeddings (card2vec substrate), game-neutral.

Learns a dense vector per item purely from which items appear together in the
same container (cards in decks) — no item content, colours, cost, or text.
This is the classic distributional approach; Levy & Goldberg (2014) showed
that truncated SVD of a PPMI (positive pointwise mutual information) matrix
approximates skip-gram word2vec, so we use PPMI-SVD instead of a sampled
neural objective: it is **deterministic** (no negative-sampling RNG), which
the repo's determinism discipline requires, and needs only numpy/sklearn.

Consumes an item-by-item co-occurrence count matrix and returns L2-normalised
row vectors (cosine-ready). No game-specific ids, names, or modules.

Determinism: ARPACK SVD with a fixed seed, plus a sign canonicalisation
(each component's largest-magnitude entry is forced positive) that removes the
sign ambiguity of singular vectors, so repeated runs on the same matrix return
identical vectors.
"""

from __future__ import annotations

import numpy as np
from sklearn.decomposition import TruncatedSVD

EMBED_SEED = 20260707


def ppmi(cooc: np.ndarray, smoothing: float = 0.75) -> np.ndarray:
    """Positive PMI of a symmetric co-occurrence count matrix.

    Context marginals are raised to ``smoothing`` (Levy & Goldberg's
    context-distribution smoothing, default 0.75) which dampens the pull of
    ubiquitous items (format staples) without a separate down-weighting pass.
    """
    cooc = cooc.astype(np.float64)
    total = cooc.sum()
    if total <= 0:
        return np.zeros_like(cooc)
    row = cooc.sum(axis=1)
    ctx = row ** smoothing
    ctx_total = ctx.sum()
    # PMI = log( P(i,j) / (P(i) * P_smoothed(j)) )
    with np.errstate(divide="ignore", invalid="ignore"):
        expected = np.outer(row / total, ctx / ctx_total)
        pmi = np.log((cooc / total) / expected)
    pmi[~np.isfinite(pmi)] = 0.0
    return np.maximum(pmi, 0.0)


def _canonical_signs(vectors: np.ndarray) -> np.ndarray:
    for k in range(vectors.shape[1]):
        col = vectors[:, k]
        idx = int(np.argmax(np.abs(col)))
        if col[idx] < 0:
            vectors[:, k] = -col
    return vectors


def embed(cooc: np.ndarray, dim: int = 50, smoothing: float = 0.75) -> np.ndarray:
    """PPMI-SVD embedding of a co-occurrence matrix -> (n_items, dim) unit rows.

    ``dim`` is clamped below the matrix rank. Rows that are all-zero (an item
    that never co-occurs) return the zero vector."""
    mat = ppmi(cooc, smoothing)
    k = min(dim, min(mat.shape) - 1)
    if k < 1:
        return np.zeros((mat.shape[0], max(dim, 1)))
    svd = TruncatedSVD(n_components=k, algorithm="arpack", random_state=EMBED_SEED)
    vecs = svd.fit_transform(mat)
    vecs = _canonical_signs(vecs)
    norms = np.linalg.norm(vecs, axis=1, keepdims=True)
    norms[norms == 0] = 1.0
    return vecs / norms


def nearest(vectors: np.ndarray, i: int, k: int = 10) -> list[tuple[int, float]]:
    """Top-k cosine neighbours of item i (excluding itself), for unit rows."""
    sims = vectors @ vectors[i]
    sims[i] = -np.inf
    order = np.argsort(-sims)[:k]
    return [(int(j), float(sims[j])) for j in order]
