"""Request-scoped database access for the read API.

One connection per request, opened against ``app.state.database_url`` (set
by the app factory so tests can point the same app at a test database).
Read-only usage; no transaction is ever committed here.
"""

from __future__ import annotations

from collections.abc import Iterator
from typing import Annotated

import psycopg
from fastapi import Depends, Request


def get_conn(request: Request) -> Iterator[psycopg.Connection]:
    with psycopg.connect(request.app.state.database_url) as conn:
        yield conn


Conn = Annotated[psycopg.Connection, Depends(get_conn)]
