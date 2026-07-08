"""The V1 archetype harness is format-parameterized; defaults reproduce the
Modern gate exactly, and a format with no emergence events runs V1.1 only."""

from __future__ import annotations

import inspect

from validation.v1_archetypes.run import run_v11, run_v12


def test_run_v11_v12_default_to_modern():
    assert inspect.signature(run_v11).parameters["format_name"].default == "modern"
    assert inspect.signature(run_v12).parameters["format_name"].default == "modern"


def test_run_v12_no_events_is_a_db_free_noop():
    # a format with no curated emergence events returns [] before touching the
    # connection (so parameterizing a new format never crashes V1.2)
    assert run_v12(conn=None, format_name="standard", emergence_events=()) == []
