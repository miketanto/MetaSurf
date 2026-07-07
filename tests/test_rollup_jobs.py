"""Rollup-job tests against the real fixture corpus in a real database.

The fixture pipeline (import -> label -> match-extract) is validated by its
own suites; these tests cover the M5 rollup jobs on top of it. Expected
values are recomputed independently with SQL inside each test, never copied
from job output. Fixture facts used below (from the corpus inspection):
the latest event date is 2025-01-26 (a Sunday, 601 decks, rounds-bearing),
so the trailing share window for that snapshot is 2024-12-07..2025-01-26 and
contains exactly that one weekend event; 2016-01-01 predates all fixture
events, giving the empty-window edge case.
"""

from __future__ import annotations

import datetime as dt

import orjson
import psycopg
import pytest

from archetypes.labeler import label_corpus
from ingest.cache_import.importer import run_import
from ingest.match_extract import extract_matches
from jobs.rollups.archetype_ts import build_archetype_ts
from jobs.rollups.best_decks import build_best_decks
from jobs.rollups.common import (
    UNIVERSE_MIN_SHARE,
    trailing_window_start,
    week_saturday,
)
from jobs.rollups.events import build_events
from jobs.rollups.matchups import build_matchups
from jobs.rollups.meta import build_meta
from tests.conftest import FIXTURES

pytestmark = pytest.mark.db

GAME = "mtg"
FORMAT = "modern"


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
    """Imported + labeled + match-extracted fixture corpus, once per module."""
    conn = psycopg.connect(test_db_url)
    with conn.cursor() as cur:
        cur.execute(
            "TRUNCATE rollup_meta, rollup_matchups, rollup_archetype_ts, rollup_best_decks,"
            " rollup_events, ingest_unresolved_cards, archetype_labels, matches, deck_cards,"
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
    yield conn
    conn.close()


@pytest.fixture(scope="module")
def as_of(corpus_conn) -> dt.date:
    with corpus_conn.cursor() as cur:
        cur.execute("SELECT max(date) FROM events")
        latest = cur.fetchone()[0]
    assert latest == dt.date(2025, 1, 26)  # frozen fixture fact
    return latest


def _sql_weekend_counts(conn, first: dt.date, last: dt.date) -> dict[int, int]:
    """Independent recomputation of labeled-weekend-deck counts per archetype."""
    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT d.archetype_id, count(*)
            FROM decks d
            JOIN events e ON e.id = d.event_id
            JOIN formats f ON f.id = e.format_id AND f.name = %s
            WHERE d.archetype_id IS NOT NULL
              AND extract(isodow FROM e.date) IN (6, 7)
              AND e.date BETWEEN %s AND %s
            GROUP BY 1
            """,
            (FORMAT, first, last),
        )
        return {int(a): int(n) for a, n in cur.fetchall()}


def _sql_universe(conn, as_of: dt.date) -> list[int]:
    counts = _sql_weekend_counts(conn, trailing_window_start(as_of), as_of)
    total = sum(counts.values())
    return sorted(a for a, n in counts.items() if total and n / total >= UNIVERSE_MIN_SHARE)


def _rows(conn, sql: str, params: tuple = ()) -> list[tuple]:
    with conn.cursor() as cur:
        cur.execute(sql, params)
        return cur.fetchall()


# ---------------------------------------------------------------- rollup_meta


def test_meta_snapshot_shares_and_intervals(corpus_conn, as_of):
    stats = build_meta(corpus_conn, GAME, FORMAT, as_of)
    rows = _rows(
        corpus_conn,
        "SELECT archetype_id, share, winrate, wr_ci_lo, wr_ci_hi, n_decks"
        " FROM rollup_meta WHERE as_of = %s ORDER BY archetype_id",
        (as_of,),
    )
    assert rows and stats.rows_written == len(rows)

    expected = _sql_weekend_counts(corpus_conn, trailing_window_start(as_of), as_of)
    total = sum(expected.values())
    assert {r[0] for r in rows} == set(expected)
    assert sum(r[5] for r in rows) == total
    assert sum(r[1] for r in rows) == pytest.approx(1.0)
    for arch, share, wr, lo, hi, n_decks in rows:
        assert n_decks == expected[arch]
        assert share == pytest.approx(n_decks / total)
        assert 0.0 < lo <= wr <= hi < 1.0


def test_meta_snapshot_idempotent_and_deterministic(corpus_conn, as_of):
    q = "SELECT * FROM rollup_meta WHERE as_of = %s ORDER BY archetype_id"
    build_meta(corpus_conn, GAME, FORMAT, as_of)
    first = _rows(corpus_conn, q, (as_of,))
    build_meta(corpus_conn, GAME, FORMAT, as_of)
    assert _rows(corpus_conn, q, (as_of,)) == first


def test_meta_snapshot_empty_window_writes_nothing(corpus_conn, as_of):
    build_meta(corpus_conn, GAME, FORMAT, as_of)  # existing snapshot must survive
    empty_day = dt.date(2016, 1, 1)  # predates every fixture event
    stats = build_meta(corpus_conn, GAME, FORMAT, empty_day)
    assert stats.rows_written == 0
    assert _rows(corpus_conn, "SELECT 1 FROM rollup_meta WHERE as_of = %s", (empty_day,)) == []
    assert _rows(corpus_conn, "SELECT 1 FROM rollup_meta WHERE as_of = %s", (as_of,))


def test_meta_snapshot_unknown_format_raises(corpus_conn, as_of):
    with pytest.raises(LookupError):
        build_meta(corpus_conn, GAME, "no-such-format", as_of)


# ------------------------------------------------------------ rollup_matchups


def test_matchup_matrix_covers_universe_and_is_coherent(corpus_conn, as_of):
    stats = build_matchups(corpus_conn, GAME, FORMAT, as_of)
    universe = _sql_universe(corpus_conn, as_of)
    assert len(universe) >= 2  # the snapshot weekend has 601 decks; matrix must be real
    rows = _rows(
        corpus_conn,
        "SELECT arch_a, arch_b, p_a_beats_b, ci_lo, ci_hi, n_matches"
        " FROM rollup_matchups WHERE as_of = %s ORDER BY arch_a, arch_b",
        (as_of,),
    )
    assert stats.rows_written == len(rows) == len(universe) ** 2
    assert {(r[0], r[1]) for r in rows} == {(a, b) for a in universe for b in universe}

    p = {(a, b): v for a, b, v, _, _, _ in rows}
    n = {(a, b): m for a, b, _, _, _, m in rows}
    for a, b, v, lo, hi, _m in rows:
        assert lo <= v <= hi
        assert p[a, b] + p[b, a] == pytest.approx(1.0)
        assert n[a, b] == n[b, a]
        if a == b:
            assert v == pytest.approx(0.5)

    # raw sample sizes recomputed independently (both orientations, <= as_of)
    with corpus_conn.cursor() as cur:
        cur.execute(
            """
            SELECT da.archetype_id, db.archetype_id, count(*)
            FROM matches m
            JOIN events e ON e.id = m.event_id AND e.date <= %s
            JOIN formats f ON f.id = e.format_id AND f.name = %s
            JOIN decks da ON da.id = m.deck_id_a
            JOIN decks db ON db.id = m.deck_id_b
            WHERE da.archetype_id IS NOT NULL AND db.archetype_id IS NOT NULL
            GROUP BY 1, 2
            """,
            (as_of, FORMAT),
        )
        stored: dict[tuple[int, int], int] = {(a, b): c for a, b, c in cur.fetchall()}
    for a in universe:
        for b in universe:
            expect = stored.get((a, b), 0) + (stored.get((b, a), 0) if a != b else 0)
            assert n[a, b] == expect, (a, b)
    # the fixture corpus has real matches between top archetypes
    assert any(m > 0 for m in n.values())


def test_matchups_idempotent(corpus_conn, as_of):
    q = "SELECT * FROM rollup_matchups WHERE as_of = %s ORDER BY arch_a, arch_b"
    build_matchups(corpus_conn, GAME, FORMAT, as_of)
    first = _rows(corpus_conn, q, (as_of,))
    build_matchups(corpus_conn, GAME, FORMAT, as_of)
    assert _rows(corpus_conn, q, (as_of,)) == first


# ---------------------------------------------------------- rollup_best_decks


def test_best_decks_ranking(corpus_conn, as_of):
    build_matchups(corpus_conn, GAME, FORMAT, as_of)
    stats = build_best_decks(corpus_conn, GAME, FORMAT, as_of)
    universe = _sql_universe(corpus_conn, as_of)
    rows = _rows(
        corpus_conn,
        "SELECT rank, archetype_id, exp_winrate_vs_field"
        " FROM rollup_best_decks WHERE as_of = %s ORDER BY rank",
        (as_of,),
    )
    assert stats.rows_written == len(rows) == len(universe)
    assert [r[0] for r in rows] == list(range(1, len(universe) + 1))
    assert {r[1] for r in rows} == set(universe)
    scores = [r[2] for r in rows]
    assert scores == sorted(scores, reverse=True)
    assert all(0.0 < s < 1.0 for s in scores)

    # cross-check each score against rollup_matchups and the latest weekend
    # field, recomputed from SQL: score_a = sum_b P(a beats b) * share_b
    sat = week_saturday(as_of)
    field_counts = _sql_weekend_counts(corpus_conn, sat, as_of)
    field = {a: field_counts.get(a, 0) for a in universe}
    total = sum(field.values())
    assert total > 0
    p = {
        (a, b): v
        for a, b, v in _rows(
            corpus_conn,
            "SELECT arch_a, arch_b, p_a_beats_b FROM rollup_matchups WHERE as_of = %s",
            (as_of,),
        )
    }
    for _rank, arch, score in rows:
        expect = sum(p[arch, b] * field[b] / total for b in universe)
        assert score == pytest.approx(expect)


# -------------------------------------------------------- rollup_archetype_ts


def test_archetype_ts_weekly_panel(corpus_conn, as_of):
    stats = build_archetype_ts(corpus_conn, GAME, FORMAT, as_of)
    rows = _rows(
        corpus_conn,
        "SELECT archetype_id, week, share, winrate, wr_ci_lo, wr_ci_hi, n_decks"
        " FROM rollup_archetype_ts ORDER BY week, archetype_id",
    )
    assert rows and stats.rows_written == len(rows)
    weeks = sorted({r[1] for r in rows})
    assert all(w.isoweekday() == 6 for w in weeks)  # Sat..Fri buckets keyed by Saturday
    assert weeks[-1] <= week_saturday(as_of)

    # each stored week's shares sum to 1 and counts match SQL exactly
    for week in weeks:
        expected = _sql_weekend_counts(corpus_conn, week, week + dt.timedelta(days=1))
        got = {r[0]: r for r in rows if r[1] == week}
        assert {a for a in got} == set(expected)
        assert sum(r[6] for r in got.values()) == sum(expected.values())
        assert sum(r[2] for r in got.values()) == pytest.approx(1.0)
        for arch, r in got.items():
            assert r[6] == expected[arch] > 0  # zero-deck weeks are not stored
            assert 0.0 < r[4] <= r[3] <= r[5] < 1.0

    # the snapshot weekend (2025-01-25 bucket) must be present
    assert week_saturday(as_of) in weeks


def test_archetype_ts_idempotent(corpus_conn, as_of):
    q = "SELECT * FROM rollup_archetype_ts ORDER BY archetype_id, week"
    build_archetype_ts(corpus_conn, GAME, FORMAT, as_of)
    first = _rows(corpus_conn, q)
    build_archetype_ts(corpus_conn, GAME, FORMAT, as_of)
    assert _rows(corpus_conn, q) == first


# -------------------------------------------------------------- rollup_events


def test_events_feed(corpus_conn, as_of):
    stats = build_events(corpus_conn, GAME, FORMAT, as_of)
    rows = _rows(
        corpus_conn,
        "SELECT event_id, date, name, source, player_count, top_archetype_id"
        " FROM rollup_events ORDER BY event_id",
    )
    expected = _rows(
        corpus_conn,
        """
        SELECT e.id, e.date, e.name, e.source, e.player_count,
               (SELECT d.archetype_id FROM decks d
                 WHERE d.event_id = e.id AND d.archetype_id IS NOT NULL
                 ORDER BY d.finish_rank NULLS LAST, d.id LIMIT 1)
        FROM events e
        JOIN formats f ON f.id = e.format_id AND f.name = %s
        WHERE e.date <= %s ORDER BY e.id
        """,
        (FORMAT, as_of),
    )
    assert stats.rows_written == len(rows) == len(expected) > 0
    assert rows == expected
    # every fixture event has at least one labeled deck, so a top archetype
    assert all(r[5] is not None for r in rows)


def test_events_feed_idempotent(corpus_conn, as_of):
    q = "SELECT * FROM rollup_events ORDER BY event_id"
    build_events(corpus_conn, GAME, FORMAT, as_of)
    first = _rows(corpus_conn, q)
    build_events(corpus_conn, GAME, FORMAT, as_of)
    assert _rows(corpus_conn, q) == first
