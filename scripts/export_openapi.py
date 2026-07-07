#!/usr/bin/env python3
"""Regenerate the committed OpenAPI contract (api/openapi.json) from the app.

The spec is part of the M5 definition of done (plan §7) and a client
contract: regenerate and commit it whenever the API shape changes; a test
asserts the committed file matches the running app.
"""

from __future__ import annotations

import json
from pathlib import Path

from api.app import create_app

OUT = Path(__file__).resolve().parent.parent / "api" / "openapi.json"


def main() -> None:
    spec = create_app().openapi()
    OUT.write_text(json.dumps(spec, indent=2, sort_keys=True) + "\n")
    print(f"wrote {OUT}")


if __name__ == "__main__":
    main()
