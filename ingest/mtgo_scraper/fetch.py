"""Polite HTTP fetcher + immutable raw archive for mtgo.com.

Politeness contract (CLAUDE.md, plan §11):
- custom User-Agent identifying the project + a contact,
- <= 1 request/second/host (token-timed, not per-call sleeps),
- exponential backoff on transient failures,
- cache everything: an event whose raw HTML is already archived is never
  re-fetched (the archive is served instead),
- raw responses are written to the archive BEFORE any parsing.

Network and clock are the only true externals; both are injectable so the
fetcher is unit-tested without touching the network (CLAUDE.md testing rule 2).
Uses the stdlib only — no runtime HTTP dependency (plan §4: keep it boring).
"""

from __future__ import annotations

import time
import urllib.error
import urllib.request
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import urlsplit

from ingest.mtgo_scraper.pipeline import SOURCE, slug_date

BASE_URL = "https://www.mtgo.com"
DEFAULT_UA = (
    "MetaSurfBot/0.1 (+https://github.com/miketanto/MetaSurf; "
    "metagame research; contact mikesutanto1812@gmail.com)"
)


@dataclass(frozen=True)
class Response:
    status: int
    body: bytes
    final_url: str


# transport(url, headers, timeout) -> Response. The default hits the network;
# tests inject a fake.
Transport = Callable[[str, dict[str, str], float], Response]


def urllib_transport(url: str, headers: dict[str, str], timeout: float) -> Response:
    req = urllib.request.Request(url, headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return Response(resp.status, resp.read(), resp.geturl())
    except urllib.error.HTTPError as exc:
        # an HTTP error still carries a status + body; surface it, don't raise
        return Response(exc.code, exc.read(), url)


class RawArchive:
    """Immutable raw-HTML store, keyed by source/date/slug (plan §4)."""

    def __init__(self, root: Path, source: str = SOURCE):
        self.root = Path(root)
        self.source = source

    def path_for(self, slug: str) -> Path:
        d = slug_date(slug)
        return (
            self.root
            / self.source
            / f"{d.year:04d}"
            / f"{d.month:02d}"
            / f"{d.day:02d}"
            / f"{slug}.html"
        )

    def exists(self, slug: str) -> bool:
        return self.path_for(slug).exists()

    def read(self, slug: str) -> bytes:
        return self.path_for(slug).read_bytes()

    def write(self, slug: str, body: bytes) -> Path:
        path = self.path_for(slug)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(body)
        return path


class FetchError(RuntimeError):
    """A URL could not be fetched after all retries."""


class Fetcher:
    def __init__(
        self,
        archive: RawArchive,
        transport: Transport = urllib_transport,
        *,
        user_agent: str = DEFAULT_UA,
        min_interval: float = 1.0,
        max_retries: int = 4,
        backoff_base: float = 1.0,
        timeout: float = 30.0,
        sleep: Callable[[float], None] = time.sleep,
        monotonic: Callable[[], float] = time.monotonic,
    ):
        self._archive = archive
        self._transport = transport
        self._ua = user_agent
        self._min_interval = min_interval
        self._max_retries = max_retries
        self._backoff_base = backoff_base
        self._timeout = timeout
        self._sleep = sleep
        self._monotonic = monotonic
        self._last_request: dict[str, float] = {}

    # -- politeness ------------------------------------------------------

    def _throttle(self, url: str) -> None:
        host = urlsplit(url).netloc
        last = self._last_request.get(host)
        now = self._monotonic()
        if last is not None:
            wait = self._min_interval - (now - last)
            if wait > 0:
                self._sleep(wait)
        self._last_request[host] = self._monotonic()

    def get(self, url: str) -> Response:
        """Rate-limited GET with exponential backoff on transient failures.

        Retries network errors and 5xx/429; returns 4xx and 3xx immediately
        (the caller decides what a redirect/not-found means)."""
        headers = {"User-Agent": self._ua}
        last_exc: Exception | None = None
        for attempt in range(self._max_retries + 1):
            self._throttle(url)
            try:
                resp = self._transport(url, headers, self._timeout)
            except Exception as exc:
                last_exc = exc
            else:
                if resp.status < 500 and resp.status != 429:
                    return resp
                last_exc = FetchError(f"{url} -> HTTP {resp.status}")
            if attempt < self._max_retries:
                self._sleep(self._backoff_base * (2**attempt))
        raise FetchError(f"failed to fetch {url}: {last_exc}")

    # -- fetch operations ------------------------------------------------

    def fetch_listing(self, year: int | None = None, month: int | None = None) -> str:
        url = f"{BASE_URL}/decklists"
        if year is not None and month is not None:
            url += f"?year={year}&month={month}"
        resp = self.get(url)
        if resp.status != 200:
            raise FetchError(f"listing {url} -> HTTP {resp.status}")
        return resp.body.decode("utf-8", errors="replace")

    def fetch_event(self, slug: str) -> bytes | None:
        """Raw HTML for an event, archived before return. Cached: an already-
        archived event is served from disk, never re-fetched. Returns None if
        the event is not available (redirect away from its own URL — observed
        for not-yet-published days), which is not a failure.
        """
        if self._archive.exists(slug):
            return self._archive.read(slug)
        url = f"{BASE_URL}/decklist/{slug}"
        resp = self.get(url)
        # a missing event 302s to /decklists; the transport follows redirects,
        # so a final_url that is no longer this event's page means "unavailable"
        if resp.status != 200 or f"/decklist/{slug}" not in resp.final_url:
            return None
        # raw archive BEFORE any parsing (plan §1: raw data is sacred)
        self._archive.write(slug, resp.body)
        return resp.body
