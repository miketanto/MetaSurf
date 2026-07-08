"""Source attribution/credits, config-driven (game-neutral).

Some data sources require a visible credit + link on any surface that uses
their data (e.g. TopDeck.gg's API terms). Source metadata lives in
config/sources.json — never hardcoded here — so this module carries no
source-specific literals and the game-neutrality gate stays green. Callers
pass the set of source keys present in a response; we return the credits to
display, unknown sources ignored.
"""

from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path

from api.schemas import Credit

_CONFIG = Path(__file__).resolve().parent.parent / "config" / "sources.json"


@lru_cache(maxsize=1)
def _catalog() -> dict[str, dict[str, object]]:
    return json.loads(_CONFIG.read_text()).get("sources", {})


def credits_for(sources: set[str]) -> list[Credit]:
    """Credits for the given source keys, in a stable order (required first,
    then alphabetical)."""
    cat = _catalog()
    out = [
        Credit(
            source=key,
            name=str(meta.get("name", key)),
            url=str(meta.get("url", "")),
            attribution=str(meta.get("attribution", "")),
            required=bool(meta.get("required", False)),
        )
        for key, meta in cat.items()
        if key in sources
    ]
    out.sort(key=lambda c: (not c.required, c.name.lower()))
    return out
