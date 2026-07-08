"""Serving entrypoint: composition root for the read API.

api/ is game-neutral by CI gate and depends only on the ClassifierService
Protocol; the game adapters are wired in here, outside the gated packages.

Run: uvicorn serve:app
"""

from __future__ import annotations

from api.app import create_app
from archetypes.service import MtgClassifierService

app = create_app(classifiers={"mtg": MtgClassifierService()})

# The emerging-feed READ path (GET /emerging) needs no injection here: it
# serves the precomputed rollup_emerging tables like any other rollup. The
# emerging BUILD path (the clustering stage, game-specific) has its own
# composition root — scripts/build_emerging.py — which wires the MTG
# EmergingBuilder adapter behind api.emerging's Protocol, since building is a
# batch/nightly job rather than a per-request path.
