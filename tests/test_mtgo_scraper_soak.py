"""Soak-monitor tests: the DoD verdict logic on synthetic status records
(pure reduction; property of the reducer, not of any real run)."""

from __future__ import annotations

from ingest.mtgo_scraper.soak import summarize


def _rec(day: str, ok: bool, failed_step: str | None = None):
    steps = [
        {"name": "mtgo_scrape", "status": "ok", "detail": ""},
        {
            "name": "import",
            "status": "failed" if failed_step == "import" else "ok",
            "detail": "",
        },
    ]
    return {"started_at": f"{day}T02:00:00Z", "ok": ok, "steps": steps}


def test_consecutive_days_counts_as_streak():
    days = [f"2026-07-{d:02d}" for d in range(1, 15)]  # 14 consecutive
    report = summarize([_rec(d, ok=True) for d in days])
    assert report.current_streak == 14
    assert report.dod_met is True
    assert report.streak_start == "2026-07-01" and report.streak_end == "2026-07-14"


def test_gap_breaks_the_streak():
    # 2026-07-03 missing entirely -> streak only counts from 04..07
    days = ["2026-07-01", "2026-07-02", "2026-07-04", "2026-07-05", "2026-07-06", "2026-07-07"]
    report = summarize([_rec(d, ok=True) for d in days])
    assert report.current_streak == 4  # 04,05,06,07
    assert report.dod_met is False


def test_failed_latest_run_makes_the_day_bad():
    records = [
        _rec("2026-07-01", ok=True),
        _rec("2026-07-02", ok=True),
        _rec("2026-07-03", ok=False, failed_step="import"),
    ]
    report = summarize(records)
    assert "2026-07-03" in report.failed_days
    assert report.current_streak == 0  # latest day failed -> no current streak
    assert report.last_failures and report.last_failures[-1]["started_at"].startswith("2026-07-03")


def test_fixed_rerun_same_day_rescues_the_day():
    # a failing run followed by a successful re-run the same day = good day
    records = [
        _rec("2026-07-01", ok=True),
        _rec("2026-07-02", ok=False, failed_step="import"),
        _rec("2026-07-02", ok=True),
    ]
    report = summarize(records)
    assert report.current_streak == 2
    assert "2026-07-02" not in report.failed_days


def test_empty_log_is_zero_streak():
    report = summarize([])
    assert report.current_streak == 0 and report.dod_met is False and report.total_runs == 0
