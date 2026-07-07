"""FastAPI read layer (M5, plan §7).

Serves precomputed rollups only — request handling is name joins and
zero-filling; every number was computed offline by jobs/rollups from the
validated models. Namespaced /v1/{game}/{format}/... from day one
(plan §4.1 rule 3).

Run via the composition entrypoint: ``uvicorn serve:app`` (which injects the
game classifier adapters this package may not import; ``uvicorn api.app:app``
also works but serves 501 on /classify). The OpenAPI contract is committed at
``api/openapi.json`` (regenerate with ``python -m scripts.export_openapi``);
a test asserts the committed spec matches the app.
"""

from __future__ import annotations

from collections.abc import Mapping

from fastapi import FastAPI

from api.classifier import ClassifierService
from api.routes import router
from db.connection import database_url

API_VERSION = "0.1.0"


def create_app(
    database_url_override: str | None = None,
    classifiers: Mapping[str, ClassifierService] | None = None,
) -> FastAPI:
    app = FastAPI(
        title="Metagame Read API",
        version=API_VERSION,
        description="Read-only metagame data served from precomputed rollups. "
        "Premium fields are gated by entitlement flags (X-Entitlements header "
        "until real auth lands) and appear locked, never hidden.",
    )
    app.state.database_url = database_url_override or database_url()
    # game name -> ClassifierService, injected by the serving entrypoint
    # (serve.py) so this package never imports game-specific code
    app.state.classifiers = dict(classifiers or {})
    app.include_router(router)
    return app


app = create_app()
