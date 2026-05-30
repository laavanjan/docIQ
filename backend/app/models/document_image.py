"""DocumentImage model — raster images extracted from a PDF, linked to their page."""

from __future__ import annotations

import uuid

from sqlalchemy import ForeignKey, Integer, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, TimestampMixin, UUIDMixin


class DocumentImage(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "document_images"

    document_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("documents.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    owner_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), index=True, nullable=False)

    page_number: Mapped[int] = mapped_column(Integer, index=True, nullable=False)
    image_index: Mapped[int] = mapped_column(Integer, default=0)
    ext: Mapped[str] = mapped_column(String(8), default="png")
    width: Mapped[int] = mapped_column(Integer, default=0)
    height: Mapped[int] = mapped_column(Integer, default=0)
    sha256: Mapped[str] = mapped_column(String(64), index=True)
    path: Mapped[str] = mapped_column(String(1024), nullable=False)
