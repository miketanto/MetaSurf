"""Batch-labeler tests against the real fixture corpus in a real database.

The engine itself is validated in test_rules_engine.py / the V1 suite; these
tests cover the persistence plumbing: every non-empty deck gets exactly one
label per classifier_version, decks.archetype_id is set, re-running is
idempotent, and the DQ gates hold.
"""

from __future__ import annotations

import orjson
import pytest

from archetypes.labeler import ROGUE_NAME, label_corpus
from ingest.cache_import.importer import run_import
from tests.conftest import FIXTURES

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


def test_every_nonempty_deck_labeled(imported_conn):
    stats = label_corpus(imported_conn)

    with imported_conn.cursor() as cur:
        cur.execute("SELECT count(*) FROM decks")
        n_decks = cur.fetchone()[0]
        cur.execute(
            "SELECT count(*) FROM decks d"
            " WHERE EXISTS (SELECT 1 FROM deck_cards dc WHERE dc.deck_id = d.id)"
        )
        n_nonempty = cur.fetchone()[0]
        cur.execute("SELECT count(*) FROM archetype_labels")
        n_labels = cur.fetchone()[0]
        cur.execute("SELECT count(*) FROM decks WHERE archetype_id IS NOT NULL")
        n_set = cur.fetchone()[0]

    assert stats.decks_labeled == n_nonempty == n_labels == n_set
    assert stats.decks_without_cards == n_decks - n_nonempty
    assert stats.classifier_version
    # methods are the classifier's vocabulary only
    assert set(stats.by_method) <= {"rules", "fallback", "rogue"}
    # the melee no-submit fixture guarantees unclassifiable decks exist
    assert stats.by_method["rogue"] > 0

    with imported_conn.cursor() as cur:
        cur.execute("SELECT count(*) FROM archetypes WHERE name = %s", (ROGUE_NAME,))
        assert cur.fetchone()[0] == 1
        # confidence: 1.0 for rules, (0,1] for fallback, NULL for rogue
        cur.execute(
            "SELECT count(*) FROM archetype_labels"
            " WHERE method = 'rules' AND confidence IS DISTINCT FROM 1.0"
        )
        assert cur.fetchone()[0] == 0
        cur.execute(
            "SELECT count(*) FROM archetype_labels WHERE method = 'rogue'"
            " AND confidence IS NOT NULL"
        )
        assert cur.fetchone()[0] == 0


def test_relabeling_same_version_is_idempotent(imported_conn):
    stats1 = label_corpus(imported_conn)
    snap1 = _label_snapshot(imported_conn)
    stats2 = label_corpus(imported_conn)
    assert _label_snapshot(imported_conn) == snap1
    assert stats1.summary() == stats2.summary()


def _label_snapshot(conn) -> list:
    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT al.deck_id, a.name, al.classifier_version, al.method, al.confidence
            FROM archetype_labels al JOIN archetypes a ON a.id = al.archetype_id
            ORDER BY al.deck_id, al.classifier_version
            """
        )
        labels = cur.fetchall()
        cur.execute("SELECT id, archetype_id, classifier_version FROM decks ORDER BY id")
        decks = cur.fetchall()
    return [labels, decks]
