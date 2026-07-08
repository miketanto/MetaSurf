"""End-to-end: live-page fixtures -> CacheItem files -> existing importer +
match extractor, against a real Postgres fixture DB.

Proves M4 reuses the canonical pipeline: the mtgo.com parser's output is
ingested by ingest.cache_import.importer and ingest.match_extract with no
source-specific code, incremental re-runs are additive (no unique-constraint
collision), and league pairings never appear (winner-censored).
"""

from __future__ import annotations

from pathlib import Path

import pytest

from ingest.cache_import.importer import (
    FUTURE_DATE_TOLERANCE_DAYS,
    run_import,
    run_post_import_checks,
)
from ingest.match_extract.extractor import extract_matches
from ingest.mtgo_scraper.parse import event_to_cacheitem, extract_decklists_data
from ingest.mtgo_scraper.pipeline import write_cacheitem

pytestmark = pytest.mark.db

FIX = Path(__file__).resolve().parent / "fixtures" / "mtgo.com"
CHALLENGE = FIX / "modern-challenge-32-2026-07-0412846483.html"
LEAGUE = FIX / "modern-league-2026-07-0610847.html"
NO_DECKLISTS = FIX / "modern-challenge-64-2026-07-0212846455-no-decklists.html"


def _build_cache(cache_root: Path) -> None:
    """Parse the three real event fixtures and land them as CacheItem files."""
    for html_path, slug in (
        (CHALLENGE, "modern-challenge-32-2026-07-0412846483"),
        (LEAGUE, "modern-league-2026-07-0610847"),
        (NO_DECKLISTS, "modern-challenge-64-2026-07-0212846455"),
    ):
        data = extract_decklists_data(html_path.read_text(encoding="utf-8", errors="replace"))
        assert data is not None
        write_cacheitem(cache_root, slug, event_to_cacheitem(data))


def _card_names(cache_root: Path) -> set[str]:
    import orjson

    names: set[str] = set()
    for path in cache_root.glob("Tournaments/*/*/*/*/*.json"):
        item = orjson.loads(path.read_bytes())
        for deck in item.get("Decks") or []:
            for zone in ("Mainboard", "Sideboard"):
                for c in deck.get(zone) or []:
                    names.add(c["CardName"])
    return names


@pytest.fixture()
def seeded(db_conn, tmp_path):
    cache_root = tmp_path / "live"
    _build_cache(cache_root)
    with db_conn.cursor() as cur:
        cur.execute(
            "TRUNCATE ingest_unresolved_cards, archetype_labels, matches, deck_cards,"
            " decks, events, cards RESTART IDENTITY CASCADE"
        )
        cur.execute("INSERT INTO games (name) VALUES ('mtg') ON CONFLICT DO NOTHING")
        cur.execute("SELECT id FROM games WHERE name = 'mtg'")
        game_id = cur.fetchone()[0]
        names = sorted(_card_names(cache_root))
        cur.executemany(
            "INSERT INTO cards (game_id, canonical_ref, name) VALUES (%s, %s, %s)",
            [(game_id, f"test-ref:{i}", n) for i, n in enumerate(names)],
        )
    db_conn.commit()
    return db_conn, cache_root


def test_live_events_ingest_through_canonical_pipeline(seeded):
    conn, cache_root = seeded
    stats = run_import(conn, cache_root, only_formats={"modern"}, skip_existing=True)

    # 3 modern events land (challenge w/ decklists, league, challenge w/o)
    assert stats.files_imported == 3
    assert stats.events == 3
    with conn.cursor() as cur:
        cur.execute(
            "SELECT source, source_event_id, event_type FROM events ORDER BY source_event_id"
        )
        rows = cur.fetchall()
    assert {r[0] for r in rows} == {"mtgo.com"}
    types = {r[1]: r[2] for r in rows}
    # event-type derived from the slug by the existing derive_event_type
    assert types["modern-challenge-32-2026-07-0412846483"] == "challenge-32"
    assert types["modern-league-2026-07-0610847"] == "league"

    with conn.cursor() as cur:
        # challenge (32) + league (58) decks; the no-decklists event adds 0
        cur.execute("SELECT count(*) FROM decks")
        assert cur.fetchone()[0] == 32 + 58
        # all deck_cards resolved to real card rows, none with count < 1
        cur.execute("SELECT count(*) FROM deck_cards WHERE count < 1")
        assert cur.fetchone()[0] == 0
        # referential integrity: every deck_card points at a seeded card
        cur.execute(
            "SELECT count(*) FROM deck_cards dc LEFT JOIN cards c ON c.id = dc.card_id"
            " WHERE c.id IS NULL"
        )
        assert cur.fetchone()[0] == 0


def test_reimport_is_additive_no_duplicate_events(seeded):
    conn, cache_root = seeded
    run_import(conn, cache_root, only_formats={"modern"}, skip_existing=True)
    stats2 = run_import(conn, cache_root, only_formats={"modern"}, skip_existing=True)
    # second run finds the same files but imports nothing (dedupe on
    # (source, source_event_id)); no events unique-constraint violation
    assert stats2.events == 0
    assert stats2.files_skipped_existing == 3
    with conn.cursor() as cur:
        cur.execute("SELECT count(*) FROM events")
        assert cur.fetchone()[0] == 3


def test_future_date_gate_tolerates_boundary_but_rejects_garbage(seeded):
    """A next-day league instance (TZ boundary) must pass; a garbage future
    date (parse error) must still fail the DQ gate loudly."""
    conn, cache_root = seeded
    run_import(conn, cache_root, only_formats={"modern"}, skip_existing=True)
    from ingest.cache_import.importer import ImportStats

    with conn.cursor() as cur:
        # within tolerance: one day ahead of the host -> gate passes
        cur.execute(
            "UPDATE events SET date = current_date + 1"
            " WHERE source_event_id = 'modern-league-2026-07-0610847'"
        )
    conn.commit()
    run_post_import_checks(conn, ImportStats())  # no raise

    with conn.cursor() as cur:
        # garbage: far in the future -> gate fails
        cur.execute(
            "UPDATE events SET date = current_date + %s"
            " WHERE source_event_id = 'modern-league-2026-07-0610847'",
            (FUTURE_DATE_TOLERANCE_DAYS + 30,),
        )
    conn.commit()
    with pytest.raises(RuntimeError, match="in the future"):
        run_post_import_checks(conn, ImportStats())


def test_match_extraction_from_challenge_bracket_only(seeded):
    conn, cache_root = seeded
    run_import(conn, cache_root, only_formats={"modern"}, skip_existing=True)
    mstats = extract_matches(conn, cache_root)

    # only the challenge carries Rounds (Top-8 bracket = 4+2+1 = 7 matches);
    # the league is winner-censored (no Rounds) and the no-decklists challenge
    # bracket references players with no deck rows -> unresolved, not matches
    with conn.cursor() as cur:
        cur.execute(
            "SELECT count(*) FROM matches m JOIN events e ON e.id = m.event_id"
            " WHERE e.event_type LIKE '%%league%%'"
        )
        assert cur.fetchone()[0] == 0  # no league matches, ever
        cur.execute("SELECT count(*) FROM matches")
        assert cur.fetchone()[0] == mstats.matches_inserted
        # the challenge-32 with published decklists yields resolvable bracket matches
        cur.execute(
            """
            SELECT count(*) FROM matches m
            JOIN events e ON e.id = m.event_id
            WHERE e.source_event_id = 'modern-challenge-32-2026-07-0412846483'
            """
        )
        assert cur.fetchone()[0] == 7
