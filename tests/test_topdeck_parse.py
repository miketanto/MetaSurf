"""TopDeck parser tests against the documented API schema (see
tests/fixtures/topdeck.gg/README.md: these are schema examples, not real
captures — the source stays disabled until validated on real responses)."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from ingest.topdeck_scraper.parse import (
    TopdeckParseError,
    build_cacheitem,
    parse_decklist,
)

FIX = Path(__file__).resolve().parent / "fixtures" / "topdeck.gg" / "modern-rcq-example.json"


def _bundle() -> dict:
    return json.loads(FIX.read_text())


def test_parse_decklist_splits_main_and_side():
    text = "~~Mainboard~~\n4 Ragavan, Nimble Pilferer\n20 Mountain\n~~Sideboard~~\n2 Duress"
    main, side = parse_decklist(text)
    assert {c["CardName"]: c["Count"] for c in main} == {
        "Ragavan, Nimble Pilferer": 4,
        "Mountain": 20,
    }
    assert side == [{"CardName": "Duress", "Count": 2}]


def test_parse_decklist_empty_is_empty():
    assert parse_decklist("") == ([], [])
    assert parse_decklist(None) == ([], [])


def test_build_cacheitem_tournament_and_decks():
    b = _bundle()
    item = build_cacheitem(b["info"], b["standings"], b["rounds"])
    assert item["Tournament"]["Name"] == "Modern RCQ Example"
    assert item["Tournament"]["Date"].startswith("2026-07-05")
    assert item["Tournament"]["Uri"].endswith("/event/TESTTID123")
    assert len(item["Decks"]) == 3
    alice = next(d for d in item["Decks"] if d["Player"] == "Alice")
    assert alice["Result"] == "1st Place"
    assert {c["CardName"]: c["Count"] for c in alice["Mainboard"]}["Ragavan, Nimble Pilferer"] == 4
    assert {c["CardName"]: c["Count"] for c in alice["Sideboard"]}["Engineered Explosives"] == 2


def test_build_cacheitem_standings_sorted():
    b = _bundle()
    item = build_cacheitem(b["info"], b["standings"], b["rounds"])
    assert [s["Rank"] for s in item["Standings"]] == [1, 2, 3]
    assert item["Standings"][0]["Player"] == "Alice"


def test_build_cacheitem_rounds_and_bye():
    b = _bundle()
    item = build_cacheitem(b["info"], b["standings"], b["rounds"])
    assert [r["RoundName"] for r in item["Rounds"]] == ["1", "2"]
    r1 = item["Rounds"][0]["Matches"]
    # Player1's-perspective game counts; Alice beat Bob 2-0
    ab = next(m for m in r1 if m["Player1"] == "Alice" and m["Player2"] == "Bob")
    assert ab["Result"] == "2-0-0"
    # Carol's table is a bye -> Player2 None (never a match row downstream)
    bye = next(m for m in r1 if m["Player1"] == "Carol")
    assert bye["Player2"] is None
    # round 2: Carol (P1) lost to Alice 1-2 -> from Carol's perspective "1-2-0"
    r2 = item["Rounds"][1]["Matches"][0]
    assert r2["Player1"] == "Carol" and r2["Result"] == "1-2-0"


def test_build_cacheitem_requires_id():
    with pytest.raises(TopdeckParseError):
        build_cacheitem({"name": "no id"}, [], [])
