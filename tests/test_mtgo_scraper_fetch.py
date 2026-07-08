"""Fetcher tests. The network and the clock are the only externals and both
are faked (CLAUDE.md: mock only true externals). No sockets, no real sleeps."""

from __future__ import annotations

import pytest

from ingest.mtgo_scraper.fetch import (
    BASE_URL,
    DEFAULT_UA,
    Fetcher,
    FetchError,
    RawArchive,
    Response,
)

SLUG = "modern-challenge-32-2026-07-0412846483"
EVENT_URL = f"{BASE_URL}/decklist/{SLUG}"


class FakeClock:
    def __init__(self) -> None:
        self.t = 1000.0
        self.slept: list[float] = []

    def monotonic(self) -> float:
        return self.t

    def sleep(self, seconds: float) -> None:
        self.slept.append(seconds)
        self.t += seconds  # sleeping advances the clock


class FakeTransport:
    """Returns scripted responses; records every requested (url, headers)."""

    def __init__(self, responses: list[Response] | Exception) -> None:
        self._responses = responses
        self.calls: list[tuple[str, dict[str, str]]] = []

    def __call__(self, url: str, headers: dict[str, str], timeout: float) -> Response:
        self.calls.append((url, dict(headers)))
        if isinstance(self._responses, Exception):
            raise self._responses
        return self._responses[min(len(self.calls) - 1, len(self._responses) - 1)]


def _fetcher(tmp_path, transport, clock=None, **kw):
    clock = clock or FakeClock()
    return (
        Fetcher(
            RawArchive(tmp_path / "raw"),
            transport,
            sleep=clock.sleep,
            monotonic=clock.monotonic,
            **kw,
        ),
        clock,
    )


def _ok(body: bytes = b"<html>ok</html>", url: str = EVENT_URL) -> Response:
    return Response(200, body, url)


def test_sends_custom_user_agent(tmp_path):
    t = FakeTransport([_ok()])
    f, _ = _fetcher(tmp_path, t)
    f.get(EVENT_URL)
    assert t.calls[0][1]["User-Agent"] == DEFAULT_UA
    assert "MetaSurf" in DEFAULT_UA


def test_rate_limits_to_one_per_second_per_host(tmp_path):
    t = FakeTransport([_ok(), _ok()])
    f, clock = _fetcher(tmp_path, t, min_interval=1.0)
    f.get(EVENT_URL)
    f.get(EVENT_URL)  # immediately after: must wait ~1s
    assert clock.slept and abs(clock.slept[0] - 1.0) < 1e-9


def test_exponential_backoff_then_success(tmp_path):
    t = FakeTransport([Response(503, b"", EVENT_URL), Response(503, b"", EVENT_URL), _ok()])
    f, clock = _fetcher(tmp_path, t, min_interval=0.0, backoff_base=1.0)
    resp = f.get(EVENT_URL)
    assert resp.status == 200
    # two retries -> backoff sleeps 1.0 then 2.0 (min_interval=0 -> no throttle)
    assert clock.slept == [1.0, 2.0]


def test_retries_exhausted_raises(tmp_path):
    t = FakeTransport([Response(500, b"", EVENT_URL)])
    f, _ = _fetcher(tmp_path, t, min_interval=0.0, max_retries=2)
    with pytest.raises(FetchError):
        f.get(EVENT_URL)
    assert len(t.calls) == 3  # initial + 2 retries


def test_network_exception_is_retried(tmp_path):
    f, _ = _fetcher(tmp_path, FakeTransport(OSError("connection reset")), min_interval=0.0)
    with pytest.raises(FetchError):
        f.get(EVENT_URL)


def test_client_error_not_retried(tmp_path):
    t = FakeTransport([Response(404, b"", EVENT_URL)])
    f, _ = _fetcher(tmp_path, t, min_interval=0.0)
    resp = f.get(EVENT_URL)
    assert resp.status == 404
    assert len(t.calls) == 1  # 4xx returned immediately


def test_fetch_event_archives_before_return(tmp_path):
    t = FakeTransport([_ok(b"<html>event</html>")])
    f, _ = _fetcher(tmp_path, t, min_interval=0.0)
    body = f.fetch_event(SLUG)
    assert body == b"<html>event</html>"
    archived = RawArchive(tmp_path / "raw").path_for(SLUG)
    assert archived.exists()
    assert archived.read_bytes() == b"<html>event</html>"


def test_archived_event_not_refetched(tmp_path):
    RawArchive(tmp_path / "raw").write(SLUG, b"<html>cached</html>")
    t = FakeTransport([_ok(b"<html>fresh</html>")])
    f, _ = _fetcher(tmp_path, t, min_interval=0.0)
    body = f.fetch_event(SLUG)
    assert body == b"<html>cached</html>"
    assert t.calls == []  # never hit the network


def test_unavailable_event_redirects_to_listing(tmp_path):
    # a not-yet-published event 302s; transport follows to /decklists
    t = FakeTransport([Response(200, b"<html>listing</html>", f"{BASE_URL}/decklists")])
    f, _ = _fetcher(tmp_path, t, min_interval=0.0)
    assert f.fetch_event(SLUG) is None
    assert not RawArchive(tmp_path / "raw").exists(SLUG)  # not archived
