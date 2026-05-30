"""Retrieval-augmented generation over a single document.

Embeds the question, retrieves the nearest chunks from pgvector, builds a grounded prompt
with ``[p.N]`` page markers, and streams an answer through the LLM router (Claude ->
OpenAI fallback). Every answer is recorded in ``query_logs`` for auditing/cost tracking.
"""

from __future__ import annotations

import logging
import time
from collections.abc import Iterator
from typing import Any

from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.logging_config import log_event
from app.models.document import Document
from app.models.query_log import QueryLog
from app.services import vectorstore
from app.services.embeddings import get_embedder
from app.services.llm.base import user_text
from app.services.llm.router import get_llm_router

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = (
    "You are a careful document-analysis assistant. Answer the user's question using ONLY the "
    "provided context from their document. If the answer is not contained in the context, say you "
    "could not find it in the document — do not invent facts. When you use information from the "
    "context, cite the page like [p.N]. Be concise and accurate."
)


def _build_context(retrieved: list[vectorstore.RetrievedChunk]) -> str:
    return "\n\n".join(f"[p.{r.page_number}] {r.content}" for r in retrieved)


def _build_messages(question: str, context: str):
    if context:
        prompt = f"Context from the document:\n\n{context}\n\n---\nQuestion: {question}"
    else:
        prompt = (
            f"No relevant context was retrieved from the document.\n\nQuestion: {question}\n\n"
            "If you cannot answer from the document, say so."
        )
    return [user_text(prompt)]


def _persist(
    db: Session,
    *,
    document: Document,
    question: str,
    answer_chars: int,
    provider: str,
    model: str,
    input_tokens: int,
    output_tokens: int,
    latency_ms: int,
) -> None:
    db.add(
        QueryLog(
            owner_id=document.owner_id,
            document_id=document.id,
            question=question,
            answer_chars=answer_chars,
            provider_used=provider or None,
            model=model or None,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            latency_ms=latency_ms,
        )
    )
    db.commit()


def _retrieve(db: Session, document: Document, question: str, top_k: int | None):
    top_k = top_k or settings.retrieval_top_k
    query_embedding = get_embedder().embed_query(question)
    retrieved = vectorstore.search(
        db,
        owner_id=document.owner_id,
        document_id=document.id,
        query_embedding=query_embedding,
        k=top_k,
    )
    sources = [
        {
            "chunk_id": str(r.chunk_id),
            "page_number": r.page_number,
            "score": r.score,
            "preview": r.content[:240],
        }
        for r in retrieved
    ]
    return retrieved, sources


def answer_stream(
    db: Session, *, document: Document, question: str, top_k: int | None = None
) -> Iterator[dict[str, Any]]:
    """Yield SSE-friendly events: one ``sources``, many ``delta``, one ``done``."""
    start = time.perf_counter()
    retrieved, sources = _retrieve(db, document, question, top_k)
    yield {"type": "sources", "sources": sources}

    messages = _build_messages(question, _build_context(retrieved))
    parts: list[str] = []
    provider = model = ""
    input_tokens = output_tokens = 0

    for chunk in get_llm_router().stream(system=SYSTEM_PROMPT, messages=messages):
        if chunk.type == "delta":
            parts.append(chunk.text)
            yield {"type": "delta", "text": chunk.text}
        else:  # done
            provider, model = chunk.provider, chunk.model
            input_tokens, output_tokens = chunk.input_tokens, chunk.output_tokens

    answer = "".join(parts)
    latency_ms = int((time.perf_counter() - start) * 1000)
    _persist(
        db,
        document=document,
        question=question,
        answer_chars=len(answer),
        provider=provider,
        model=model,
        input_tokens=input_tokens,
        output_tokens=output_tokens,
        latency_ms=latency_ms,
    )
    log_event(
        logger,
        "rag.answer",
        provider=provider,
        model=model,
        sources=len(sources),
        input_tokens=input_tokens,
        output_tokens=output_tokens,
        ms=latency_ms,
    )
    yield {
        "type": "done",
        "provider": provider,
        "model": model,
        "input_tokens": input_tokens,
        "output_tokens": output_tokens,
        "latency_ms": latency_ms,
        "answer_chars": len(answer),
    }


def answer(
    db: Session, *, document: Document, question: str, top_k: int | None = None
) -> dict[str, Any]:
    """Non-streaming variant returning the full answer + sources + usage."""
    start = time.perf_counter()
    retrieved, sources = _retrieve(db, document, question, top_k)
    messages = _build_messages(question, _build_context(retrieved))
    response = get_llm_router().complete(system=SYSTEM_PROMPT, messages=messages)
    latency_ms = int((time.perf_counter() - start) * 1000)
    _persist(
        db,
        document=document,
        question=question,
        answer_chars=len(response.text),
        provider=response.provider,
        model=response.model,
        input_tokens=response.input_tokens,
        output_tokens=response.output_tokens,
        latency_ms=latency_ms,
    )
    log_event(
        logger,
        "rag.answer",
        provider=response.provider,
        model=response.model,
        sources=len(sources),
        input_tokens=response.input_tokens,
        output_tokens=response.output_tokens,
        ms=latency_ms,
    )
    return {
        "answer": response.text,
        "provider": response.provider,
        "model": response.model,
        "sources": sources,
        "input_tokens": response.input_tokens,
        "output_tokens": response.output_tokens,
        "latency_ms": latency_ms,
    }
