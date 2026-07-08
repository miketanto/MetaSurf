"""The V1 archetype harness is format-parameterized; defaults reproduce the
Modern gate exactly, and a format with no emergence events runs V1.1 only."""

from __future__ import annotations

import inspect

from validation.v1_archetypes.run import (
    STANDARD_EMERGENCE_EVENTS,
    run_v11,
    run_v12,
)


def test_standard_emergence_events_curated():
    # each event is (label, rule-file stem, key card, window-start date) grounded
    # in the corpus (Duskmourn arrivals); used by V1.2 for Standard
    assert STANDARD_EMERGENCE_EVENTS
    for label, stem, key_card, start in STANDARD_EMERGENCE_EVENTS:
        assert label and stem and key_card
        assert start.year == 2024


def test_run_v11_v12_default_to_modern():
    assert inspect.signature(run_v11).parameters["format_name"].default == "modern"
    assert inspect.signature(run_v12).parameters["format_name"].default == "modern"


def test_run_v12_no_events_is_a_db_free_noop():
    # a format with no curated emergence events returns [] before touching the
    # connection (so parameterizing a new format never crashes V1.2)
    assert run_v12(conn=None, format_name="standard", emergence_events=()) == []
