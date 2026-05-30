"""RAG query endpoints — non-streaming JSON and streaming SSE."""

from __future__ import annotations

import json
import logging
import uuid

from fastapi import APIRouter, HTTPException, status
from fastapi.responses import StreamingResponse

from app.core.deps import CurrentUser, DbSession
from app.models.constants import DocumentStatus
from app.models.document import Document
from app.schemas.query import QueryRequest, QueryResponse
from app.services import rag

router = APIRouter(prefix="/documents", tags=["query"])
logger = logging.getLogger(__name__)


def _get_ready_document(db, current_user, document_id: uuid.UUID) -> Document:
    document = db.get(Document, document_id)
    if document is None or document.owner_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document not found")
    if document.status != DocumentStatus.READY:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Document is not ready for querying (status={document.status}).",
        )
    return document


@router.post("/{document_id}/query", response_model=QueryResponse)
def query_document(
    document_id: uuid.UUID, payload: QueryRequest, db: DbSession, current_user: CurrentUser
) -> dict:
    """Answer a question about the document (full response, non-streaming)."""
    document = _get_ready_document(db, current_user, document_id)
    return rag.answer(db, document=document, question=payload.question, top_k=payload.top_k)


@router.post("/{document_id}/query/stream")
def query_document_stream(
    document_id: uuid.UUID, payload: QueryRequest, db: DbSession, current_user: CurrentUser
) -> StreamingResponse:
    """Stream the answer as Server-Sent Events.

    Event payloads (JSON after ``data:``) have a ``type`` of ``sources`` | ``delta`` |
    ``done`` | ``error``.
    """
    document = _get_ready_document(db, current_user, document_id)

    def event_gen():
        try:
            for event in rag.answer_stream(
                db, document=document, question=payload.question, top_k=payload.top_k
            ):
                yield f"data: {json.dumps(event)}\n\n"
        except Exception as exc:  # noqa: BLE001 - surface a clean error event to the client
            logger.exception("stream query failed")
            yield f"data: {json.dumps({'type': 'error', 'detail': str(exc)})}\n\n"

    return StreamingResponse(
        event_gen(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )
