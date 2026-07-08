"""Daily unattended ingestion chain (M4 DoD).

Order (each REQUIRED step gates the ones after it; a REQUIRED failure alerts
and aborts the rest of the chain — you must not roll up a DB whose import
failed):

    melee_scrape   (best-effort — never blocks MTGO; plan §10 risk 2)
    mtgo_scrape    fetch new mtgo.com events -> raw archive + CacheItem files
    import         run_import(skip_existing) — DQ gates inside
    match_extract  brackets/rounds -> matches — DQ gates inside
    label          archetypes.labeler.label_corpus
    rollups        jobs.rollups builders (what the API serves)

Every run appends a status record to a JSONL log for monitoring, and any
failure raises an alert through the injected Alerter. The orchestration core
(`run_pipeline`) is pure and unit-tested with fake steps; `main()` wires the
real callables.
"""

from __future__ import annotations

import datetime as dt
import json
import os
import traceback
from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path

import psycopg

from db.connection import database_url
from ingest.mtgo_scraper.alerting import Alerter, LoggingAlerter

DEFAULT_CACHE_ROOT = Path(os.environ.get("METASURF_CACHE_ROOT", "data/MTGODecklistCache"))
DEFAULT_RAW_ROOT = Path(os.environ.get("METASURF_RAW_ROOT", "data/raw"))
DEFAULT_STATE_DIR = Path(os.environ.get("METASURF_STATE_DIR", "data/state"))


@dataclass
class Step:
    name: str
    fn: Callable[[], str]
    required: bool = True


@dataclass
class StepResult:
    name: str
    status: str  # "ok" | "failed" | "skipped" | "warned"
    detail: str = ""


@dataclass
class RunReport:
    started_at: str
    steps: list[StepResult] = field(default_factory=list)
    ok: bool = True

    def as_record(self) -> dict[str, object]:
        return {
            "started_at": self.started_at,
            "ok": self.ok,
            "steps": [{"name": s.name, "status": s.status, "detail": s.detail} for s in self.steps],
        }


def run_pipeline(
    steps: list[Step],
    alerter: Alerter,
    *,
    started_at: str,
) -> RunReport:
    report = RunReport(started_at=started_at)
    aborted = False
    for step in steps:
        if aborted:
            report.steps.append(StepResult(step.name, "skipped", "prior required step failed"))
            continue
        try:
            detail = step.fn()
            report.steps.append(StepResult(step.name, "ok", detail))
        except Exception as exc:  # step boundary: capture any failure and route to alert
            tb = traceback.format_exc()
            if step.required:
                report.ok = False
                aborted = True
                report.steps.append(StepResult(step.name, "failed", str(exc)))
                alerter.alert(
                    f"[MetaSurf M4] daily ingestion FAILED at step '{step.name}'",
                    tb,
                    level="error",
                )
            else:
                report.steps.append(StepResult(step.name, "warned", str(exc)))
                alerter.alert(
                    f"[MetaSurf M4] best-effort step '{step.name}' failed (MTGO unaffected)",
                    tb,
                    level="warning",
                )
    return report


def write_status(state_dir: Path, report: RunReport) -> Path:
    state_dir.mkdir(parents=True, exist_ok=True)
    path = state_dir / "daily_status.jsonl"
    with path.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(report.as_record()) + "\n")
    return path


def build_steps(
    conn: psycopg.Connection,
    cache_root: Path,
    raw_root: Path,
    *,
    game: str = "mtg",
    format_name: str = "modern",
) -> list[Step]:
    # imported lazily so unit tests of run_pipeline need no DB/model deps
    from archetypes.labeler import label_corpus
    from ingest import melee_scraper
    from ingest.cache_import.importer import run_import
    from ingest.match_extract.extractor import extract_matches
    from ingest.mtgo_scraper.fetch import Fetcher, RawArchive
    from ingest.mtgo_scraper.scrape import run_scrape
    from jobs.rollups.__main__ import JOBS, latest_event_date
    from jobs.rollups.common import resolve_format_id

    def _melee() -> str:
        if not melee_scraper.enabled():
            return "disabled (METASURF_MELEE_ENABLED unset)"
        return melee_scraper.run_scrape(cache_root)

    def _mtgo_scrape() -> str:
        fetcher = Fetcher(RawArchive(raw_root))
        return run_scrape(fetcher, cache_root, game=game).summary()

    def _import() -> str:
        return run_import(conn, cache_root, game=game, skip_existing=True).summary()

    def _match_extract() -> str:
        return extract_matches(conn, cache_root).summary()

    def _label() -> str:
        return label_corpus(conn, format_name).summary()

    def _rollups() -> str:
        format_id = resolve_format_id(conn, game, format_name)
        as_of = latest_event_date(conn, format_id)
        if as_of is None:
            raise RuntimeError("no stored events for this format; nothing to roll up")
        lines = [f"as_of={as_of}"]
        for name in sorted(JOBS):
            JOBS[name](conn, game, format_name, as_of)
            lines.append(f"  {name}: ok")
        return "\n".join(lines)

    return [
        Step("melee_scrape", _melee, required=False),
        Step("mtgo_scrape", _mtgo_scrape),
        Step("import", _import),
        Step("match_extract", _match_extract),
        Step("label", _label),
        Step("rollups", _rollups),
    ]


def main() -> int:
    import argparse

    parser = argparse.ArgumentParser(description="M4 daily unattended ingestion chain")
    parser.add_argument("--game", default="mtg")
    parser.add_argument("--format", dest="format_name", default="modern")
    parser.add_argument("--cache-root", type=Path, default=DEFAULT_CACHE_ROOT)
    parser.add_argument("--raw-root", type=Path, default=DEFAULT_RAW_ROOT)
    parser.add_argument("--state-dir", type=Path, default=DEFAULT_STATE_DIR)
    args = parser.parse_args()

    started_at = dt.datetime.now(dt.UTC).strftime("%Y-%m-%dT%H:%M:%SZ")
    alerter = LoggingAlerter(args.state_dir / "alerts.jsonl")
    try:
        with psycopg.connect(database_url()) as conn:
            steps = build_steps(
                conn, args.cache_root, args.raw_root, game=args.game, format_name=args.format_name
            )
            report = run_pipeline(steps, alerter, started_at=started_at)
    except Exception:
        # top-level failure outside any step (e.g. DB unreachable at connect):
        # still alert + record a failed run so the soak never silently stalls
        tb = traceback.format_exc()
        alerter.alert("[MetaSurf M4] daily ingestion crashed before/around the chain", tb)
        report = RunReport(started_at=started_at, ok=False)
        report.steps.append(StepResult("startup", "failed", tb.strip().splitlines()[-1]))
    write_status(args.state_dir, report)
    for s in report.steps:
        print(f"[{s.status}] {s.name}: {s.detail.splitlines()[0] if s.detail else ''}")
    return 0 if report.ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
