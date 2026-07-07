"""Clustering stage: HDBSCAN over deck vectors + nearest-centroid noise
attachment (plan §5 Layer 1).

Runs on the rules-unlabeled remainder in production; in validation it runs on
full slices to measure how well density clustering recovers the rule-defined
archetype structure (V1.1) and flags genuinely new decks (V1.2).

Hyperparameters were frozen on the TUNING month 2023-03 (disjoint from the
V1.1 holdout 2024-01) by a grid sweep over min_cluster_size {5,10,25} x
min_samples {1,None} x selection method {eom,leaf} x attachment tau
{None,0.5,0.4,0.3,0.2}, scored with the V1.1 agreement metric:
raw HDBSCAN left 40% of decks in noise (agreement 0.58); attaching each noise
deck to its nearest cluster centroid when cosine similarity >= tau recovers
them (best tuning-month score: min_cluster_size=5, min_samples=1, eom,
tau=0.3 -> agreement 0.9925, worst established-archetype F1 0.933, noise 85
of 8,185). Decks below tau stay NOISE (-1) = "Rogue", preserving the
outliers-are-Rogue semantics. cluster_selection_epsilon is unusable in the
installed sklearn 1.9.0 (TypeError in _tree.epsilon_search when > 0).

HDBSCAN (sklearn.cluster.HDBSCAN, checked against the installed 1.9.0 API)
and the attachment step are deterministic for a given input matrix — no RNG —
so determinism (V1.3) reduces to feeding deterministically ordered vectors.
min_cluster_size=5 matches the V1.2 acceptance criterion ("within 7 days of
the deck's first >= 5 appearances").
"""

from __future__ import annotations

import numpy as np
from scipy import sparse
from sklearn.cluster import HDBSCAN

CLUSTERING_SEMANTICS = "hdbscan-cosine-attach-1"
NOISE = -1

MIN_CLUSTER_SIZE = 5
MIN_SAMPLES = 1
ATTACH_TAU = 0.3


def cluster_decks(
    matrix: sparse.csr_matrix,
    min_cluster_size: int = MIN_CLUSTER_SIZE,
    min_samples: int | None = MIN_SAMPLES,
) -> np.ndarray:
    """Raw HDBSCAN stage on L2-normalized deck vectors with cosine distance.
    Returns one integer label per row; NOISE (-1) marks outliers."""
    if matrix.shape[0] < min_cluster_size:
        return np.full(matrix.shape[0], NOISE, dtype=int)
    model = HDBSCAN(
        min_cluster_size=min_cluster_size,
        min_samples=min_samples,
        metric="cosine",
        algorithm="brute",  # cosine requires brute; also fully deterministic
        copy=True,
    )
    labels: np.ndarray = model.fit_predict(matrix)
    return labels.astype(int)


def attach_noise(
    matrix: sparse.csr_matrix, labels: np.ndarray, tau: float = ATTACH_TAU
) -> np.ndarray:
    """Attach noise rows to their nearest cluster centroid when the cosine
    similarity is >= tau; rows below tau stay NOISE ("Rogue"). Rows must be
    L2-normalized (as produced by the vectorizer)."""
    labels = labels.copy()
    clusters = sorted(set(labels.tolist()) - {NOISE})
    noise_idx = np.where(labels == NOISE)[0]
    if not clusters or len(noise_idx) == 0:
        return labels
    centroids = np.vstack(
        [np.asarray(matrix[labels == cl].mean(axis=0)).ravel() for cl in clusters]
    )
    norms = np.linalg.norm(centroids, axis=1)
    norms[norms == 0] = 1.0
    centroids /= norms[:, None]
    sims = np.asarray(matrix[noise_idx] @ centroids.T)
    best = sims.argmax(axis=1)
    best_sim = sims.max(axis=1)
    for i, b, s in zip(noise_idx, best, best_sim, strict=True):
        if s >= tau:
            labels[i] = clusters[int(b)]
    return labels


def cluster_and_attach(
    matrix: sparse.csr_matrix,
    min_cluster_size: int = MIN_CLUSTER_SIZE,
    min_samples: int | None = MIN_SAMPLES,
    tau: float = ATTACH_TAU,
) -> np.ndarray:
    """The full clustering stage as validated: HDBSCAN + noise attachment."""
    return attach_noise(matrix, cluster_decks(matrix, min_cluster_size, min_samples), tau)
