"""Liveness and readiness probes."""

from __future__ import annotations

import logging

from fastapi import APIRouter, HTTPException, status
from sqlalchemy import text

from app import __version__
from app.core.deps import DbSession

router = APIRouter(tags=["health"])
logger = logging.getLogger(__name__)


@router.get("/health")
def health() -> dict[str, str]:
    """Liveness: the process is up."""
    return {"status": "ok", "version": __version__}


@router.get("/health/ready")
def ready(db: DbSession) -> dict[str, str]:
    """Readiness: the database is reachable."""
    try:
        db.execute(text("SELECT 1"))
    except Exception as exc:  # noqa: BLE001 - report any DB failure as not-ready
        logger.error("readiness check failed: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="database not ready"
        ) from exc
    return {"status": "ready"}
