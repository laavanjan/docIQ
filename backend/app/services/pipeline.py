"""End-to-end ingestion orchestration.

``ingest_document`` runs the pipeline within a given session. ``process_document`` is the
entrypoint scheduled as a FastAPI background task: it opens its own session (the request
session is gone by then), re-attaches the request id for log correlation, and records a
failure on the document row instead of crashing silently.
"""

from __future__ import annotations

import logging
import time
import uuid

from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.logging_config import log_event
from app.core.request_context import set_request_id
from app.db.session import SessionLocal
from app.models.constants import DocumentStatus
from app.models.document import Document
from app.services import vectorstore
from app.services.chunking import Chunker
from app.services.embeddings import get_embedder
from app.services.extraction.factory import get_extractor
from app.services.extraction.image_extractor import extract_embedded_images
from app.services.images import store_document_images

logger = logging.getLogger(__name__)


class PipelineError(Exception):
    """Raised when a document cannot be ingested (e.g. nothing extracted)."""


def ingest_document(db: Session, document: Document) -> None:
    """Extract -> chunk -> embed -> store. Commits on success; raises on failure."""
    start = time.perf_counter()
    log_event(
        logger,
        "ingest.start",
        document_id=str(document.id),
        method=document.extraction_method,
        file=document.filename,
    )

    extractor = get_extractor(document.extraction_method)
    result = extractor.extract(document.storage_path)
    document.page_count = result.page_count

    chunks = Chunker().chunk(result.pages)
    if not chunks:
        raise PipelineError("No text could be extracted from the document.")

    embeddings = get_embedder().embed_documents([c.content for c in chunks])
    count = vectorstore.add_chunks(
        db,
        document_id=document.id,
        owner_id=document.owner_id,
        chunks=chunks,
        embeddings=embeddings,
    )

    # Extract embedded images (figures/logos) so the chat can show them for cited pages.
    if settings.extract_images:
        try:
            extracted = extract_embedded_images(
                document.storage_path, settings.image_min_dimension
            )
            store_document_images(
                db, document=document, extracted=extracted, base_dir=settings.upload_dir
            )
        except Exception:  # noqa: BLE001 - image extraction must never fail ingestion
            logger.exception("image extraction failed for document %s", document.id)

    document.chunk_count = count
    document.status = DocumentStatus.READY
    document.error = None
    db.commit()

    log_event(
        logger,
        "ingest.done",
        document_id=str(document.id),
        pages=result.page_count,
        chunks=count,
        ms=round((time.perf_counter() - start) * 1000, 1),
    )


def process_document(document_id: uuid.UUID, request_id: str | None = None) -> None:
    """Background-task entrypoint. Never raises — failures are written to the document row."""
    if request_id:
        set_request_id(request_id)

    db = SessionLocal()
    try:
        document = db.get(Document, document_id)
        if document is None:
            logger.warning("ingest: document %s not found", document_id)
            return
        try:
            ingest_document(db, document)
        except Exception as exc:  # noqa: BLE001 - record failure, don't crash the worker
            db.rollback()
            document = db.get(Document, document_id)
            if document is not None:
                document.status = DocumentStatus.ERROR
                document.error = str(exc)[:2000]
                db.commit()
            logger.exception("ingest failed for document %s", document_id)
    finally:
        db.close()
