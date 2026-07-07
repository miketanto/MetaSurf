"""End-to-end importer tests against the real fixture corpus and a real
Postgres database (only the card table content is synthetic: rows are seeded
from card names that occur in the fixtures, with clearly-synthetic
canonical_refs — production canonical_refs come from Scryfall bulk data)."""

from __future__ import annotations

import orjson
import pytest

from ingest.cache_import.importer import run_import
from tests.conftest import FIXTURES

pytestmark = pytest.mark.db

# a real card name present in the 2016 fixture, deliberately NOT seeded into
# the cards table so unresolved logging is exercised
HOLDOUT_NAME = "Ancient Stirrings"


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
def seeded_conn(db_conn):
    with db_conn.cursor() as cur:
        cur.execute(
            "TRUNCATE ingest_unresolved_cards, archetype_labels, matches, deck_cards,"
            " decks, events, cards RESTART IDENTITY CASCADE"
        )
        cur.execute("INSERT INTO games (name) VALUES ('mtg') ON CONFLICT DO NOTHING")
        cur.execute("SELECT id FROM games WHERE name = 'mtg'")
        game_id = cur.fetchone()[0]
        names = sorted(_fixture_card_names() - {HOLDOUT_NAME})
        cur.executemany(
            "INSERT INTO cards (game_id, canonical_ref, name) VALUES (%s, %s, %s)",
            [(game_id, f"test-ref:{i}", n) for i, n in enumerate(names)],
        )
    db_conn.commit()
    return db_conn


def test_full_fixture_import(seeded_conn):
    stats = run_import(seeded_conn, FIXTURES)

    # fixture corpus: 12 files; 1 has no format token (2019 MOCS open),
    # 1 is a duplicate league re-publication -> 10 imported
    assert stats.files_seen == 12
    assert stats.files_skipped_format_unknown == 1
    assert stats.files_skipped_duplicate == 1
    assert stats.files_skipped_other_format == 0
    assert stats.files_imported == 10
    assert stats.events == 10
    # the 2022 melee Dallas fixture carries 2 literal Count:0 card entries
    assert stats.zero_count_card_lines == 2

    with seeded_conn.cursor() as cur:
        cur.execute("SELECT count(*) FROM events")
        assert cur.fetchone()[0] == 10
        cur.execute("SELECT count(*) FROM deck_cards WHERE count < 1")
        assert cur.fetchone()[0] == 0
        cur.execute("SELECT count(*) FROM decks")
        n_decks = cur.fetchone()[0]
        assert n_decks == stats.decks > 0
        cur.execute("SELECT count(*) FROM deck_cards")
        assert cur.fetchone()[0] == stats.deck_card_rows > 0
        # M2 scope: no matches in M0
        cur.execute("SELECT count(*) FROM matches")
        assert cur.fetchone()[0] == 0


def test_unresolved_cards_logged_never_guessed(seeded_conn):
    run_import(seeded_conn, FIXTURES)
    with seeded_conn.cursor() as cur:
        cur.execute("SELECT card_name, occurrences, decks_affected FROM ingest_unresolved_cards")
        rows = cur.fetchall()
    assert len(rows) == 1
    name, occurrences, decks_affected = rows[0]
    assert name == HOLDOUT_NAME
    assert occurrences > 0 and decks_affected > 0
    # and the holdout name must not have been inserted as a card
    with seeded_conn.cursor() as cur:
        cur.execute("SELECT count(*) FROM cards WHERE name = %s", (HOLDOUT_NAME,))
        assert cur.fetchone()[0] == 0


def test_import_is_deterministic_across_rebuilds(seeded_conn):
    stats1 = run_import(seeded_conn, FIXTURES)
    snap1 = _snapshot(seeded_conn)
    # wipe event data (keep cards), resetting id sequences so ids are reproduced
    with seeded_conn.cursor() as cur:
        cur.execute(
            "TRUNCATE ingest_unresolved_cards, deck_cards, decks, events"
            " RESTART IDENTITY CASCADE"
        )
    seeded_conn.commit()
    stats2 = run_import(seeded_conn, FIXTURES)
    assert _snapshot(seeded_conn) == snap1
    assert stats1.summary() == stats2.summary()


def test_import_refuses_empty_cards_table(db_conn):
    with db_conn.cursor() as cur:
        cur.execute(
            "TRUNCATE ingest_unresolved_cards, deck_cards, decks, events, cards"
            " RESTART IDENTITY CASCADE"
        )
    db_conn.commit()
    with pytest.raises(RuntimeError, match="cards table is empty"):
        run_import(db_conn, FIXTURES)


def _snapshot(conn) -> list:
    out = []
    with conn.cursor() as cur:
        cur.execute(
            "SELECT source, source_event_id, format_id, name, date, event_type,"
            " player_count, raw_ref FROM events ORDER BY id"
        )
        out.append(cur.fetchall())
        cur.execute(
            "SELECT event_id, player, finish_rank, wins, losses, draws FROM decks ORDER BY id"
        )
        out.append(cur.fetchall())
        cur.execute("SELECT deck_id, card_id, count, board FROM deck_cards ORDER BY 1, 2, 4")
        out.append(cur.fetchall())
    return out
