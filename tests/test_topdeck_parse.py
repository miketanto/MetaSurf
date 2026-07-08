"""TopDeck parser tests against REAL captured API responses (fixtures under
tests/fixtures/topdeck.gg/, captured 2026-07-08 from the live v2 API)."""

from __future__ import annotations

import json
import re
from pathlib import Path

import pytest

from ingest.topdeck_scraper.parse import (
    TopdeckParseError,
    build_cacheitem,
    parse_decklist,
    to_iso_date,
)

FIX = Path(__file__).resolve().parent / "fixtures" / "topdeck.gg"
WITH_DECKS = FIX / "real-modern-with-decklists.json"
NO_DECKS = FIX / "real-no-decklists-edge.json"


def _t(path: Path) -> dict:
    return json.loads(path.read_text())


def _item(path: Path) -> dict:
    t = _t(path)
    return build_cacheitem(t, t["standings"], t["rounds"])


def test_parse_decklist_handles_double_escaped_text():
    # real API quirk: literal "\n" separators + escaped apostrophes
    text = (
        "~~Mainboard~~\\n1 Cavern of Souls\\n1 Elspeth, Sun\\'s Champion"
        "\\n~~Sideboard~~\\n2 Duress"
    )
    main, side = parse_decklist(text)
    assert {c["CardName"]: c["Count"] for c in main} == {
        "Cavern of Souls": 1,
        "Elspeth, Sun's Champion": 1,  # apostrophe un-escaped
    }
    assert side == [{"CardName": "Duress", "Count": 2}]


def test_parse_decklist_empty():
    assert parse_decklist("") == ([], [])
    assert parse_decklist(None) == ([], [])


def test_to_iso_date_from_unix_and_iso():
    assert to_iso_date(1783250100) == "2026-07-05T11:15:00Z"
    assert to_iso_date("1783250100") == "2026-07-05T11:15:00Z"
    assert to_iso_date("2026-07-05T11:15:00Z") == "2026-07-05T11:15:00Z"
    assert to_iso_date(None) is None


def test_real_tournament_maps_to_cacheitem():
    item = _item(WITH_DECKS)
    assert item["Tournament"]["Name"] == "Impact Returns 26 Sunday Modern 2015"
    assert re.match(r"2026-07-\d\dT", item["Tournament"]["Date"])
    assert item["Tournament"]["Uri"].endswith("/event/impact-returns-26-sunday-modern-2015")
    assert len(item["Decks"]) == 15
    with_main = [d for d in item["Decks"] if d["Mainboard"]]
    assert len(with_main) == 14  # 14 of 15 players submitted lists
    # a real submitted list is a legal-size Modern deck; apostrophe card resolved
    d = with_main[0]
    assert sum(c["Count"] for c in d["Mainboard"]) >= 60
    names = {c["CardName"] for dd in with_main for c in dd["Mainboard"]}
    assert "Elspeth, Sun's Champion" in names
    # record-shaped Result the normalizer already parses
    assert re.match(r"^\d+-\d+(-\d+)?$", d["Result"])


def test_real_standings_ranked_with_records():
    item = _item(WITH_DECKS)
    st = item["Standings"]
    assert [s["Rank"] for s in st] == list(range(1, 16))
    assert st[0]["Player"] and "Wins" in st[0] and "Losses" in st[0]


def test_real_rounds_player1_perspective():
    item = _item(WITH_DECKS)
    m = item["Rounds"][0]["Matches"][0]
    # W-L-D from Player1's perspective (verified: Gerardo beat Mario 2-1)
    assert re.match(r"^\d+-\d+-\d+$", m["Result"])
    assert m["Player1"] and m["Player2"]


def test_no_decklists_edge_does_not_crash():
    item = _item(NO_DECKS)
    assert len(item["Decks"]) >= 1
    # players submitted no lists -> empty boards, record-based Result, no error
    assert all(d["Mainboard"] == [] for d in item["Decks"])
    assert all(re.match(r"^\d+-\d+", d["Result"]) for d in item["Decks"])


def test_build_cacheitem_requires_tid():
    with pytest.raises(TopdeckParseError):
        build_cacheitem({"tournamentName": "no id"}, [], [])
