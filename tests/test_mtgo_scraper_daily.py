"""Tests for the scrape orchestration, the daily-chain runner, and alerting.

The runner core (run_pipeline) is exercised with fake steps and a fake alerter
(no DB, no network): the point under test is the failure routing — required
failure aborts + alerts, best-effort failure warns + continues.
"""

from __future__ import annotations

import json
from pathlib import Path

from ingest.mtgo_scraper.alerting import LoggingAlerter
from ingest.mtgo_scraper.daily import RunReport, Step, StepResult, run_pipeline, write_status
from ingest.mtgo_scraper.parse import event_to_cacheitem, extract_decklists_data
from ingest.mtgo_scraper.pipeline import cacheitem_relpath
from ingest.mtgo_scraper.scrape import run_scrape
from tests.test_mtgo_scraper_fetch import FakeTransport, Response, _fetcher

FIX = Path(__file__).resolve().parent / "fixtures" / "mtgo.com"


class RecordingAlerter:
    def __init__(self):
        self.alerts = []

    def alert(self, subject, body, *, level="error"):
        self.alerts.append((level, subject))


# ------------------------------------------------------------- run_pipeline

def test_all_steps_ok_no_alert():
    alerter = RecordingAlerter()
    steps = [Step("a", lambda: "ok-a"), Step("b", lambda: "ok-b")]
    report = run_pipeline(steps, alerter, started_at="T")
    assert report.ok
    assert [s.status for s in report.steps] == ["ok", "ok"]
    assert alerter.alerts == []


def test_required_failure_aborts_and_alerts():
    alerter = RecordingAlerter()

    def boom():
        raise RuntimeError("import blew up")

    steps = [
        Step("scrape", lambda: "ok"),
        Step("import", boom),
        Step("rollups", lambda: "should not run"),
    ]
    report = run_pipeline(steps, alerter, started_at="T")
    assert report.ok is False
    statuses = {s.name: s.status for s in report.steps}
    assert statuses == {"scrape": "ok", "import": "failed", "rollups": "skipped"}
    assert len(alerter.alerts) == 1
    assert alerter.alerts[0][0] == "error"
    assert "import" in alerter.alerts[0][1]


def test_best_effort_failure_warns_but_continues():
    alerter = RecordingAlerter()

    def melee_down():
        raise RuntimeError("melee refused")

    steps = [
        Step("melee", melee_down, required=False),
        Step("mtgo_scrape", lambda: "ok"),
        Step("import", lambda: "ok"),
    ]
    report = run_pipeline(steps, alerter, started_at="T")
    # best-effort failure must NOT block the MTGO chain
    assert report.ok is True
    statuses = {s.name: s.status for s in report.steps}
    assert statuses == {"melee": "warned", "mtgo_scrape": "ok", "import": "ok"}
    assert alerter.alerts == [("warning", alerter.alerts[0][1])]
    assert "melee" in alerter.alerts[0][1]


def test_write_status_appends_jsonl(tmp_path):
    report = RunReport(started_at="T")
    report.steps.append(StepResult("a", "ok", "detail"))
    path = write_status(tmp_path, report)
    path = write_status(tmp_path, report)
    lines = path.read_text().strip().splitlines()
    assert len(lines) == 2
    rec = json.loads(lines[0])
    assert rec["ok"] is True and rec["steps"][0]["name"] == "a"


# ------------------------------------------------------------- alerting

def test_logging_alerter_writes_and_notifies(tmp_path):
    log = tmp_path / "alerts.jsonl"
    marker = tmp_path / "notified.txt"
    # a harmless notify command that records it fired
    alerter = LoggingAlerter(log, notify_cmd=f"cat > {marker}")
    alerter.alert("subject line", "body text", level="error")
    rec = json.loads(log.read_text().strip())
    assert rec["subject"] == "subject line" and rec["level"] == "error"
    assert marker.exists() and "subject line" in marker.read_text()


# ------------------------------------------------------------- run_scrape

def _event_html(name: str) -> str:
    return (FIX / name).read_text(encoding="utf-8", errors="replace")


def test_run_scrape_targets_only_enabled_formats_and_writes(tmp_path):
    cache_root = tmp_path / "cache"
    # a tiny listing with one modern (enabled) + one legacy (disabled) event
    listing = (
        '<a href="/decklist/modern-challenge-32-2026-07-0412846483"></a>'
        '<a href="/decklist/legacy-challenge-32-2026-07-0499999999"></a>'
    )
    # transport returns the real challenge page for the modern event
    resp = Response(200, _event_html("modern-challenge-32-2026-07-0412846483.html").encode(),
                    "https://www.mtgo.com/decklist/modern-challenge-32-2026-07-0412846483")
    fetcher, _ = _fetcher(tmp_path, FakeTransport([resp]), min_interval=0.0)

    stats = run_scrape(fetcher, cache_root, listing_html=listing)
    assert stats.events_listed == 2
    assert stats.events_targeted == 1  # legacy is import-disabled -> not fetched
    assert stats.written == 1
    written = cache_root / cacheitem_relpath("modern-challenge-32-2026-07-0412846483")
    assert written.exists()


def test_run_scrape_skips_already_have(tmp_path):
    cache_root = tmp_path / "cache"
    slug = "modern-challenge-32-2026-07-0412846483"
    # pre-write the CacheItem so the event is "already have"
    (cache_root / cacheitem_relpath(slug)).parent.mkdir(parents=True, exist_ok=True)
    (cache_root / cacheitem_relpath(slug)).write_text("{}")
    listing = f'<a href="/decklist/{slug}"></a>'
    fetcher, _ = _fetcher(tmp_path, FakeTransport([]), min_interval=0.0)  # must not be called
    stats = run_scrape(fetcher, cache_root, listing_html=listing)
    assert stats.already_have == 1 and stats.fetched == 0 and stats.written == 0


def test_run_scrape_counts_unavailable_and_parse_errors(tmp_path):
    cache_root = tmp_path / "cache"
    good = "modern-league-2026-07-0610847"
    unavail = "modern-league-2026-07-0810847"
    garbage = "modern-challenge-32-2026-07-0100000000"
    listing = "".join(f'<a href="/decklist/{s}"></a>' for s in (good, unavail, garbage))

    def transport(url, headers, timeout):
        if good in url:
            body = _event_html("modern-league-2026-07-0610847.html").encode()
            return Response(200, body, url)
        if garbage in url:
            return Response(200, b"<html>no data blob here</html>", url)
        # unavailable -> redirected to listing
        return Response(200, b"", "https://www.mtgo.com/decklists")

    fetcher, _ = _fetcher(tmp_path, transport, min_interval=0.0)
    stats = run_scrape(fetcher, cache_root, listing_html=listing)
    assert stats.written == 1  # the league
    assert stats.unavailable == 1
    assert stats.parse_errors == 1 and stats.parse_error_slugs == [garbage]


def test_run_scrape_output_matches_direct_parse(tmp_path):
    """The scrape-written CacheItem is exactly what the parser produces."""
    import orjson

    cache_root = tmp_path / "cache"
    slug = "modern-league-2026-07-0610847"
    resp = Response(200, _event_html(f"{slug}.html").encode(),
                    f"https://www.mtgo.com/decklist/{slug}")
    fetcher, _ = _fetcher(tmp_path, FakeTransport([resp]), min_interval=0.0)
    run_scrape(fetcher, cache_root, listing_html=f'<a href="/decklist/{slug}"></a>')

    written = orjson.loads((cache_root / cacheitem_relpath(slug)).read_bytes())
    direct = event_to_cacheitem(extract_decklists_data(_event_html(f"{slug}.html")))
    assert written == direct
