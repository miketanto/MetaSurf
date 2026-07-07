"""Clustering stage: HDBSCAN over deck vectors (plan §5 Layer 1).

Runs on the rules-unlabeled remainder in production; in validation it runs on
full slices to measure how well density clustering recovers the rule-defined
archetype structure (V1.1) and flags genuinely new decks (V1.2).

HDBSCAN (sklearn.cluster.HDBSCAN, checked against the installed 1.9.0 API) is
deterministic for a given input matrix and parameters — no RNG is involved —
so determinism (V1.3) reduces to feeding it deterministically ordered vectors.
Noise label -1 = "Rogue". min_cluster_size defaults to 5, matching the V1.2
acceptance criterion ("within 7 days of the deck's first ≥5 appearances").
"""

from __future__ import annotations

import numpy as np
from scipy import sparse
from sklearn.cluster import HDBSCAN

CLUSTERING_SEMANTICS = "hdbscan-cosine-1"
NOISE = -1


def cluster_decks(
    matrix: sparse.csr_matrix,
    min_cluster_size: int = 5,
    min_samples: int | None = None,
) -> np.ndarray:
    """Cluster L2-normalized deck vectors with cosine distance. Returns one
    integer label per row; NOISE (-1) marks outliers ("Rogue")."""
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
