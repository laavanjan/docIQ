"""pgvector-backed storage and similarity search over the ``chunks`` table."""

from __future__ import annotations

import logging
import time
import uuid
from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.logging_config import log_event
from app.models.chunk import Chunk
from app.services.chunking import ChunkData

logger = logging.getLogger(__name__)


@dataclass
class RetrievedChunk:
    chunk_id: uuid.UUID
    page_number: int
    content: str
    distance: float

    @property
    def score(self) -> float:
        # Cosine distance in [0, 2] -> similarity in [-1, 1]; clamp for display.
        return round(max(0.0, 1.0 - self.distance), 4)


def add_chunks(
    db: Session,
    *,
    document_id: uuid.UUID,
    owner_id: uuid.UUID,
    chunks: list[ChunkData],
    embeddings: list[list[float]],
) -> int:
    """Persist chunks + embeddings. Returns the number of rows inserted."""
    if len(chunks) != len(embeddings):
        raise ValueError("chunks and embeddings length mismatch")

    rows = [
        Chunk(
            document_id=document_id,
            owner_id=owner_id,
            chunk_index=chunk.chunk_index,
            page_number=chunk.page_number,
            content=chunk.content,
            token_count=chunk.approx_tokens,
            embedding=embedding,
            meta={},
        )
        for chunk, embedding in zip(chunks, embeddings, strict=True)
    ]
    db.add_all(rows)
    db.flush()
    log_event(logger, "vectorstore.upsert", rows=len(rows), document_id=str(document_id))
    return len(rows)


def search(
    db: Session,
    *,
    owner_id: uuid.UUID,
    document_id: uuid.UUID,
    query_embedding: list[float],
    k: int,
) -> list[RetrievedChunk]:
    """Top-k nearest chunks for a document by cosine distance."""
    start = time.perf_counter()
    distance = Chunk.embedding.cosine_distance(query_embedding).label("distance")
    stmt = (
        select(Chunk, distance)
        .where(Chunk.owner_id == owner_id, Chunk.document_id == document_id)
        .order_by(distance)
        .limit(k)
    )
    results = [
        RetrievedChunk(
            chunk_id=chunk.id,
            page_number=chunk.page_number,
            content=chunk.content,
            distance=float(dist),
        )
        for chunk, dist in db.execute(stmt).all()
    ]
    log_event(
        logger,
        "vectorstore.search",
        document_id=str(document_id),
        k=k,
        hits=len(results),
        top_score=results[0].score if results else None,
        ms=round((time.perf_counter() - start) * 1000, 1),
    )
    return results
