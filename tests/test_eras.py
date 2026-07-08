"""Rotation-era resolution derived from dated definition folders (transferable
to any rotating format; no config)."""

from __future__ import annotations

import datetime as dt

from archetypes.classifier.eras import format_eras, rules_dir_for_date


def test_standard_eras_ordered_with_open_current():
    eras = format_eras("standard")
    # two dated historical eras + the open current era
    assert [e.rules_dir for e in eras] == [
        "standard-20230701-20240802",
        "standard-20240803-20250730",
        "standard",
    ]
    assert eras[0].start == dt.date(2023, 7, 1) and eras[0].end == dt.date(2024, 8, 2)
    assert eras[1].start == dt.date(2024, 8, 3) and eras[1].end == dt.date(2025, 7, 30)
    # current era is open on the right, starting the day after the last dated end
    assert eras[2].start == dt.date(2025, 7, 31) and eras[2].end is None


def test_rules_dir_for_date_picks_the_era():
    assert rules_dir_for_date("standard", dt.date(2024, 3, 15)) == "standard-20230701-20240802"
    assert rules_dir_for_date("standard", dt.date(2024, 11, 1)) == "standard-20240803-20250730"
    assert rules_dir_for_date("standard", dt.date(2026, 7, 8)) == "standard"


def test_nonrotating_format_has_single_open_era():
    # Modern has no dated folders -> one open era = the format itself
    eras = format_eras("modern")
    assert len(eras) == 1
    assert eras[0].rules_dir == "modern" and eras[0].start is None and eras[0].end is None
