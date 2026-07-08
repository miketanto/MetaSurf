"""Soak monitor: turn the daily status log into a DoD verdict.

M4 DoD (plan §7): 14 consecutive days of unattended daily ingestion with
failure alerting. This reads the JSONL written by `daily.run_pipeline` and
reports the current streak of consecutive calendar days that each had at
least one fully-successful run, plus the most recent failures — the single
number that says whether the milestone is met.
"""

from __future__ import annotations

import datetime as dt
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

DOD_DAYS = 14


@dataclass
class SoakReport:
    total_runs: int
    successful_days: list[str]  # sorted YYYY-MM-DD with >=1 ok run
    failed_days: list[str]  # dates whose latest run failed
    current_streak: int  # consecutive ok days ending at the latest ok day
    streak_start: str | None
    streak_end: str | None
    dod_met: bool
    last_failures: list[dict[str, Any]]

    def summary(self) -> str:
        lines = [
            f"runs recorded:        {self.total_runs}",
            f"successful days:      {len(self.successful_days)}",
            f"current streak:       {self.current_streak}/{DOD_DAYS} days"
            + (f" ({self.streak_start} -> {self.streak_end})" if self.streak_start else ""),
            f"DoD (14 consecutive): {'MET' if self.dod_met else 'not yet'}",
        ]
        if self.failed_days:
            lines.append(f"days with a failing latest run: {', '.join(self.failed_days)}")
        for f in self.last_failures:
            failed = [s["name"] for s in f["steps"] if s["status"] == "failed"]
            lines.append(f"  FAIL {f['started_at']}: {', '.join(failed) or 'unknown step'}")
        return "\n".join(lines)


def _day(started_at: str) -> str:
    return started_at[:10]


def summarize(records: list[dict[str, Any]], dod_days: int = DOD_DAYS) -> SoakReport:
    """Reduce raw status records to a soak verdict. A calendar day counts as
    successful iff its LAST run that day succeeded (a failed run followed by a
    fixed re-run is a good day; a passing run followed by a broken one is not).
    """
    by_day_last: dict[str, dict[str, Any]] = {}
    for rec in sorted(records, key=lambda r: r["started_at"]):
        by_day_last[_day(rec["started_at"])] = rec

    ok_days = sorted(d for d, r in by_day_last.items() if r.get("ok"))
    failed_days = sorted(d for d, r in by_day_last.items() if not r.get("ok"))

    # current streak = consecutive ok days ending at the most recent calendar
    # day that has a run. If that latest day's run failed, the streak is 0
    # (we are not currently green), even if earlier days were fine.
    streak = 0
    streak_start = streak_end = None
    ok_set = set(ok_days)
    if by_day_last:
        latest_day = max(by_day_last)
        if latest_day in ok_set:
            streak_end = latest_day
            cur = dt.date.fromisoformat(latest_day)
            while cur.isoformat() in ok_set:
                streak += 1
                streak_start = cur.isoformat()
                cur -= dt.timedelta(days=1)

    last_failures = [r for r in sorted(records, key=lambda r: r["started_at"]) if not r.get("ok")][
        -5:
    ]
    return SoakReport(
        total_runs=len(records),
        successful_days=ok_days,
        failed_days=failed_days,
        current_streak=streak,
        streak_start=streak_start,
        streak_end=streak_end,
        dod_met=streak >= dod_days,
        last_failures=last_failures,
    )


def load_status(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    out: list[dict[str, Any]] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line:
            out.append(json.loads(line))
    return out


def main() -> int:
    import argparse

    from ingest.mtgo_scraper.daily import DEFAULT_STATE_DIR

    parser = argparse.ArgumentParser(description="M4 soak status / DoD verdict")
    parser.add_argument("--state-dir", type=Path, default=DEFAULT_STATE_DIR)
    args = parser.parse_args()
    report = summarize(load_status(args.state_dir / "daily_status.jsonl"))
    print(report.summary())
    return 0 if report.dod_met else 1


if __name__ == "__main__":
    raise SystemExit(main())
