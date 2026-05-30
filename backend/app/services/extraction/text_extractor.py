"""Text extraction for digital (selectable-text) PDFs via PyMuPDF."""

from __future__ import annotations

import logging
import time

from app.core.logging_config import log_event
from app.services.extraction.base import ExtractionResult, PageContent

logger = logging.getLogger(__name__)


class TextExtractor:
    method = "text"

    def extract(self, file_path: str) -> ExtractionResult:
        import fitz  # PyMuPDF; imported as fitz

        start = time.perf_counter()
        pages: list[PageContent] = []
        with fitz.open(file_path) as doc:
            for index, page in enumerate(doc):
                pages.append(PageContent(page_number=index + 1, text=page.get_text("text")))

        result = ExtractionResult(method=self.method, pages=pages)
        log_event(
            logger,
            "extract.done",
            method=self.method,
            pages=result.page_count,
            chars=result.char_count,
            ms=round((time.perf_counter() - start) * 1000, 1),
        )
        return result
