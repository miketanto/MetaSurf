"""TopDeck Tournament Data API v2 client.

Politeness: the API key rides the Authorization header; requests are throttled
(default 0.6s -> <=100/min, the documented limit) with exponential backoff on
5xx/429; raw JSON responses are archived before parsing. Network is the only
external and is injectable, so the client is unit-tested without sockets.
Stdlib only.
"""

from __future__ import annotations

import json
import time
import urllib.error
import urllib.request
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from ingest.topdeck_scraper import SOURCE

API_BASE = "https://topdeck.gg/api"


@dataclass(frozen=True)
class Response:
    status: int
    body: bytes


# transport(method, url, headers, body, timeout) -> Response
Transport = Callable[[str, str, dict[str, str], bytes | None, float], Response]


def urllib_transport(
    method: str, url: str, headers: dict[str, str], body: bytes | None, timeout: float
) -> Response:
    req = urllib.request.Request(url, data=body, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return Response(resp.status, resp.read())
    except urllib.error.HTTPError as exc:
        return Response(exc.code, exc.read())


class TopdeckError(RuntimeError):
    pass


class TopdeckClient:
    def __init__(
        self,
        api_key: str,
        transport: Transport = urllib_transport,
        *,
        raw_root: Path | None = None,
        min_interval: float = 0.6,
        max_retries: int = 4,
        backoff_base: float = 1.0,
        timeout: float = 30.0,
        sleep: Callable[[float], None] = time.sleep,
        monotonic: Callable[[], float] = time.monotonic,
    ):
        if not api_key:
            raise TopdeckError("a TopDeck API key is required")
        self._key = api_key
        self._transport = transport
        self._raw_root = Path(raw_root) if raw_root else None
        self._min_interval = min_interval
        self._max_retries = max_retries
        self._backoff_base = backoff_base
        self._timeout = timeout
        self._sleep = sleep
        self._monotonic = monotonic
        self._last = 0.0

    def _throttle(self) -> None:
        wait = self._min_interval - (self._monotonic() - self._last)
        if wait > 0:
            self._sleep(wait)
        self._last = self._monotonic()

    def _request(self, method: str, path: str, body: dict[str, Any] | None = None) -> Any:
        url = f"{API_BASE}{path}"
        headers = {"Authorization": self._key, "Accept": "application/json"}
        payload: bytes | None = None
        if body is not None:
            payload = json.dumps(body).encode()
            headers["Content-Type"] = "application/json"
        last: Exception | None = None
        for attempt in range(self._max_retries + 1):
            self._throttle()
            try:
                resp = self._transport(method, url, headers, payload, self._timeout)
            except Exception as exc:  # network is the external boundary
                last = exc
            else:
                if resp.status == 200:
                    return json.loads(resp.body)
                if resp.status < 500 and resp.status != 429:
                    raise TopdeckError(f"{method} {path} -> HTTP {resp.status}")
                last = TopdeckError(f"{method} {path} -> HTTP {resp.status}")
            if attempt < self._max_retries:
                self._sleep(self._backoff_base * (2**attempt))
        raise TopdeckError(f"failed {method} {path}: {last}")

    def _archive(self, tid: str, kind: str, obj: Any) -> None:
        if self._raw_root is None:
            return
        path = self._raw_root / SOURCE / f"{tid}.{kind}.json"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(json.dumps(obj).encode())

    # -- endpoints (documented v2) --------------------------------------

    def search(
        self, game: str, fmt: str, start: str | None = None, end: str | None = None
    ) -> list[dict[str, Any]]:
        """POST /v2/tournaments — completed tournaments for a game+format."""
        body: dict[str, Any] = {"game": game, "format": fmt}
        if start:
            body["start"] = start
        if end:
            body["end"] = end
        result = self._request("POST", "/v2/tournaments", body)
        return result if isinstance(result, list) else result.get("tournaments", [])

    def info(self, tid: str) -> dict[str, Any]:
        obj = self._request("GET", f"/v2/tournaments/{tid}/info")
        self._archive(tid, "info", obj)
        return obj

    def standings(self, tid: str) -> list[dict[str, Any]]:
        obj = self._request("GET", f"/v2/tournaments/{tid}/standings")
        self._archive(tid, "standings", obj)
        return obj

    def rounds(self, tid: str) -> list[dict[str, Any]]:
        obj = self._request("GET", f"/v2/tournaments/{tid}/rounds")
        self._archive(tid, "rounds", obj)
        return obj
