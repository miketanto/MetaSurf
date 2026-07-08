"""Failure alerting for unattended ingestion (M4 DoD: alerting on failure).

Boring by design (plan §4): an alert is a line appended to a JSONL log and
echoed to stderr, plus — if `METASURF_ALERT_CMD` is set — the message piped to
that shell command's stdin. The operator wires that env var to whatever
channel they use (email, Slack webhook, Pushover, ntfy…); the pipeline needs
no code change to add a channel. The alert sink is a Protocol so the daily
runner is unit-tested with a fake.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
from collections.abc import Callable
from datetime import UTC, datetime
from pathlib import Path
from typing import Protocol


class Alerter(Protocol):
    def alert(self, subject: str, body: str, *, level: str = "error") -> None: ...


class LoggingAlerter:
    """Append alerts to a JSONL file, echo to stderr, and optionally invoke
    an external notify command (`METASURF_ALERT_CMD`)."""

    def __init__(
        self,
        log_path: Path,
        notify_cmd: str | None = None,
        *,
        now: Callable[[], datetime] | None = None,
    ):
        self.log_path = Path(log_path)
        if notify_cmd is not None:
            self.notify_cmd: str | None = notify_cmd
        else:
            self.notify_cmd = os.environ.get("METASURF_ALERT_CMD")
        self._now = now or (lambda: datetime.now(UTC))

    def alert(self, subject: str, body: str, *, level: str = "error") -> None:
        ts = self._now().strftime("%Y-%m-%dT%H:%M:%SZ")
        record = {"ts": ts, "level": level, "subject": subject, "body": body}
        self.log_path.parent.mkdir(parents=True, exist_ok=True)
        with self.log_path.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(record) + "\n")
        print(f"[{level.upper()}] {ts} {subject}", file=sys.stderr)
        if self.notify_cmd:
            try:
                subprocess.run(
                    self.notify_cmd,
                    shell=True,
                    input=f"{subject}\n\n{body}",
                    text=True,
                    timeout=30,
                    check=False,
                )
            except Exception as exc:  # never let alerting itself crash the run
                print(f"[WARN] alert notify command failed: {exc}", file=sys.stderr)
