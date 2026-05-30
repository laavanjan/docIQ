"""Query (RAG) request/response schemas."""

from __future__ import annotations

from pydantic import BaseModel, Field


class QueryRequest(BaseModel):
    question: str = Field(min_length=1, max_length=4000)
    top_k: int | None = Field(default=None, ge=1, le=20)


class Source(BaseModel):
    chunk_id: str
    page_number: int
    score: float
    preview: str


class QueryResponse(BaseModel):
    answer: str
    provider: str
    model: str
    sources: list[Source]
    input_tokens: int
    output_tokens: int
    latency_ms: int
