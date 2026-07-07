"""Vectorizer + clustering-stage tests on real fixture decks (the 25 decks of
the 2016-03-23 Modern daily swiss, tests/fixtures/MTGODecklistCache). Card ids
are a deterministic enumeration of the fixture's card names — the vectorizer
is id-agnostic; production uses cards.id."""

from __future__ import annotations

import numpy as np
import orjson

from archetypes.classifier.clustering import NOISE, cluster_decks
from archetypes.classifier.vectorizer import vectorize
from tests.conftest import FIXTURES

FIXTURE_2016 = (
    FIXTURES
    / "Tournaments/mtgo.com/2016/03/23/modern-daily-swiss-2016-03-239485836.json"
)


def _fixture_decks():
    data = orjson.loads(FIXTURE_2016.read_bytes())
    name_ids: dict[str, int] = {}
    decks: list[tuple[int, dict[int, int]]] = []
    players: list[str] = []
    for i, deck in enumerate(data["Decks"]):
        cards: dict[int, int] = {}
        for e in deck["Mainboard"]:
            cid = name_ids.setdefault(e["CardName"], len(name_ids) + 1)
            cards[cid] = cards.get(cid, 0) + e["Count"]
        decks.append((i, cards))
        players.append(deck["Player"])
    return decks, players, name_ids


def test_vectorize_exclusions_shape_and_idf():
    decks, _, name_ids = _fixture_decks()
    island = name_ids["Island"]
    vecs = vectorize(decks, exclude_card_ids=frozenset({island}))

    assert len(vecs.deck_ids) == 25
    assert island not in vecs.card_ids
    # rows are L2-normalized
    norms = np.sqrt(np.asarray(vecs.matrix.multiply(vecs.matrix).sum(axis=1)).ravel())
    assert np.allclose(norms[norms > 0], 1.0)

    # ubiquitous staples get down-weighted below rare cards: in this real
    # event, Lightning Bolt appears in far more decks than Goryo's Vengeance
    col = {cid: i for i, cid in enumerate(vecs.card_ids)}
    bolt, goryo = name_ids["Lightning Bolt"], name_ids["Goryo's Vengeance"]
    assert vecs.idf[col[bolt]] < vecs.idf[col[goryo]]


def test_clustering_deterministic_and_groups_real_affinity_decks():
    decks, players, name_ids = _fixture_decks()
    vecs = vectorize(decks, exclude_card_ids=frozenset({name_ids["Island"]}))

    labels1 = cluster_decks(vecs.matrix, min_cluster_size=2)
    labels2 = cluster_decks(vecs.matrix, min_cluster_size=2)
    assert (labels1 == labels2).all()  # V1.3: fully deterministic

    by_player = dict(zip(players, labels1, strict=True))
    # the two hand-verified Affinity lists (see test_rules_engine) must share
    # a non-noise cluster
    assert by_player["ArcaCrema"] == by_player["snapcaster____mage"] != NOISE


def test_tiny_input_is_all_noise():
    decks, _, _ = _fixture_decks()
    vecs = vectorize(decks[:3])
    assert (cluster_decks(vecs.matrix, min_cluster_size=5) == NOISE).all()


def test_attach_noise_thresholds():
    from archetypes.classifier.clustering import attach_noise

    decks, _, name_ids = _fixture_decks()
    vecs = vectorize(decks, exclude_card_ids=frozenset({name_ids["Island"]}))
    base = cluster_decks(vecs.matrix, min_cluster_size=2)
    n_noise = int((base == NOISE).sum())
    assert n_noise > 0  # observed: 6 noise decks in this real event

    # impossible threshold: nothing attaches, labels unchanged
    same = attach_noise(vecs.matrix, base, tau=1.01)
    assert (same == base).all()

    # zero threshold: every noise deck attaches to its nearest centroid
    all_in = attach_noise(vecs.matrix, base, tau=0.0)
    assert int((all_in == NOISE).sum()) == 0
    # attachment never relabels clustered decks
    assert (all_in[base != NOISE] == base[base != NOISE]).all()

    # attachment is deterministic
    assert (attach_noise(vecs.matrix, base, tau=0.3)
            == attach_noise(vecs.matrix, base, tau=0.3)).all()
