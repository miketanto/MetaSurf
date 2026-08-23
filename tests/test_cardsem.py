"""Tests for the CardGuru card-semantics bridge (ingest/cardsem).

All parser tests run against real bytes taken from CardGuru's
rl/e2_features.tsv (tests/fixtures/cardguru/e2_features_sample.tsv), plus one
hand-written malformed fixture. No synthetic "probably looks like this" data.
"""

from __future__ import annotations

import gzip
from pathlib import Path

import pytest

from ingest.cardsem import (
    CardIdentity,
    FeatureTableError,
    fold_name,
    join_to_cards,
    load_feature_table,
    parse_feature_table,
)
from ingest.cardsem.coverage import BLIND_SPOT_PROBE, VANILLA_PROBE
from ingest.cardsem.dims import DIM, FEATURE_NAMES, UNREPRESENTED_MECHANICS

FIXTURES = Path(__file__).parent / "fixtures" / "cardguru"
SAMPLE = FIXTURES / "e2_features_sample.tsv"
MALFORMED = FIXTURES / "e2_features_malformed.tsv"
SHIPPED = Path(__file__).resolve().parents[1] / "ingest" / "cardsem" / "features.tsv.gz"


def _sample_table():
    return parse_feature_table(SAMPLE.read_text(encoding="utf-8").splitlines())


# ------------------------------------------------------------------- parsing


def test_parses_real_sample_rows():
    table = _sample_table()
    assert table.dim == 68
    assert len(table.vectors) == 8
    assert len(table.vectors["Lightning Bolt"]) == 68


def test_every_vector_has_declared_dim():
    table = _sample_table()
    assert all(len(v) == table.dim for v in table.vectors.values())


def test_observed_zero_vector_row_is_kept_and_flagged():
    """763 of 35,390 real rows are all-zero: the extractor found no scripted
    mechanics. That is NOT the same as 'no data' and must stay distinguishable."""
    table = _sample_table()
    assert "Aboroth" in table.vectors
    assert not any(table.vectors["Aboroth"])
    assert "Aboroth" in table.zero_vector_names
    assert "Lightning Bolt" not in table.zero_vector_names


def test_non_ascii_name_round_trips():
    assert "Andúril, Flame of the West" in _sample_table().vectors


def test_multi_face_joined_name_is_a_single_row():
    table = _sample_table()
    joined = "A-Alrund, God of the Cosmos // A-Hakka, Whispering Raven"
    assert joined in table.vectors
    assert table.vectors[joined][-1] == 1.0  # multi_face is the last dim


@pytest.mark.parametrize(
    "bad_line", ["Short Vector", "Not A Number", "No Tab Separator Here"]
)
def test_malformed_rows_fail_loudly(bad_line):
    """Never silently drop a row: a malformed table is a broken pin, not a
    partial dataset (CLAUDE.md: fail loudly instead of ingesting garbage)."""
    lines = MALFORMED.read_text(encoding="utf-8").splitlines()
    keep = [lines[0]] + [line for line in lines[1:] if line.startswith(bad_line)]
    with pytest.raises(FeatureTableError) as exc:
        parse_feature_table(keep)
    assert bad_line in str(exc.value)


def test_missing_dim_header_fails_loudly():
    with pytest.raises(FeatureTableError):
        parse_feature_table(["Lightning Bolt\t0,1"])


def test_duplicate_name_fails_loudly():
    lines = SAMPLE.read_text(encoding="utf-8").splitlines()
    with pytest.raises(FeatureTableError):
        parse_feature_table([*lines, lines[1]])


# -------------------------------------------------------------- shipped table


def test_shipped_table_matches_pinned_provenance():
    """The committed table is the exact artifact named in PROVENANCE.md."""
    with gzip.open(SHIPPED, "rt", encoding="utf-8") as fh:
        table = parse_feature_table(fh.read().splitlines())
    assert table.dim == 68
    assert len(table.vectors) == 35390
    assert len(table.zero_vector_names) == 763


def test_load_feature_table_handles_gzip():
    assert load_feature_table(SHIPPED).dim == 68


# ------------------------------------------------------------------- folding


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("Andúril, Flame of the West", "anduril, flame of the west"),
        ("Lightning Bolt", "lightning bolt"),
        ("  Fatal Push  ", "fatal push"),
        ("LIGHTNING BOLT", "lightning bolt"),
    ],
)
def test_fold_name(raw, expected):
    assert fold_name(raw) == expected


# ---------------------------------------------------------------------- join


def test_join_exact_match():
    table = _sample_table()
    res = join_to_cards(table, [CardIdentity(1, "Lightning Bolt", ())])
    assert res.by_card_key[1] == table.vectors["Lightning Bolt"]
    assert res.matched_exact == 1
    assert not res.unmatched_cards


def test_join_casefold_match_is_counted_separately():
    res = join_to_cards(_sample_table(), [CardIdentity(1, "lightning bolt", ())])
    assert 1 in res.by_card_key
    assert res.matched_exact == 0
    assert res.matched_folded == 1


def test_join_accent_folded_match():
    res = join_to_cards(
        _sample_table(), [CardIdentity(1, "Anduril, Flame of the West", ())]
    )
    assert 1 in res.by_card_key
    assert res.matched_folded == 1


def test_join_falls_back_to_face_names():
    """Scryfall stores split/DFC cards under a combined name plus face_names;
    the feature table registers both. A card whose combined name is absent
    must still resolve through a face name."""
    table = _sample_table()
    res = join_to_cards(
        table,
        [CardIdentity(1, "Nonexistent // Combined", ("Lightning Bolt", "Fatal Push"))],
    )
    assert res.by_card_key[1] == table.vectors["Lightning Bolt"]
    assert res.matched_via_face == 1


def test_join_reports_unmatched_and_never_guesses():
    res = join_to_cards(_sample_table(), [CardIdentity(7, "Definitely Not A Real Card", ())])
    assert res.by_card_key == {}
    assert res.unmatched_cards == ((7, "Definitely Not A Real Card"),)


def test_join_flags_zero_vector_cards_for_masking():
    """A zero vector means 'no scripted mechanics found', which is not the
    same as 'this card does nothing'. Callers must be able to mask these."""
    res = join_to_cards(_sample_table(), [CardIdentity(1, "Aboroth", ())])
    assert res.zero_vector_keys == (1,)


def test_join_is_deterministic_and_order_independent():
    table = _sample_table()
    cards = [
        CardIdentity(2, "Fatal Push", ()),
        CardIdentity(1, "Lightning Bolt", ()),
        CardIdentity(3, "Counterspell", ()),
    ]
    a = join_to_cards(table, cards)
    b = join_to_cards(table, list(reversed(cards)))
    assert a.by_card_key == b.by_card_key
    assert a.unmatched_cards == b.unmatched_cards


def test_first_match_tier_wins():
    """Exact beats folded: a card whose exact name is present must not be
    reassigned by the folding pass."""
    table = _sample_table()
    res = join_to_cards(table, [CardIdentity(1, "Counterspell", ("Lightning Bolt",))])
    assert res.by_card_key[1] == table.vectors["Counterspell"]
    assert res.matched_exact == 1
    assert res.matched_via_face == 0


# ------------------------------------------------------------------ dimensions


def test_dim_names_match_shipped_table():
    """A pin bump that changes the feature space must fail here rather than
    silently shift the meaning of every column."""
    assert DIM == 68
    assert len(set(FEATURE_NAMES)) == 68
    assert load_feature_table(SHIPPED).dim == DIM


def test_unrepresented_mechanics_really_are_unrepresented():
    """The blind-spot list is a claim about the feature space; assert it."""
    for mechanic in UNREPRESENTED_MECHANICS:
        assert not any(mechanic in name for name in FEATURE_NAMES), mechanic


def test_blind_spot_probe_cards_are_all_zero():
    """Documented evidence that an all-zero vector is not proof of a vanilla
    card: these three have real abilities and still extract to zero."""
    table = load_feature_table(SHIPPED)
    for name, _ in BLIND_SPOT_PROBE:
        assert name in table.vectors, name
        assert not any(table.vectors[name]), name


def test_vanilla_probe_cards_are_all_zero_and_that_is_correct():
    """The contrast case: these really are vanilla, so zero is the right answer.
    Together with the blind-spot probe this proves the two are indistinguishable
    from the vector alone — which is why masking is required."""
    table = load_feature_table(SHIPPED)
    for name in VANILLA_PROBE:
        assert name in table.vectors, name
        assert not any(table.vectors[name]), name
