"""Match-extraction tests against the real fixture corpus in a real database.

Every expected number below was computed independently from the fixture bytes
(see the observed-schema note's Rounds/Matches deep-dive): the fixture corpus
contains 8 imported rounds-bearing events with 5,011 match entries, of which
4,999 become rows (10 byes, 1 mirrored duplicate pair, 1 match with neither
player's deck published).
"""

from __future__ import annotations

import orjson
import pytest

from ingest.cache_import.importer import run_import
from ingest.match_extract import extract_matches, parse_match_result
from tests.conftest import FIXTURES

pytestmark = pytest.mark.db


def test_parse_match_result():
    r = parse_match_result("2-1-0")
    assert r is not None and (r.wins, r.losses, r.draws) == (2, 1, 0)
    assert r.inverted().canonical() == "1-2-0"
    assert parse_match_result("0-0-3").inverted().canonical() == "0-0-3"
    assert parse_match_result("") is None
    assert parse_match_result(None) is None
    assert parse_match_result("5-0") is None  # league record shape, not a match
    assert parse_match_result("1st Place") is None


def _fixture_card_names() -> set[str]:
    names: set[str] = set()
    for path in sorted((FIXTURES / "Tournaments").glob("*/*/*/*/*.json")):
        data = orjson.loads(path.read_bytes())
        for deck in data.get("Decks") or []:
            for zone in ("Mainboard", "Sideboard"):
                for entry in deck.get(zone) or []:
                    names.add(entry["CardName"])
    return names


@pytest.fixture()
def imported_conn(db_conn):
    with db_conn.cursor() as cur:
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
    db_conn.commit()
    run_import(db_conn, FIXTURES)
    return db_conn


def test_extraction_counts_match_fixture_ground_truth(imported_conn):
    stats = extract_matches(imported_conn, FIXTURES)

    assert stats.events_seen == 12
    assert stats.events_with_rounds == 8
    assert stats.events_without_rounds == 4  # daily-swiss, preliminary, 2 leagues
    assert stats.matches_seen == 5011
    assert stats.matches_inserted == 4999
    assert stats.byes_skipped == 10  # 5 manatraders (Player2 null) + 5 topdeck ("")
    assert stats.duplicates_skipped == 1  # prague: mirrored 0-0-1 draw
    assert stats.self_matches_skipped == 0
    assert stats.invalid_results_skipped == 0
    assert stats.matches_both_sides_unresolved == 1  # manatraders
    assert stats.sides_swapped == 78
    assert stats.deck_b_unresolved == 216
    assert stats.unmatched_player_slots == 218
    assert stats.ambiguous_player_slots == 16  # showdown: 'Cesar Hernandez' x2 decks
    assert dict(stats.unmatched_by_source) == {
        "manatraders.com": 30,
        "melee.gg": 182,
        "topdeck.gg": 6,
    }

    with imported_conn.cursor() as cur:
        cur.execute("SELECT count(*) FROM matches")
        assert cur.fetchone()[0] == 4999
        cur.execute("SELECT count(*) FROM matches WHERE deck_id_b IS NULL")
        assert cur.fetchone()[0] == 216
        # league events must never produce matches (winner-censored)
        cur.execute(
            "SELECT count(*) FROM matches m JOIN events e ON e.id = m.event_id"
            " WHERE e.event_type LIKE '%league%'"
        )
        assert cur.fetchone()[0] == 0


def test_mtgo_challenge_bracket_extracted_verbatim(imported_conn):
    """The 2020-03-21 challenge fixture: exactly its 7 Top-8 bracket matches,
    result always from deck_id_a's perspective."""
    extract_matches(imported_conn, FIXTURES)
    with imported_conn.cursor() as cur:
        cur.execute(
            """
            SELECT m.round, a.player, b.player, m.result
            FROM matches m
            JOIN events e ON e.id = m.event_id
            JOIN decks a ON a.id = m.deck_id_a
            JOIN decks b ON b.id = m.deck_id_b
            WHERE e.source_event_id = 'modern-challenge-2020-03-2112110950'
            ORDER BY m.id
            """
        )
        rows = cur.fetchall()
    assert rows == [
        ("Quarterfinals", "nahuel10", "tia05", "2-0-0"),
        ("Quarterfinals", "albert62", "Jenara19", "2-1-0"),
        ("Quarterfinals", "stainerson", "remf", "2-1-0"),
        ("Quarterfinals", "SCJ", "_IlNano_", "2-0-0"),
        ("Semifinals", "albert62", "SCJ", "2-0-0"),
        ("Semifinals", "nahuel10", "stainerson", "2-0-0"),
        ("Finals", "albert62", "nahuel10", "2-1-0"),
    ]


def test_topdeck_numeric_rounds_and_match_level_results(imported_conn):
    extract_matches(imported_conn, FIXTURES)
    with imported_conn.cursor() as cur:
        cur.execute(
            """
            SELECT DISTINCT m.round FROM matches m
            JOIN events e ON e.id = m.event_id WHERE e.source = 'topdeck.gg'
            """
        )
        rounds = {r[0] for r in cur.fetchall()}
        assert rounds <= {"1", "2", "3", "4", "5", "Top 8", "Top 4", "Top 2"}
        assert "1" in rounds
        cur.execute(
            """
            SELECT DISTINCT m.result FROM matches m
            JOIN events e ON e.id = m.event_id WHERE e.source = 'topdeck.gg'
            """
        )
        results = {r[0] for r in cur.fetchall()}
        # match-level encoding, both orientations (0-1-0 arises from swaps)
        assert results <= {"1-0-0", "0-1-0", "0-0-1"}


def test_extraction_is_deterministic_and_replaces(imported_conn):
    stats1 = extract_matches(imported_conn, FIXTURES)
    snap1 = _match_snapshot(imported_conn)
    stats2 = extract_matches(imported_conn, FIXTURES)
    assert _match_snapshot(imported_conn) == snap1  # replaced, not duplicated
    assert stats1.summary() == stats2.summary()


def _match_snapshot(conn) -> list:
    with conn.cursor() as cur:
        cur.execute(
            "SELECT event_id, round, deck_id_a, deck_id_b, result FROM matches"
            " ORDER BY event_id, round, deck_id_a"
        )
        return cur.fetchall()
