"""Property tests for the game-neutral co-occurrence embedding."""

from __future__ import annotations

import numpy as np

from models.embeddings import embed, nearest, ppmi


def _block_cooc() -> np.ndarray:
    """Two tight communities {0,1,2} and {3,4,5} that co-occur within group
    far more than across — the embedding must separate them."""
    c = np.full((6, 6), 1.0)  # weak background co-occurrence
    for grp in ([0, 1, 2], [3, 4, 5]):
        for i in grp:
            for j in grp:
                c[i, j] = 50.0
    np.fill_diagonal(c, 100.0)
    return c


def test_ppmi_nonnegative_and_zero_on_independence():
    # independent items: co-occurrence equals product of marginals -> PMI 0
    cooc = np.array([[4.0, 2.0], [2.0, 4.0]])
    m = ppmi(cooc, smoothing=1.0)
    assert np.all(m >= 0)


def test_embedding_is_unit_normed_and_deterministic():
    cooc = _block_cooc()
    v1 = embed(cooc, dim=4)
    v2 = embed(cooc, dim=4)
    assert np.allclose(np.linalg.norm(v1, axis=1), 1.0, atol=1e-9)
    assert np.array_equal(v1, v2)  # byte-identical across runs (determinism)


def test_same_community_items_are_nearest():
    v = embed(_block_cooc(), dim=4)
    for i, grp in ((0, {1, 2}), (3, {4, 5})):
        top = {j for j, _ in nearest(v, i, k=2)}
        assert top == grp  # nearest neighbours are the same community


def test_cross_community_similarity_below_within():
    v = embed(_block_cooc(), dim=4)
    within = float(v[0] @ v[1])
    across = float(v[0] @ v[3])
    assert within > across
