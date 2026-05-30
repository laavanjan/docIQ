"""Vision extraction: render each page to an image and let an LLM read it.

Handles scanned documents, complex layouts, charts and embedded images. Uses the LLM
router, so it benefits from the Claude -> OpenAI fallback like everything else.
"""

from __future__ import annotations

import io
import logging
import time

from app.core.config import settings
from app.core.logging_config import log_event
from app.services.extraction.base import ExtractionResult, PageContent
from app.services.llm.base import user_text_and_images
from app.services.llm.router import get_llm_router

logger = logging.getLogger(__name__)

VISION_SYSTEM = "You are a precise document OCR and layout-extraction engine."
VISION_PROMPT = (
    "Extract ALL text content from this document page image and return it as clean Markdown. "
    "Preserve reading order and headings. Render any tables as GitHub-flavoured Markdown tables. "
    "Do not add commentary, explanations, or fences — output only the extracted content."
)


class VisionExtractor:
    method = "vision"

    def __init__(self, router=None) -> None:
        self._router = router or get_llm_router()

    def _render(self, file_path: str):
        from pdf2image import convert_from_path

        kwargs: dict = {"dpi": settings.vision_dpi}
        if settings.poppler_path:
            kwargs["poppler_path"] = settings.poppler_path
        return convert_from_path(file_path, **kwargs)

    def extract(self, file_path: str) -> ExtractionResult:
        start = time.perf_counter()
        images = self._render(file_path)
        pages: list[PageContent] = []

        for index, image in enumerate(images):
            buf = io.BytesIO()
            image.save(buf, format="PNG")
            message = user_text_and_images(VISION_PROMPT, [buf.getvalue()])
            response = self._router.complete(
                system=VISION_SYSTEM,
                messages=[message],
            )
            pages.append(
                PageContent(
                    page_number=index + 1,
                    text=response.text,
                    meta={"provider": response.provider, "model": response.model},
                )
            )
            log_event(
                logger,
                "extract.vision.page",
                level=logging.DEBUG,
                page=index + 1,
                provider=response.provider,
                chars=len(response.text),
            )

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
