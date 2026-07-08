"""Scryfall bulk importer tests against real saved card objects
(tests/fixtures/scryfall/oracle-cards-sample.jsonl — byte-exact lines from the
2026-07-07 oracle-cards bulk file; provenance in
docs/notes/scryfall-oracle-cards-observed-schema.md).

The fixture deliberately contains the observed edge cases:
- a token/normal name collision (`Adorned Pouncer`, layouts token+normal),
- a funny/real full-name duplicate (`Pick Your Poison`, cmb2 playtest vs MKM),
- a face name equal to another card's full name (`Harmonized Trio // Brainstorm`
  face `Brainstorm` vs the real card `Brainstorm`),
- split / transform / modal_dfc multifaced cards corroborated by the decklist
  corpus (`Alive // Well`, `Fable of the Mirror-Breaker // ...`,
  `Clearwater Pathway // ...`).
"""

from __future__ import annotations

import json

import pytest

from ingest.normalize.resolver import CardResolver
from ingest.scryfall import ScryfallStats, load_cards, parse_cards
from tests.conftest import REPO

SAMPLE = REPO / "tests" / "fixtures" / "scryfall" / "oracle-cards-sample.jsonl"

# oracle_ids as observed in the bulk file (inspection session 2026-07-07)
ORACLE = {
    "Alive // Well": "57ad3c3a-6ac7-4a35-bc07-00f6ea0988c5",
    "Fable of the Mirror-Breaker // Reflection of Kiki-Jiki": (
        "c0957e5e-c71b-439c-931c-9f55d2f76ace"
    ),
    "Clearwater Pathway // Murkwater Pathway": "144119bc-7fd1-45c5-9e29-f742e7c255ac",
    "Pick Your Poison (mkm)": "9af4a832-d634-47aa-91ed-79d44fe08864",
    "Pick Your Poison (cmb2 playtest)": "191634b4-42e5-499f-a1a8-1d0407626be8",
}


def test_parse_filters_nonplayable_layouts_and_extracts_faces():
    stats = ScryfallStats()
    rows = parse_cards(SAMPLE, stats)

    assert stats.objects_seen == 12
    # exactly one fixture object is non-playable: the Adorned Pouncer token
    assert dict(stats.skipped_by_layout) == {"token": 1}
    assert stats.cards_imported == len(rows) == 11

    by_ref = {r.oracle_id: r for r in rows}
    split = by_ref[ORACLE["Alive // Well"]]
    assert split.name == "Alive // Well"
    assert split.attrs["layout"] == "split"
    assert split.attrs["face_names"] == ["Alive", "Well"]
    # per-format legality is carried into attrs (used to tell whether a deck is
    # still legal in a rotating format, not just played)
    assert split.attrs["legalities"]["standard"] == "not_legal"
    assert split.attrs["legalities"]["legacy"] in {"legal", "banned", "restricted"}

    dfc = by_ref[ORACLE["Fable of the Mirror-Breaker // Reflection of Kiki-Jiki"]]
    assert dfc.attrs["layout"] == "transform"
    assert dfc.attrs["face_names"] == [
        "Fable of the Mirror-Breaker",
        "Reflection of Kiki-Jiki",
    ]

    # single-faced cards carry no face_names key
    normals = [r for r in rows if r.name == "Bloodbraid Elf"]
    assert len(normals) == 1 and "face_names" not in normals[0].attrs


def test_resolution_tier_orders_real_cards_before_variants():
    rows = parse_cards(SAMPLE)
    pyp = [r for r in rows if r.name == "Pick Your Poison"]
    assert len(pyp) == 2
    tiers = {r.oracle_id: r.resolution_tier for r in pyp}
    assert tiers[ORACLE["Pick Your Poison (mkm)"]] == 0
    assert tiers[ORACLE["Pick Your Poison (cmb2 playtest)"]] == 1
    # sorted output puts the real card strictly first
    positions = {r.oracle_id: i for i, r in enumerate(rows)}
    assert (
        positions[ORACLE["Pick Your Poison (mkm)"]]
        < positions[ORACLE["Pick Your Poison (cmb2 playtest)"]]
    )


def test_legacy_json_array_framing_parses_identically(tmp_path):
    objects = [
        json.loads(line)
        for line in SAMPLE.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    array_file = tmp_path / "oracle-cards.json"
    array_file.write_text(json.dumps(objects), encoding="utf-8")
    assert parse_cards(array_file) == parse_cards(SAMPLE)


@pytest.mark.db
def test_load_and_resolve_end_to_end(db_conn):
    with db_conn.cursor() as cur:
        cur.execute(
            "TRUNCATE ingest_unresolved_cards, archetype_labels, matches, deck_cards,"
            " decks, events, cards RESTART IDENTITY CASCADE"
        )
    db_conn.commit()
    load_cards(db_conn, parse_cards(SAMPLE))

    resolver = CardResolver.from_db(db_conn, "mtg")

    def ref(name: str) -> str | None:
        cid = resolver.resolve(name)
        if cid is None:
            return None
        with db_conn.cursor() as cur:
            cur.execute("SELECT canonical_ref FROM cards WHERE id = %s", (cid,))
            row = cur.fetchone()
            return row[0] if row else None

    # corpus convention: split cards by combined name, DFCs by front face
    assert ref("Alive // Well") == ORACLE["Alive // Well"]
    assert (
        ref("Fable of the Mirror-Breaker")
        == ORACLE["Fable of the Mirror-Breaker // Reflection of Kiki-Jiki"]
    )
    assert (
        ref("Clearwater Pathway") == ORACLE["Clearwater Pathway // Murkwater Pathway"]
    )

    # full names win over face names: the real Brainstorm, not the face of
    # 'Harmonized Trio // Brainstorm'
    brainstorm_ref = ref("Brainstorm")
    with db_conn.cursor() as cur:
        cur.execute("SELECT name FROM cards WHERE canonical_ref = %s", (brainstorm_ref,))
        row = cur.fetchone()
        assert row is not None and row[0] == "Brainstorm"

    # tier preference: the MKM card, not the playtest variant
    assert ref("Pick Your Poison") == ORACLE["Pick Your Poison (mkm)"]

    # the token was filtered: 'Adorned Pouncer' resolves to the expansion card
    with db_conn.cursor() as cur:
        cur.execute("SELECT count(*) FROM cards WHERE name = 'Adorned Pouncer'")
        row = cur.fetchone()
        assert row is not None and row[0] == 1

    # observed mtgo.com_limited_data variant: split-card names written with
    # ' && ' (18 distinct names / 4,752 occurrences in the corpus, all
    # matching ' // ' split cards in the bulk file — see the schema notes)
    assert (
        ref("Unholy Annex && Ritual Chamber")
        == "bd388ad9-a47b-4b0b-b94a-8e4343cd3de5"
    )
    assert (
        ref("Roaring Furnace && Steaming Sauna")
        == "d5f31713-d380-42ba-8052-4b8d9beb3958"
    )

    # observed live mtgo.com (2026) variant: split-card names written 'A/B'
    # (no spaces) where the canonical name is 'A // B'. Same mechanical
    # separator normalisation; resolves only if the ' // ' form exists.
    assert ref("Alive/Well") == ORACLE["Alive // Well"]

    # unknown names stay unresolved — never guessed
    assert resolver.resolve("Not A Real Card Name") is None
    assert resolver.resolve("Not A Real && Card Name") is None
    assert resolver.resolve("Not A Real/Card Name") is None


@pytest.mark.db
def test_load_refuses_nonempty_cards_table(db_conn):
    with db_conn.cursor() as cur:
        cur.execute(
            "TRUNCATE ingest_unresolved_cards, archetype_labels, matches, deck_cards,"
            " decks, events, cards RESTART IDENTITY CASCADE"
        )
    db_conn.commit()
    rows = parse_cards(SAMPLE)
    load_cards(db_conn, rows)
    with pytest.raises(RuntimeError, match="already has"):
        load_cards(db_conn, rows)
