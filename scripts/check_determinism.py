#!/usr/bin/env python3
"""CI gate: the normalization pipeline must be byte-deterministic.

Runs the full fixture corpus through discovery + normalization twice, in
independent passes, serializes the canonical output and asserts identical
SHA-256 digests. (Full-DB rebuild determinism is demonstrated at milestone
gates by rebuilding twice and diffing the data-quality reports.)
"""

from __future__ import annotations

import dataclasses
import hashlib
import json
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO))

from ingest.cache_import.importer import ImportStats, discover_files  # noqa: E402
from ingest.formats_config import load_formats  # noqa: E402
from ingest.normalize.cache_item import normalize_file  # noqa: E402

FIXTURES = REPO / "tests" / "fixtures" / "MTGODecklistCache"


def one_pass() -> str:
    formats = load_formats()
    tokens = {f.name: f.slug_tokens for f in formats}
    targets = {f.name for f in formats if f.do_import}
    stats = ImportStats()
    files = discover_files(FIXTURES, tokens, targets, stats)
    out = []
    for path, source, fmt in files:
        ev = normalize_file(path, FIXTURES, source)
        out.append((fmt, dataclasses.asdict(ev)))
    blob = json.dumps(out, sort_keys=True, default=str).encode()
    return hashlib.sha256(blob).hexdigest()


def main() -> int:
    h1, h2 = one_pass(), one_pass()
    if h1 != h2:
        print(f"determinism check FAILED: {h1} != {h2}")
        return 1
    print(f"determinism check passed: sha256 {h1}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
