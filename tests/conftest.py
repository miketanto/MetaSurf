from __future__ import annotations

import os
import subprocess
from pathlib import Path

import psycopg
import pytest

REPO = Path(__file__).resolve().parent.parent
FIXTURES = REPO / "tests" / "fixtures" / "MTGODecklistCache"

TEST_DB = "metagame_test"


def _admin_url() -> str:
    """Server-level URL derived from DATABASE_URL, pointing at the postgres db."""
    from db.connection import database_url

    base, _, _ = database_url().rpartition("/")
    return f"{base}/postgres"


def _test_url() -> str:
    base, _, _ = _admin_url().rpartition("/")
    return f"{base}/{TEST_DB}"


@pytest.fixture(scope="session")
def test_db_url() -> str:
    """Fresh, migrated test database; requires a reachable Postgres server."""
    try:
        admin = psycopg.connect(_admin_url(), autocommit=True)
    except psycopg.OperationalError as exc:  # pragma: no cover
        pytest.skip(f"no PostgreSQL server available: {exc}")
    with admin.cursor() as cur:
        cur.execute(f"DROP DATABASE IF EXISTS {TEST_DB} (FORCE)")
        cur.execute(f"CREATE DATABASE {TEST_DB}")
    admin.close()
    env = dict(os.environ, DATABASE_URL=_test_url())
    subprocess.run(
        ["alembic", "upgrade", "head"], cwd=REPO, env=env, check=True, capture_output=True
    )
    return _test_url()


@pytest.fixture()
def db_conn(test_db_url: str):
    conn = psycopg.connect(test_db_url)
    yield conn
    conn.close()
