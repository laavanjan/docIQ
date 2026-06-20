"""Document endpoints: upload (with extraction method), list, get, delete."""

from __future__ import annotations

import logging
import uuid
from pathlib import Path

from fastapi import (
    APIRouter,
    BackgroundTasks,
    File,
    Form,
    HTTPException,
    Query,
    Response,
    UploadFile,
    status,
)
from fastapi.responses import FileResponse
from sqlalchemy import select

from app.core.config import settings
from app.core.deps import CurrentUser, DbSession
from app.core.request_context import get_request_id
from app.models.constants import DocumentStatus, ExtractionMethod
from app.models.document import Document
from app.models.document_image import DocumentImage
from app.schemas.document import DocumentImageRead, DocumentRead
from app.services.pipeline import process_document

router = APIRouter(prefix="/documents", tags=["documents"])
logger = logging.getLogger(__name__)


def _get_owned(db, current_user, document_id: uuid.UUID) -> Document:
    document = db.get(Document, document_id)
    if document is None or document.owner_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document not found")
    return document


@router.post("", response_model=DocumentRead, status_code=status.HTTP_201_CREATED)
async def upload_document(
    db: DbSession,
    current_user: CurrentUser,
    background: BackgroundTasks,
    file: UploadFile = File(...),
    method: str = Form(ExtractionMethod.TEXT),
) -> Document:
    """Upload a PDF and kick off ingestion in the background.

    ``method`` selects the extraction strategy: ``text`` | ``ocr`` | ``vision``.
    """
    if method not in ExtractionMethod.ALL:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Invalid method. Choose one of {ExtractionMethod.ALL}.",
        )
    filename = file.filename or ""
    is_pdf = (file.content_type == "application/pdf") or filename.lower().endswith(".pdf")
    if not is_pdf:
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail="Only PDF files are supported.",
        )

    data = await file.read()
    if len(data) > settings.max_upload_bytes:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"File exceeds the {settings.max_upload_mb} MB limit.",
        )

    document_id = uuid.uuid4()
    user_dir = Path(settings.upload_dir) / str(current_user.id)
    user_dir.mkdir(parents=True, exist_ok=True)
    storage_path = user_dir / f"{document_id}.pdf"
    storage_path.write_bytes(data)

    document = Document(
        id=document_id,
        owner_id=current_user.id,
        filename=filename or f"{document_id}.pdf",
        content_type=file.content_type or "application/pdf",
        size_bytes=len(data),
        storage_path=str(storage_path),
        extraction_method=method,
        status=DocumentStatus.PROCESSING,
    )
    db.add(document)
    db.commit()
    db.refresh(document)

    logger.info(
        "document uploaded",
        extra={
            "event": "document.upload",
            "document_id": str(document_id),
            "method": method,
            "size_bytes": len(data),
        },
    )
    # Run extraction/embedding outside the request; propagate the request id for tracing.
    background.add_task(process_document, document.id, get_request_id())
    return document


@router.get("", response_model=list[DocumentRead])
def list_documents(db: DbSession, current_user: CurrentUser) -> list[Document]:
    documents = db.scalars(
        select(Document)
        .where(Document.owner_id == current_user.id)
        .order_by(Document.created_at.desc())
    ).all()
    return list(documents)


@router.get("/{document_id}", response_model=DocumentRead)
def get_document(document_id: uuid.UUID, db: DbSession, current_user: CurrentUser) -> Document:
    return _get_owned(db, current_user, document_id)


@router.get("/{document_id}/images", response_model=list[DocumentImageRead])
def list_document_images(
    document_id: uuid.UUID,
    db: DbSession,
    current_user: CurrentUser,
    pages: str | None = Query(
        default=None,
        description="Comma-separated page numbers to filter by (e.g. '3,5'). Omit for all images.",
    ),
) -> list[DocumentImage]:
    document = _get_owned(db, current_user, document_id)
    stmt = select(DocumentImage).where(DocumentImage.document_id == document.id)
    if pages:
        page_numbers = [int(p) for p in pages.split(",") if p.strip().isdigit()]
        if not page_numbers:
            return []
        stmt = stmt.where(DocumentImage.page_number.in_(page_numbers))
    stmt = stmt.order_by(DocumentImage.page_number, DocumentImage.image_index)
    return list(db.scalars(stmt).all())


@router.get("/{document_id}/images/{image_id}")
def get_document_image(
    document_id: uuid.UUID, image_id: uuid.UUID, db: DbSession, current_user: CurrentUser
) -> FileResponse:
    document = _get_owned(db, current_user, document_id)
    image = db.get(DocumentImage, image_id)
    if image is None or image.document_id != document.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Image not found")
    media_type = "image/jpeg" if image.ext in ("jpg", "jpeg") else f"image/{image.ext}"
    return FileResponse(image.path, media_type=media_type)


@router.delete("/{document_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_document(
    document_id: uuid.UUID, db: DbSession, current_user: CurrentUser
) -> Response:
    document = _get_owned(db, current_user, document_id)
    try:
        Path(document.storage_path).unlink(missing_ok=True)
    except OSError:  # pragma: no cover - best-effort file cleanup
        logger.warning("could not delete file for document %s", document_id)
    db.delete(document)  # cascades to chunks
    db.commit()
    logger.info(
        "document deleted",
        extra={"event": "document.delete", "document_id": str(document_id)},
    )
    return Response(status_code=status.HTTP_204_NO_CONTENT)
