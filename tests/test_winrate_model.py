"""Winrate-model tests on a real historical slice (the fixture corpus run
through the real import -> label -> extract pipeline; CLAUDE.md forbids
synthetic-only model tests). A few pure property tests on tiny hand-built
inputs are added on top, never instead.
"""

from __future__ import annotations

import numpy as np
import orjson
import pytest

from archetypes.labeler import label_corpus
from ingest.cache_import.importer import run_import
from ingest.match_extract import extract_matches
from models.winrate import UNKNOWN, MatchData, WinrateModel
from tests.conftest import FIXTURES
from validation.v2_winrates.data import load_match_data, n_archetype_slots

pytestmark = pytest.mark.db


def _fixture_card_names() -> set[str]:
    names: set[str] = set()
    for path in sorted((FIXTURES / "Tournaments").glob("*/*/*/*/*.json")):
        data = orjson.loads(path.read_bytes())
        for deck in data.get("Decks") or []:
            for zone in ("Mainboard", "Sideboard"):
                for entry in deck.get(zone) or []:
                    names.add(entry["CardName"])
    return names


@pytest.fixture(scope="module")
def real_slice(test_db_url):
    """MatchData from the fixture corpus via the real pipeline."""
    import psycopg

    with psycopg.connect(test_db_url) as conn:
        with conn.cursor() as cur:
            cur.execute(
                "TRUNCATE ingest_unresolved_cards, archetype_labels, matches, deck_cards,"
                " decks, events, archetypes, cards RESTART IDENTITY CASCADE"
            )
            cur.execute("INSERT INTO games (name) VALUES ('mtg') ON CONFLICT DO NOTHING")
            cur.execute("SELECT id FROM games WHERE name = 'mtg'")
            game_id = cur.fetchone()[0]
            names = sorted(_fixture_card_names())
            cur.executemany(
                "INSERT INTO cards (game_id, canonical_ref, name) VALUES (%s, %s, %s)",
                [(game_id, f"test-ref:{i}", n) for i, n in enumerate(names)],
            )
        conn.commit()
        run_import(conn, FIXTURES)
        label_corpus(conn)
        extract_matches(conn, FIXTURES)
        data, arch_names, stats = load_match_data(conn, "modern")
    return data, arch_names, stats


def test_real_slice_loads_all_matches(real_slice):
    data, arch_names, stats = real_slice
    # 4,999 extracted fixture matches; only both-unlabeled rows may drop
    assert stats.matches_loaded + stats.dropped_both_unlabeled == 4999
    assert stats.matches_loaded > 4900
    assert data.n == stats.matches_loaded
    assert set(np.unique(data.side_a)) <= set(arch_names)


def _fit(real_slice, **kw):
    data, arch_names, _ = real_slice
    n = n_archetype_slots(arch_names)
    as_of = int(data.day.max()) + 1
    model = WinrateModel(**kw)
    return data, n, as_of, model.fit(data, as_of, n)


def test_fit_is_deterministic(real_slice):
    _, _, _, p1 = _fit(real_slice)
    _, _, _, p2 = _fit(real_slice)
    assert p1.format_mean == p2.format_mean
    assert np.array_equal(p1.arch_alpha, p2.arch_alpha)
    assert np.array_equal(p1.pair_wins, p2.pair_wins)


def test_no_future_leak(real_slice):
    data, n, _, _ = _fit(real_slice)
    model = WinrateModel()
    empty = model.fit(data, int(data.day.min()), n)  # nothing strictly before
    assert empty.format_mean == 0.5
    assert np.allclose(empty.archetype_mean(), 0.5)


def test_posterior_means_shrink_toward_format_mean(real_slice):
    data, n, as_of, post = _fit(real_slice)
    # raw decayed rates recomputed independently of the model
    raw_post = WinrateModel(hierarchical=False).fit(data, as_of, n)
    w = raw_post.arch_alpha - 1.0  # flat Beta(1,1) prior contributes exactly 1
    lo = raw_post.arch_beta - 1.0
    seen = (w + lo) > 0
    raw = np.where(seen, w / np.where(w + lo > 0, w + lo, 1.0), 0.5)
    mean = post.archetype_mean()
    # every posterior mean lies between the raw rate and the format mean
    lo_b = np.minimum(raw, post.format_mean) - 1e-12
    hi_b = np.maximum(raw, post.format_mean) + 1e-12
    assert np.all(mean[seen] >= lo_b[seen])
    assert np.all(mean[seen] <= hi_b[seen])


def test_matchup_matrix_is_coherent(real_slice):
    _, n, _, post = _fit(real_slice)
    a, b = np.meshgrid(np.arange(n), np.arange(n), indexing="ij")
    a, b = a.ravel(), b.ravel()
    p_ab = post.match_prob(a, b)
    p_ba = post.match_prob(b, a)
    assert np.allclose(p_ab + p_ba, 1.0, atol=1e-12)
    # mirror cells are exactly one half
    mirror = post.match_prob(np.arange(n), np.arange(n))
    assert np.allclose(mirror, 0.5, atol=1e-12)


def test_unknown_opponent_uses_archetype_mean(real_slice):
    _, n, _, post = _fit(real_slice)
    a = np.arange(n)
    b = np.full(n, UNKNOWN)
    assert np.allclose(post.match_prob(a, b), post.archetype_mean())


def test_intervals_contain_mean_and_narrow_with_evidence(real_slice):
    data, n, _as_of, post = _fit(real_slice)
    lo, hi = post.archetype_interval(0.90)
    mean = post.archetype_mean()
    assert np.all(lo <= mean) and np.all(mean <= hi)
    evidence = np.bincount(data.side_a, minlength=n)
    heavy = int(np.argmax(evidence))
    light = int(np.argmin(evidence))
    assert (hi - lo)[heavy] < (hi - lo)[light]


def test_time_decay_downweights_old_evidence():
    """Property test on a hand-built two-archetype history (in addition to the
    real-slice tests above): archetype 1 won long ago, lost recently."""
    day = np.array([0, 0, 0, 100, 100, 100])
    side_a = np.array([1, 1, 1, 1, 1, 1])
    side_b = np.array([2, 2, 2, 2, 2, 2])
    win = np.array([1.0, 1.0, 1.0, 0.0, 0.0, 0.0])
    data = MatchData(day=day, side_a=side_a, side_b=side_b, win_frac=win)
    decayed = WinrateModel(half_life_days=14.0).fit(data, 101, 3)
    flat = WinrateModel(half_life_days=None).fit(data, 101, 3)
    # without decay the record is 3-3 -> exactly the prior mean; with decay
    # the recent losses dominate
    assert np.isclose(flat.archetype_mean()[1], 0.5)
    assert decayed.archetype_mean()[1] < flat.archetype_mean()[1]
    # and evidence from the far side matches: archetype 2 mirrors archetype 1
    assert np.isclose(
        decayed.archetype_mean()[1] + decayed.archetype_mean()[2], 1.0, atol=1e-12
    )


def test_thin_pairs_shrink_to_archetype_prior():
    """One decisive match between two otherwise 50/50 archetypes must not
    produce an extreme matchup claim."""
    day = np.array([10])
    data = MatchData(
        day=day,
        side_a=np.array([1]),
        side_b=np.array([2]),
        win_frac=np.array([1.0]),
    )
    post = WinrateModel(half_life_days=None, pair_prior_strength=20.0).fit(data, 11, 3)
    p = float(post.match_prob(np.array([1]), np.array([2]))[0])
    assert 0.5 < p < 0.65  # far from the raw 1.0
