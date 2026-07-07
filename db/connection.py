"""Database connection helpers.

All code obtains connections here so that DATABASE_URL is the single source
of configuration.
"""

from __future__ import annotations

import os

import psycopg

DEFAULT_DATABASE_URL = "postgresql://metagame:metagame@localhost:5432/metagame"


def database_url() -> str:
    return os.environ.get("DATABASE_URL", DEFAULT_DATABASE_URL)


def connect(autocommit: bool = False) -> psycopg.Connection:
    return psycopg.connect(database_url(), autocommit=autocommit)
