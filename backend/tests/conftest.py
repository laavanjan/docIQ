"""Shared pytest fixtures.

Unit tests (chunking, LLM router) run anywhere. DB-backed tests (health/ready, auth)
require a reachable PostgreSQL+pgvector instance; they're skipped automatically when none
is available by depending on the ``db_required`` fixture.
"""

from __future__ import annotations

import pytest
from sqlalchemy import text

import app.models  # noqa: F401  -- register all tables on Base.metadata
from app.db.base import Base
from app.db.session import engine


def _db_ready() -> bool:
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        return True
    except Exception:
        return False


DB_READY = _db_ready()


@pytest.fixture(scope="session", autouse=True)
def _schema():
    """Create the pgvector extension + tables once for the test session."""
    if DB_READY:
        with engine.begin() as conn:
            conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
        Base.metadata.create_all(engine)
    yield


@pytest.fixture
def db_required():
    if not DB_READY:
        pytest.skip("PostgreSQL not available")


@pytest.fixture
def client():
    from fastapi.testclient import TestClient

    from app.main import app

    return TestClient(app)
