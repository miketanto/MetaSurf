"""weekend_archetype_counts serves only currently-legal decks: a deck holding a
card explicitly banned/not_legal in the format is excluded (rotation + bans);
missing legality never excludes."""

from __future__ import annotations

import datetime as dt

import pytest

from jobs.rollups.common import weekend_archetype_counts

pytestmark = pytest.mark.db

SAT = dt.date(2026, 6, 6)  # a Saturday (isodow 6)


@pytest.fixture()
def two_decks(db_conn):
    """One legal deck + one deck running a not_legal card, same archetype,
    same weekend event."""
    with db_conn.cursor() as cur:
        cur.execute(
            "TRUNCATE archetype_labels, matches, deck_cards, decks, events, archetypes,"
            " cards RESTART IDENTITY CASCADE"
        )
        cur.execute("INSERT INTO games (name) VALUES ('mtg') ON CONFLICT DO NOTHING")
        cur.execute("SELECT id FROM games WHERE name='mtg'")
        gid = cur.fetchone()[0]
        cur.execute(
            "INSERT INTO formats (game_id, name, config) VALUES (%s,'modern','{}'::jsonb)"
            " ON CONFLICT (game_id,name) DO NOTHING",
            (gid,),
        )
        cur.execute("SELECT id FROM formats WHERE game_id=%s AND name='modern'", (gid,))
        fid = cur.fetchone()[0]
        cur.execute(
            "INSERT INTO archetypes (format_id, name) VALUES (%s,'X') RETURNING id", (fid,)
        )
        aid = cur.fetchone()[0]
        # two cards: one legal, one not_legal in modern
        cur.execute(
            "INSERT INTO cards (game_id, canonical_ref, name, attrs) VALUES"
            " (%s,'r1','Legal Card', '{\"legalities\":{\"modern\":\"legal\"}}'::jsonb),"
            " (%s,'r2','Rotated Card', '{\"legalities\":{\"modern\":\"not_legal\"}}'::jsonb)"
            " RETURNING id",
            (gid, gid),
        )
        legal_cid = cur.fetchall()[0][0]
        cur.execute("SELECT id FROM cards WHERE name='Rotated Card'")
        illegal_cid = cur.fetchone()[0]
        cur.execute(
            "INSERT INTO events (game_id, source, source_event_id, format_id, date, event_type)"
            " VALUES (%s,'t','ev',%s,%s,'challenge') RETURNING id",
            (gid, fid, SAT),
        )
        eid = cur.fetchone()[0]
        for player, cid in (("legal_player", legal_cid), ("illegal_player", illegal_cid)):
            cur.execute(
                "INSERT INTO decks (event_id, player, archetype_id) VALUES (%s,%s,%s) RETURNING id",
                (eid, player, aid),
            )
            did = cur.fetchone()[0]
            cur.execute(
                "INSERT INTO deck_cards (deck_id, card_id, count, board) VALUES (%s,%s,4,'main')",
                (did, cid),
            )
    db_conn.commit()
    return db_conn, fid, aid


def test_not_legal_deck_excluded_from_counts(two_decks):
    conn, fid, aid = two_decks
    counts = weekend_archetype_counts(conn, fid, SAT, SAT, "modern")
    # only the legal deck is counted (the not_legal-card deck is dropped)
    assert counts == {aid: 1}


def test_missing_legality_does_not_exclude(two_decks):
    conn, fid, aid = two_decks
    # strip legality from both cards -> unknown legality must NOT exclude
    with conn.cursor() as cur:
        cur.execute("UPDATE cards SET attrs='{}'::jsonb")
    conn.commit()
    counts = weekend_archetype_counts(conn, fid, SAT, SAT, "modern")
    assert counts == {aid: 2}
