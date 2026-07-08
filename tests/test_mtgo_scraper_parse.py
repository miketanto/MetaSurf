"""Parser tests for the live mtgo.com/decklists source, run against REAL saved
pages under tests/fixtures/mtgo.com/ (CLAUDE.md parser discipline: inspect
before you parse; test on real fixture bytes + a malformed fixture).

The parser's job is live-page HTML -> CacheItem-shaped dict; the resulting
dicts are then consumed by the existing normalize/import/match-extract code,
which has its own tests. No network, no DB here.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from ingest.mtgo_scraper.parse import (
    MtgoParseError,
    event_to_cacheitem,
    extract_decklists_data,
    parse_listing_slugs,
)

FIX = Path(__file__).resolve().parent / "fixtures" / "mtgo.com"

LISTING = FIX / "listing-decklists-2026-07-07.html"
CHALLENGE = FIX / "modern-challenge-32-2026-07-0412846483.html"
LEAGUE = FIX / "modern-league-2026-07-0610847.html"
NO_DECKLISTS = FIX / "modern-challenge-64-2026-07-0212846455-no-decklists.html"
MALFORMED_NO_BLOB = FIX / "malformed-no-data-blob.html"
MALFORMED_TRUNCATED = FIX / "malformed-truncated-json.html"


def _html(p: Path) -> str:
    return p.read_text(encoding="utf-8", errors="replace")


# ---------------------------------------------------------------- listing

def test_listing_slugs_include_known_events():
    slugs = parse_listing_slugs(_html(LISTING))
    assert "modern-challenge-32-2026-07-0412846483" in slugs
    assert "modern-league-2026-07-0610847" in slugs
    # the real 2026-07-07 listing carried 103 distinct events
    assert len(slugs) == 103
    # no duplicates, no leading slash, plausible slug grammar
    assert len(set(slugs)) == len(slugs)
    assert all("/" not in s and s == s.strip() for s in slugs)


def test_listing_slugs_deduplicated_and_ordered():
    slugs = parse_listing_slugs(_html(LISTING))
    # deterministic order (needed for reproducible fetch scheduling)
    assert slugs == sorted(set(slugs))


# ---------------------------------------------------------------- blob extraction

def test_extract_blob_challenge_has_decklists():
    data = extract_decklists_data(_html(CHALLENGE))
    assert data is not None
    assert data["type"] == "TOURNAMENT"
    assert data["site_name"] == "modern-challenge-32-2026-07-0412846483"
    assert len(data["decklists"]) == 32


def test_extract_blob_absent_returns_none():
    assert extract_decklists_data(_html(MALFORMED_NO_BLOB)) is None


def test_extract_blob_invalid_json_raises():
    with pytest.raises(MtgoParseError):
        extract_decklists_data(_html(MALFORMED_TRUNCATED))


# ---------------------------------------------------------------- challenge mapping

def test_challenge_to_cacheitem_structure():
    item = event_to_cacheitem(extract_decklists_data(_html(CHALLENGE)))
    assert item["Tournament"]["Name"] == "Modern Challenge 32"
    assert item["Tournament"]["Date"].startswith("2026-07-04")
    assert item["Tournament"]["Uri"].endswith("modern-challenge-32-2026-07-0412846483")
    assert len(item["Decks"]) == 32

    # the rank-1 player (FakeShaver) is decklists[0] in the fixture
    by_player = {d["Player"]: d for d in item["Decks"]}
    fake = by_player["FakeShaver"]
    main = {c["CardName"]: c["Count"] for c in fake["Mainboard"]}
    assert main["Disrupting Shoal"] == 4
    assert main["Spell Snare"] == 2
    side = {c["CardName"]: c["Count"] for c in fake["Sideboard"]}
    assert side["Engineered Explosives"] == 2
    # challenge decks carry a rank-derived Result the normalizer understands
    assert fake["Result"] == "1st Place"


def test_challenge_standings_and_rounds():
    item = event_to_cacheitem(extract_decklists_data(_html(CHALLENGE)))
    assert len(item["Standings"]) == 32
    top = item["Standings"][0]
    assert top["Rank"] == 1 and top["Player"] == "FakeShaver"

    # brackets -> Rounds: Top-8 tree, Player1's-perspective W-L-D results
    names = [r["RoundName"] for r in item["Rounds"]]
    assert names == ["Quarterfinals", "Semifinals", "Finals"]
    counts = [len(r["Matches"]) for r in item["Rounds"]]
    assert counts == [4, 2, 1]
    qf0 = item["Rounds"][0]["Matches"][0]
    # gazmon48 (2-0) beat TrueHero in the fixture's first QF match
    assert qf0["Player1"] == "gazmon48" and qf0["Player2"] == "TrueHero"
    assert qf0["Result"] == "2-0-0"


# ---------------------------------------------------------------- league mapping

def test_league_to_cacheitem_structure():
    item = event_to_cacheitem(extract_decklists_data(_html(LEAGUE)))
    assert item["Tournament"]["Name"] == "Modern League"
    assert item["Tournament"]["Date"].startswith("2026-07-06")
    assert len(item["Decks"]) == 58
    # leagues are winner-censored 5-0 lists: Result records, no standings/rounds
    assert item["Rounds"] is None
    assert item["Standings"] is None

    val = next(d for d in item["Decks"] if d["Player"] == "Valident")
    assert val["Result"] == "5-0"
    main = {c["CardName"]: c["Count"] for c in val["Mainboard"]}
    assert main["Lórien Revealed"] == 3


# ---------------------------------------------------------------- edge: no decklists

def test_no_decklists_event_yields_zero_decks():
    data = extract_decklists_data(_html(NO_DECKLISTS))
    assert data is not None
    assert "decklists" not in data or not data["decklists"]
    item = event_to_cacheitem(data)
    # standings/brackets exist but no published decklists -> 0 decks, not an error
    assert item["Decks"] == []
    assert item["Tournament"]["Name"] == "Modern Challenge 64"
