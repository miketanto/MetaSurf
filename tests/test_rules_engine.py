"""Rules-engine tests.

Pure tests exercise the documented reference semantics on constructed decks
(integer card ids). The DB tests load the full ported Modern definitions
against the real cards table (seeded from the committed Scryfall snapshot)
and classify two real Affinity decks saved in the 2016 daily-swiss fixture —
expected results are hand-traced against the ported rule files in comments.
"""

from __future__ import annotations

import gzip

import orjson
import pytest

from archetypes.classifier.definitions import (
    ArchetypeDef,
    Condition,
    FallbackDef,
    FormatDefinitions,
    LoadReport,
    build_fold_index,
    load_format,
)
from archetypes.classifier.engine import ENGINE_SEMANTICS, Deck, classify, deck_color
from ingest.normalize.resolver import CardResolver
from ingest.scryfall import load_cards, parse_cards
from tests.conftest import REPO

pytestmark = []


def _defs(archetypes=(), fallbacks=(), lands=None, nonlands=None) -> FormatDefinitions:
    return FormatDefinitions(
        format_name="modern",
        archetypes=tuple(archetypes),
        fallbacks=tuple(fallbacks),
        land_colors=lands or {},
        nonland_colors=nonlands or {},
        classifier_version="test",
    )


def _arch(name, conditions, variants=(), color=False) -> ArchetypeDef:
    return ArchetypeDef(
        name=name,
        include_color_in_name=color,
        conditions=tuple(conditions),
        variants=tuple(variants),
    )


def c(ctype, *ids, raw=None) -> Condition:
    return Condition(type=ctype, card_ids=tuple(ids), raw_count=raw or len(ids))


class TestConditionSemantics:
    DECK = Deck(main={1: 4, 2: 1}, side={3: 2})

    @pytest.mark.parametrize(
        ("cond", "expected"),
        [
            (c("InMainboard", 1), True),
            (c("InMainboard", 3), False),  # sideboard only
            (c("InSideboard", 3), True),
            (c("InSideboard", 1), False),
            (c("InMainOrSideboard", 3), True),
            (c("OneOrMoreInMainboard", 5, 6, 1), True),
            (c("OneOrMoreInMainboard", 5, 6), False),
            (c("TwoOrMoreInMainboard", 1, 2), True),
            (c("TwoOrMoreInMainboard", 1, 5), False),  # one distinct name, 4 copies
            (c("TwoOrMoreInMainOrSideboard", 1, 3), True),
            (c("DoesNotContain", 5), True),
            (c("DoesNotContain", 3), False),  # checks side too
            (c("DoesNotContainMainboard", 3), True),
            (c("DoesNotContainSideboard", 1), True),
            # positive condition whose names all failed to resolve can never hold
            (c("InMainboard", raw=1), False),
            (c("OneOrMoreInMainboard", raw=3), False),
            # negative condition with unresolved name trivially holds
            (c("DoesNotContain", raw=1), True),
            # empty-Cards condition is skipped (treated as satisfied)
            (c("InMainboard", raw=0), True),
        ],
    )
    def test_condition(self, cond, expected):
        defs = _defs(archetypes=[_arch("X", [cond])])
        got = classify(self.DECK, defs).match is not None
        assert got is expected


def test_variant_replaces_parent_and_conflicts_prefer_simpler():
    parent = _arch(
        "Parent",
        [c("InMainboard", 1)],
        variants=[_arch("Kid", [c("InMainboard", 2)])],
    )
    other = _arch("Other", [c("InMainboard", 1), c("DoesNotContain", 9)])
    defs = _defs(archetypes=[parent, other])

    got = classify(Deck(main={1: 4, 2: 2}, side={}), defs)
    assert got.match is not None
    assert (got.match.archetype, got.match.variant) == ("Parent", "Kid")
    # conflict: Parent(1 cond)+Kid(1 cond)=2 vs Other 2 conds -> tie broken by
    # sort stability (file order); conflict set is reported either way
    assert set(got.conflict) == {"Kid", "Other"}

    got2 = classify(Deck(main={1: 4}, side={}), defs)
    assert got2.match is not None and got2.match.archetype == "Parent"
    assert got2.match.variant is None
    # Parent (1 condition) preferred over Other (2 conditions)
    assert got2.conflict == ("Parent", "Other")


def test_fallback_similarity_threshold_and_tiebreak():
    fb_big = FallbackDef("GenericControl", False, common_card_ids=(1, 2, 3))
    fb_small = FallbackDef("Control", False, common_card_ids=(1, 2))
    defs = _defs(fallbacks=[fb_big, fb_small])

    # weight 5 over 10 distinct entries = 0.5 similarity; tie -> fewer commons
    deck = Deck(main={1: 4, 2: 1, **{i: 1 for i in range(100, 108)}}, side={})
    got = classify(deck, defs)
    assert got.match is not None
    assert got.match.archetype == "Control"
    assert got.match.method == "fallback"
    assert got.match.similarity == pytest.approx(5 / 10)

    # below the 0.1 threshold -> unclassified
    thin = Deck(main={1: 1, **{i: 1 for i in range(100, 115)}}, side={})
    assert classify(thin, _defs(fallbacks=[fb_big])).match is None


def test_color_and_display_name():
    # color needs the same color in BOTH a land and a non-land
    defs = _defs(
        archetypes=[_arch("GenericControl", [c("InMainboard", 10)], color=True)],
        lands={1: "U", 2: "R"},
        nonlands={10: "U"},
    )
    deck = Deck(main={1: 4, 10: 4}, side={2: 1})  # R land but no R non-land
    assert deck_color(deck, defs) == "U"
    got = classify(deck, defs)
    assert got.match is not None
    # 'Generic' stripped, MonoBlue prefixed, PascalCase split
    assert got.match.label == "Mono Blue Control"

    # no colors at all -> 'C', which prefixes nothing
    got_c = classify(Deck(main={10: 4}, side={}), defs)
    assert got_c.color == "C" and got_c.match is not None
    assert got_c.match.label == "Control"


# --- DB-backed: full ported definitions against the real cards table --------

FIXTURE_2016 = (
    REPO
    / "tests/fixtures/MTGODecklistCache/Tournaments/mtgo.com/2016/03/23"
    / "modern-daily-swiss-2016-03-239485836.json"
)
SNAPSHOT = REPO / "data/scryfall/oracle-cards.jsonl.gz"


@pytest.fixture()
def cards_conn(db_conn, tmp_path):
    with db_conn.cursor() as cur:
        cur.execute(
            "TRUNCATE ingest_unresolved_cards, archetype_labels, matches, deck_cards,"
            " decks, events, cards RESTART IDENTITY CASCADE"
        )
    db_conn.commit()
    decompressed = tmp_path / "oracle-cards.jsonl"
    decompressed.write_bytes(gzip.decompress(SNAPSHOT.read_bytes()))
    load_cards(db_conn, parse_cards(decompressed))
    return db_conn


@pytest.mark.db
def test_full_modern_definitions_load_cleanly(cards_conn):
    resolver = CardResolver.from_db(cards_conn, "mtg")
    with cards_conn.cursor() as cur:
        cur.execute(
            "SELECT c.name, c.id FROM cards c JOIN games g ON g.id = c.game_id"
            " WHERE g.name = 'mtg' ORDER BY c.id"
        )
        fold_index = build_fold_index(cur.fetchall())
    report = LoadReport()
    defs = load_format(
        "modern", resolver.resolve, fold_index, ENGINE_SEMANTICS, report=report
    )
    assert len(defs.archetypes) == 130
    assert len(defs.fallbacks) == 9
    # the two known upstream typos fold-resolve; nothing stays unresolved
    assert sorted(report.fold_resolved) == [" Bottled Cloister", "Troll of Khazad-dum"]
    assert report.unresolved == []
    assert defs.classifier_version.startswith("rules-")

    # real decks from the 2016 daily-swiss fixture, players ArcaCrema and
    # snapcaster____mage. Hand-trace vs Archetypes/Affinity.json: both decks
    # have Ornithopter+Memnite+Springleaf Drum+Mox Opal (condition 1) and
    # Arcbound Ravager (condition 2; second deck also Thoughtcast); none of
    # the 2021+ DoesNotContain cards can occur in a 2016 list.
    data = orjson.loads(FIXTURE_2016.read_bytes())
    checked = 0
    for deck in data["Decks"]:
        if deck["Player"] not in ("ArcaCrema", "snapcaster____mage"):
            continue
        main: dict[int, int] = {}
        side: dict[int, int] = {}
        for zone, target in (("Mainboard", main), ("Sideboard", side)):
            for entry in deck[zone]:
                cid = resolver.resolve(entry["CardName"])
                assert cid is not None, entry["CardName"]
                target[cid] = target.get(cid, 0) + entry["Count"]
        got = classify(Deck(main=main, side=side), defs)
        assert got.match is not None
        assert got.match.archetype == "Affinity"
        assert got.match.method == "rules"
        assert got.conflict == ()
        checked += 1
    assert checked == 2
