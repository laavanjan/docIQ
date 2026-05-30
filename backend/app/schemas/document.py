"""Document response schema."""

from __future__ import annotations

import datetime
import uuid

from pydantic import BaseModel, ConfigDict


class DocumentRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    filename: str
    content_type: str
    size_bytes: int
    extraction_method: str
    status: str
    page_count: int
    chunk_count: int
    error: str | None
    created_at: datetime.datetime
    updated_at: datetime.datetime


class DocumentImageRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    page_number: int
    image_index: int
    width: int
    height: int
    ext: str
