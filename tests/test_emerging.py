"""Emerging-cluster characterizer + rollup_emerging writer, against the real
fixture corpus in a real database.

Mirrors test_rollup_jobs.py: the fixture pipeline (import -> label -> match
extract) is validated by its own suites; these tests cover the emerging
builder on top of it. Every expected value is recomputed independently (SQL or
the deterministic characterizer output), never copied from a report.

Fixture facts used below: the latest event date is 2025-01-26; the 30-day
default window has too few unlabeled decks to cluster, so these tests use a
wider window (a builder parameter) to exercise real clusters — the corpus's
Rogue/unlabeled pool over ~13 months yields dense clusters with match data.
2016-01-01 predates all fixture events (empty-window edge case).
"""

from __future__ import annotations

import datetime as dt

import orjson
import psycopg
import pytest

from archetypes.classifier.clustering import NOISE, cluster_and_attach
from archetypes.classifier.corpus import basic_land_ids, load_decks, load_definitions
from archetypes.classifier.engine import Deck, deck_color
from archetypes.classifier.vectorizer import vectorize
from archetypes.emerging import (
    MIN_CLUSTER_DECKS,
    build_emerging,
    characterize,
)
from archetypes.labeler import label_corpus
from ingest.cache_import.importer import run_import
from ingest.match_extract import extract_matches
from tests.conftest import FIXTURES

pytestmark = pytest.mark.db

GAME = "mtg"
FORMAT = "modern"
WINDOW = 400  # wide enough that the fixture's unlabeled pool forms clusters


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
def corpus_conn(test_db_url):
    conn = psycopg.connect(test_db_url)
    with conn.cursor() as cur:
        cur.execute(
            "TRUNCATE rollup_emerging_signature, rollup_emerging, ingest_unresolved_cards,"
            " archetype_labels, matches, deck_cards, decks, events, archetypes, cards"
            " RESTART IDENTITY CASCADE"
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
    yield conn
    conn.close()


@pytest.fixture(scope="module")
def as_of(corpus_conn) -> dt.date:
    with corpus_conn.cursor() as cur:
        cur.execute("SELECT max(date) FROM events")
        latest = cur.fetchone()[0]
    assert latest == dt.date(2025, 1, 26)  # frozen fixture fact
    return latest


def _rows(conn, sql: str, params: tuple = ()) -> list[tuple]:
    with conn.cursor() as cur:
        cur.execute(sql, params)
        return cur.fetchall()


# ------------------------------------------------------------ detect + characterize


def test_characterize_finds_real_clusters(corpus_conn, as_of):
    clusters = characterize(corpus_conn, FORMAT, as_of, window_days=WINDOW)
    assert clusters, "the corpus's unlabeled pool should form >= 1 cluster"

    # every characterized cluster is a genuine density cluster of unlabeled decks
    for c in clusters:
        assert c.n_decks >= MIN_CLUSTER_DECKS
        assert c.n_decks == len(set(c.deck_ids))
        assert 0 <= c.recent_decks <= c.n_decks
        assert c.color  # non-empty WUBRG string or 'C'
        # provisional descriptors are flagged unnamed (CLAUDE.md rule 4)
        assert c.provisional_descriptor.startswith("Unnamed:")
        # signatures are ranked by lift desc and are genuinely in-cluster cards
        lifts = [s.lift for s in c.signature_cards]
        assert lifts == sorted(lifts, reverse=True)
        for s in c.signature_cards:
            assert 0.5 <= s.in_cluster_freq <= 1.0
            assert s.in_cluster_freq > s.out_cluster_freq
            assert s.lift == pytest.approx(s.in_cluster_freq / max(s.out_cluster_freq, 0.01))

    # ordering contract: size desc, then first_seen, then cluster_key
    keys = [(-c.n_decks, c.first_seen, c.cluster_key) for c in clusters]
    assert keys == sorted(keys)


def test_characterized_clusters_are_unlabeled_by_rules(corpus_conn, as_of):
    """The detected clusters come from the Rogue/unlabeled pool: none of their
    member decks is given a specific *rule* label by the definitions."""
    clusters = characterize(corpus_conn, FORMAT, as_of, window_days=WINDOW)
    defs, _ = load_definitions(corpus_conn, format_name=FORMAT)
    first = as_of - dt.timedelta(days=WINDOW)
    by_id = {d.deck_id: d for d in load_decks(corpus_conn, first, as_of, FORMAT)}
    from archetypes.classifier.engine import classify

    for c in clusters:
        for did in c.deck_ids:
            res = classify(by_id[did].deck, defs)
            assert not (res.match is not None and res.match.method == "rules")


def test_cluster_membership_matches_validated_stage(corpus_conn, as_of):
    """The builder's clusters must be exactly the validated cluster_and_attach
    output on the same pool — the feed reuses the stage, not a fork of it."""
    from archetypes.classifier.engine import classify

    defs, _ = load_definitions(corpus_conn, format_name=FORMAT)
    first = as_of - dt.timedelta(days=WINDOW)
    decks = load_decks(corpus_conn, first, as_of, FORMAT)
    pool = [
        d
        for d in decks
        if not (
            (m := classify(d.deck, defs).match) is not None and m.method == "rules"
        )
    ]
    exclude = basic_land_ids(corpus_conn)
    vectors = vectorize([(d.deck_id, d.deck.main) for d in pool], exclude)
    labels = cluster_and_attach(vectors.matrix)
    expected: dict[int, set[int]] = {}
    for did, cl in zip(vectors.deck_ids, labels, strict=True):
        if int(cl) != NOISE:
            expected.setdefault(int(cl), set()).add(did)
    expected = {k: v for k, v in expected.items() if len(v) >= MIN_CLUSTER_DECKS}

    clusters = characterize(corpus_conn, FORMAT, as_of, window_days=WINDOW)
    got = {c.cluster_key: set(c.deck_ids) for c in clusters}
    assert got == expected


def test_cluster_color_uses_engine_deck_color(corpus_conn, as_of):
    """Cluster color = engine deck_color over the majority-vote centroid deck."""
    clusters = characterize(corpus_conn, FORMAT, as_of, window_days=WINDOW)
    defs, _ = load_definitions(corpus_conn, format_name=FORMAT)
    first = as_of - dt.timedelta(days=WINDOW)
    by_id = {d.deck_id: d for d in load_decks(corpus_conn, first, as_of, FORMAT)}
    for c in clusters:
        n = c.n_decks
        present: dict[int, int] = {}
        for did in c.deck_ids:
            for cid in by_id[did].deck.main:
                present[cid] = present.get(cid, 0) + 1
        centroid = {cid: 1 for cid, k in present.items() if k > n / 2}
        assert c.color == deck_color(Deck(main=centroid, side={}), defs)


def test_cluster_winrate_matches_independent_sql(corpus_conn, as_of):
    """Winrate = cluster wins / decided non-mirror games, recomputed from SQL."""
    clusters = characterize(corpus_conn, FORMAT, as_of, window_days=WINDOW)
    for c in clusters:
        ids = list(c.deck_ids)
        rows = _rows(
            corpus_conn,
            """
            SELECT m.deck_id_a, m.deck_id_b,
                   split_part(m.result,'-',1)::int, split_part(m.result,'-',2)::int
            FROM matches m JOIN events e ON e.id = m.event_id
            WHERE e.date <= %s AND m.result ~ '^[0-9]+-[0-9]+-[0-9]+$'
              AND (m.deck_id_a = ANY(%s) OR m.deck_id_b = ANY(%s))
            """,
            (as_of, ids, ids),
        )
        members = set(ids)
        wins = games = 0
        for a, b, w, losses in rows:
            if w == losses:
                continue
            if (a in members) != (b in members):  # exactly one side is ours
                mine_won = (w > losses) if a in members else (losses > w)
                wins += 1 if mine_won else 0
                games += 1
        assert c.n_match_games == games
        if games == 0:
            assert c.winrate is None
        else:
            assert c.winrate == pytest.approx(wins / games)


# ------------------------------------------------------------ persist


def test_build_writes_rollup_and_signatures(corpus_conn, as_of):
    stats = build_emerging(corpus_conn, GAME, FORMAT, as_of, window_days=WINDOW)
    clusters = characterize(corpus_conn, FORMAT, as_of, window_days=WINDOW)
    assert stats.n_clusters == len(clusters)

    parent = _rows(
        corpus_conn,
        "SELECT cluster_key, provisional_descriptor, color, n_decks, first_seen,"
        " recent_decks, winrate, n_match_games FROM rollup_emerging WHERE as_of = %s"
        " ORDER BY cluster_key",
        (as_of,),
    )
    assert len(parent) == len(clusters)
    by_key = {c.cluster_key: c for c in clusters}
    for key, desc, color, n, first, recent, wr, games in parent:
        c = by_key[key]
        assert (desc, color, n, first, recent, games) == (
            c.provisional_descriptor,
            c.color,
            c.n_decks,
            c.first_seen,
            c.recent_decks,
            c.n_match_games,
        )
        if c.winrate is None:
            assert wr is None
        else:
            assert wr == pytest.approx(c.winrate)

    # child rows: one per signature card, ranked 1..k, FK-cascaded
    sig = _rows(
        corpus_conn,
        "SELECT cluster_key, rank, card_id, in_cluster_freq, out_cluster_freq, lift"
        " FROM rollup_emerging_signature WHERE as_of = %s ORDER BY cluster_key, rank",
        (as_of,),
    )
    expected_sig = sum(len(c.signature_cards) for c in clusters)
    assert len(sig) == expected_sig
    assert stats.rows_written == len(parent) + expected_sig
    for group_ranks in _group_ranks(sig).values():
        assert group_ranks == list(range(1, len(group_ranks) + 1))


def _group_ranks(sig_rows: list[tuple]) -> dict[int, list[int]]:
    out: dict[int, list[int]] = {}
    for key, rank, *_ in sig_rows:
        out.setdefault(key, []).append(rank)
    return out


def test_build_idempotent_and_deterministic(corpus_conn, as_of):
    q_parent = "SELECT * FROM rollup_emerging WHERE as_of = %s ORDER BY cluster_key"
    q_sig = (
        "SELECT * FROM rollup_emerging_signature WHERE as_of = %s"
        " ORDER BY cluster_key, rank"
    )
    build_emerging(corpus_conn, GAME, FORMAT, as_of, window_days=WINDOW)
    first_parent = _rows(corpus_conn, q_parent, (as_of,))
    first_sig = _rows(corpus_conn, q_sig, (as_of,))
    build_emerging(corpus_conn, GAME, FORMAT, as_of, window_days=WINDOW)
    assert _rows(corpus_conn, q_parent, (as_of,)) == first_parent
    assert _rows(corpus_conn, q_sig, (as_of,)) == first_sig


def test_build_empty_window_writes_nothing(corpus_conn, as_of):
    build_emerging(corpus_conn, GAME, FORMAT, as_of, window_days=WINDOW)  # keep snapshot
    empty_day = dt.date(2016, 1, 1)  # predates every fixture event
    stats = build_emerging(corpus_conn, GAME, FORMAT, empty_day, window_days=WINDOW)
    assert stats.rows_written == 0 and stats.n_clusters == 0
    assert _rows(corpus_conn, "SELECT 1 FROM rollup_emerging WHERE as_of = %s", (empty_day,)) == []
    assert _rows(corpus_conn, "SELECT 1 FROM rollup_emerging WHERE as_of = %s", (as_of,))


def test_build_unknown_format_raises(corpus_conn, as_of):
    with pytest.raises(LookupError):
        build_emerging(corpus_conn, GAME, "no-such-format", as_of, window_days=WINDOW)
