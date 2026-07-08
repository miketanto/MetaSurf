"""TopDeck client + scrape tests. Network is faked (no sockets)."""

from __future__ import annotations

import json
from pathlib import Path

import orjson
import pytest

from ingest.topdeck_scraper.client import Response, TopdeckClient, TopdeckError
from ingest.topdeck_scraper.scrape import run_scrape

FIX = (
    Path(__file__).resolve().parent
    / "fixtures" / "topdeck.gg" / "real-modern-with-decklists.json"
)


class FakeClock:
    def __init__(self):
        self.t = 1000.0
        self.slept = []

    def monotonic(self):
        return self.t

    def sleep(self, s):
        self.slept.append(s)
        self.t += s


class FakeTransport:
    """Routes by (method, path); records Authorization header seen."""

    def __init__(self, routes):
        self.routes = routes
        self.calls = []
        self.auth_seen = []

    def __call__(self, method, url, headers, body, timeout):
        self.auth_seen.append(headers.get("Authorization"))
        path = url.split("/api", 1)[1]
        self.calls.append((method, path))
        for (m, p), resp in self.routes.items():
            if m == method and p in path:
                return resp() if callable(resp) else resp
        return Response(404, b"{}")


def _json(obj, status=200):
    return Response(status, json.dumps(obj).encode())


def _client(transport, **kw):
    clk = FakeClock()
    return TopdeckClient(
        "SECRETKEY", transport, min_interval=0.0, sleep=clk.sleep, monotonic=clk.monotonic, **kw
    ), clk


def test_requires_api_key():
    with pytest.raises(TopdeckError):
        TopdeckClient("")


def test_sends_authorization_header():
    t = FakeTransport({("GET", "/standings"): _json([])})
    c, _ = _client(t)
    c.standings("TID1")
    assert t.auth_seen[-1] == "SECRETKEY"


def test_backoff_on_5xx_then_success():
    calls = {"n": 0}

    def flaky():
        calls["n"] += 1
        return Response(503, b"") if calls["n"] < 3 else _json([{"standing": 1}])

    t = FakeTransport({("GET", "/standings"): flaky})
    c, clk = _client(t, backoff_base=1.0)
    assert c.standings("TID1") == [{"standing": 1}]
    assert clk.slept == [1.0, 2.0]


def test_4xx_not_retried():
    t = FakeTransport({("GET", "/standings"): Response(403, b"{}")})
    c, _ = _client(t)
    with pytest.raises(TopdeckError):
        c.standings("TID1")
    assert len([x for x in t.calls if x[1].endswith("/standings")]) == 1


def test_archives_raw_response(tmp_path):
    t = FakeTransport({("GET", "/standings"): _json([{"standing": 1, "name": "A"}])})
    c, _ = _client(t, raw_root=tmp_path / "raw")
    c.standings("TID1")
    archived = tmp_path / "raw" / "topdeck.gg" / "TID1.standings.json"
    assert archived.exists() and json.loads(archived.read_text())[0]["name"] == "A"


def test_run_scrape_writes_cacheitem(tmp_path):
    # the real search returns tournaments with standings + rounds inline
    tournament = json.loads(FIX.read_text())
    routes = {("POST", "/v2/tournaments"): _json([tournament])}
    c, _ = _client(FakeTransport(routes))
    stats = run_scrape(
        c, tmp_path / "cache", game="Magic: The Gathering", fmt="Modern", format_slug="modern"
    )
    assert stats.tournaments_found == 1 and stats.written == 1 and stats.errors == 0
    tid = tournament["TID"]
    written = tmp_path / "cache" / f"Tournaments/topdeck.gg/2026/07/05/modern-{tid}.json"
    assert written.exists()
    item = orjson.loads(written.read_bytes())
    assert item["Tournament"]["Name"] == "Impact Returns 26 Sunday Modern 2015"
    assert len(item["Decks"]) == 15
    # second run: already have -> nothing written (idempotent)
    stats2 = run_scrape(
        c, tmp_path / "cache", game="Magic: The Gathering", fmt="Modern", format_slug="modern"
    )
    assert stats2.already_have == 1 and stats2.written == 0
