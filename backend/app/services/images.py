"""Persist extracted document images to disk + database."""

from __future__ import annotations

import logging
import uuid
from pathlib import Path

from sqlalchemy.orm import Session

from app.core.logging_config import log_event
from app.models.document import Document
from app.models.document_image import DocumentImage
from app.services.extraction.image_extractor import ExtractedImage

logger = logging.getLogger(__name__)


def store_document_images(
    db: Session, *, document: Document, extracted: list[ExtractedImage], base_dir: str
) -> int:
    """Write image files and insert ``document_images`` rows. Returns count stored."""
    if not extracted:
        log_event(logger, "images.extracted", document_id=str(document.id), count=0)
        return 0

    image_dir = Path(base_dir) / str(document.owner_id) / str(document.id) / "images"
    image_dir.mkdir(parents=True, exist_ok=True)

    rows: list[DocumentImage] = []
    for item in extracted:
        image_id = uuid.uuid4()
        path = image_dir / f"{image_id}.{item.ext}"
        path.write_bytes(item.data)
        rows.append(
            DocumentImage(
                id=image_id,
                document_id=document.id,
                owner_id=document.owner_id,
                page_number=item.page_number,
                image_index=item.image_index,
                ext=item.ext,
                width=item.width,
                height=item.height,
                sha256=item.sha256,
                path=str(path),
            )
        )

    db.add_all(rows)
    db.flush()
    log_event(logger, "images.extracted", document_id=str(document.id), count=len(rows))
    return len(rows)
