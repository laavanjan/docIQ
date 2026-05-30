"""Aggregate API router mounted under the versioned prefix (e.g. ``/api/v1``)."""

from __future__ import annotations

from fastapi import APIRouter

from app.api.routes import auth, documents, query

api_router = APIRouter()
api_router.include_router(auth.router)
api_router.include_router(documents.router)
api_router.include_router(query.router)
