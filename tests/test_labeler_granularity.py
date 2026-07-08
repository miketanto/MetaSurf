"""Variant-granularity labeling: a matched rule variant becomes its own
archetype under archetypes.parent_id, while default (parent) granularity keeps
the V1-validated identity. Tested on a real Broodscale-Eldrazi list against a
Postgres fixture DB (no mocking of the classifier)."""

from __future__ import annotations

import pytest

from archetypes.labeler import label_corpus

pytestmark = pytest.mark.db

# a minimal but genuinely-matching Broodscale Eldrazi mainboard: Eldrazi Temple
# (base gate) + Basking Broodscale (base list card AND the Broodscale variant
# signpost) + Thought-Knot Seer (second base-list card). Real card names.
DECK = {
    "Eldrazi Temple": 4,
    "Basking Broodscale": 4,
    "Thought-Knot Seer": 4,
    "Blade of the Bloodchief": 3,
    "Forest": 12,
}


@pytest.fixture()
def one_eldrazi_deck(db_conn):
    with db_conn.cursor() as cur:
        cur.execute(
            "TRUNCATE ingest_unresolved_cards, archetype_labels, matches, deck_cards,"
            " decks, events, archetypes, cards RESTART IDENTITY CASCADE"
        )
        cur.execute("INSERT INTO games (name) VALUES ('mtg') ON CONFLICT DO NOTHING")
        cur.execute("SELECT id FROM games WHERE name='mtg'")
        game_id = cur.fetchone()[0]
        cur.execute(
            "INSERT INTO formats (game_id, name, config) VALUES (%s,'modern','{}'::jsonb)"
            " ON CONFLICT (game_id, name) DO NOTHING",
            (game_id,),
        )
        cur.execute("SELECT id FROM formats WHERE game_id=%s AND name='modern'", (game_id,))
        format_id = cur.fetchone()[0]
        for i, name in enumerate(DECK):
            cur.execute(
                "INSERT INTO cards (game_id, canonical_ref, name) VALUES (%s,%s,%s)",
                (game_id, f"ref:{i}", name),
            )
        cur.execute(
            "INSERT INTO events (game_id, source, source_event_id, format_id, date, event_type)"
            " VALUES (%s,'mtgo.com','ev1',%s,'2026-07-04','challenge-32') RETURNING id",
            (game_id, format_id),
        )
        event_id = cur.fetchone()[0]
        cur.execute(
            "INSERT INTO decks (event_id, player) VALUES (%s,'tester') RETURNING id",
            (event_id,),
        )
        deck_id = cur.fetchone()[0]
        for name, count in DECK.items():
            cur.execute("SELECT id FROM cards WHERE name=%s", (name,))
            cid = cur.fetchone()[0]
            cur.execute(
                "INSERT INTO deck_cards (deck_id, card_id, count, board) VALUES (%s,%s,%s,'main')",
                (deck_id, cid, count),
            )
    db_conn.commit()
    return db_conn, deck_id


def _label_name(conn, deck_id):
    with conn.cursor() as cur:
        cur.execute(
            "SELECT a.name FROM decks d JOIN archetypes a ON a.id=d.archetype_id WHERE d.id=%s",
            (deck_id,),
        )
        return cur.fetchone()[0]


def test_parent_granularity_labels_eldrazi(one_eldrazi_deck):
    conn, deck_id = one_eldrazi_deck
    label_corpus(conn, "modern", granularity="parent")
    assert _label_name(conn, deck_id) == "Eldrazi"
    with conn.cursor() as cur:
        cur.execute("SELECT count(*) FROM archetypes WHERE parent_id IS NOT NULL")
        assert cur.fetchone()[0] == 0  # no splits at parent granularity


def test_variant_granularity_splits_to_broodscale_under_eldrazi(one_eldrazi_deck):
    conn, deck_id = one_eldrazi_deck
    label_corpus(conn, "modern", granularity="variant")
    assert _label_name(conn, deck_id) == "Broodscale"
    with conn.cursor() as cur:
        # Broodscale is a child of Eldrazi via parent_id (plan §4 split seam)
        cur.execute(
            """
            SELECT p.name FROM archetypes c JOIN archetypes p ON p.id=c.parent_id
            WHERE c.name='Broodscale'
            """
        )
        assert cur.fetchone()[0] == "Eldrazi"


def test_variant_granularity_is_deterministic(one_eldrazi_deck):
    conn, deck_id = one_eldrazi_deck
    label_corpus(conn, "modern", granularity="variant")
    first = _label_name(conn, deck_id)
    label_corpus(conn, "modern", granularity="variant")
    assert _label_name(conn, deck_id) == first == "Broodscale"
