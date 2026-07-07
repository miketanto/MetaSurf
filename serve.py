"""Serving entrypoint: composition root for the read API.

api/ is game-neutral by CI gate and depends only on the ClassifierService
Protocol; the game adapters are wired in here, outside the gated packages.

Run: uvicorn serve:app
"""

from __future__ import annotations

from api.app import create_app
from archetypes.service import MtgClassifierService

app = create_app(classifiers={"mtg": MtgClassifierService()})
