"""Split extracted pages into overlapping chunks for embedding.

Chunks are produced per page so every chunk carries a definite ``page_number`` for
citations. A lightweight recursive packer keeps chunks under ``CHUNK_SIZE`` characters with
``CHUNK_OVERLAP`` carry-over, breaking on paragraphs then words — no external dependency.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass

from app.core.config import settings
from app.core.logging_config import log_event
from app.services.extraction.base import PageContent

logger = logging.getLogger(__name__)


@dataclass
class ChunkData:
    chunk_index: int
    page_number: int
    content: str

    @property
    def approx_tokens(self) -> int:
        # Rough heuristic: ~4 characters per token. Good enough for logging/budgeting.
        return max(1, len(self.content) // 4)


class Chunker:
    def __init__(self, chunk_size: int | None = None, overlap: int | None = None) -> None:
        self.chunk_size = chunk_size or settings.chunk_size
        self.overlap = overlap or settings.chunk_overlap

    def _hard_split(self, text: str) -> list[str]:
        """Split an over-long paragraph on word boundaries."""
        out: list[str] = []
        current = ""
        for word in text.split():
            if current and len(current) + 1 + len(word) > self.chunk_size:
                out.append(current)
                current = word
            else:
                current = f"{current} {word}".strip()
        if current:
            out.append(current)
        return out

    def _atomize(self, text: str) -> list[str]:
        units: list[str] = []
        for para in text.split("\n\n"):
            para = para.strip()
            if not para:
                continue
            if len(para) <= self.chunk_size:
                units.append(para)
            else:
                units.extend(self._hard_split(para))
        return units

    def _split_text(self, text: str) -> list[str]:
        text = text.strip()
        if not text:
            return []
        if len(text) <= self.chunk_size:
            return [text]

        chunks: list[str] = []
        current = ""
        for unit in self._atomize(text):
            if not current:
                current = unit
            elif len(current) + 1 + len(unit) <= self.chunk_size:
                current = f"{current}\n{unit}"
            else:
                chunks.append(current)
                tail = current[-self.overlap :] if self.overlap else ""
                current = f"{tail}\n{unit}".strip() if tail else unit
        if current:
            chunks.append(current)
        return chunks

    def chunk(self, pages: list[PageContent]) -> list[ChunkData]:
        chunks: list[ChunkData] = []
        index = 0
        for page in pages:
            for piece in self._split_text(page.text):
                chunks.append(
                    ChunkData(chunk_index=index, page_number=page.page_number, content=piece)
                )
                index += 1
        log_event(
            logger,
            "chunk.done",
            pages=len(pages),
            chunks=len(chunks),
            size=self.chunk_size,
            overlap=self.overlap,
        )
        return chunks
