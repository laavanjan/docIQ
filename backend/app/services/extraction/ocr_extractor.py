"""OCR extraction: poppler render -> YOLO layout regions -> Tesseract per region.

If ``YOLO_ENABLED`` is false (or the model finds no regions on a page) this falls back to
plain full-page Tesseract OCR.
"""

from __future__ import annotations

import logging
import time

from app.core.config import settings
from app.core.logging_config import log_event
from app.services.extraction.base import ExtractionResult, PageContent
from app.services.extraction.layout_detector import get_layout_detector

logger = logging.getLogger(__name__)


class OCRExtractor:
    method = "ocr"

    def __init__(self) -> None:
        self._layout = get_layout_detector() if settings.yolo_enabled else None
        if settings.tesseract_cmd:
            import pytesseract

            pytesseract.pytesseract.tesseract_cmd = settings.tesseract_cmd

    def _render(self, file_path: str):
        from pdf2image import convert_from_path

        kwargs: dict = {"dpi": settings.ocr_dpi}
        if settings.poppler_path:
            kwargs["poppler_path"] = settings.poppler_path
        return convert_from_path(file_path, **kwargs)

    def _ocr_full(self, image) -> str:
        import pytesseract

        return pytesseract.image_to_string(image)

    def _ocr_regions(self, image, regions) -> str:
        import pytesseract

        parts: list[str] = []
        for region in regions:
            x0, y0, x1, y1 = (int(v) for v in region.bbox)
            if x1 <= x0 or y1 <= y0:
                continue
            crop = image.crop((x0, y0, x1, y1))
            text = pytesseract.image_to_string(crop).strip()
            if text:
                parts.append(text)
        return "\n".join(parts)

    def extract(self, file_path: str) -> ExtractionResult:
        start = time.perf_counter()
        images = self._render(file_path)
        pages: list[PageContent] = []
        total_regions = 0

        for index, image in enumerate(images):
            region_count = 0
            if self._layout is not None:
                regions = self._layout.detect(image)
                region_count = len(regions)
                text = self._ocr_regions(image, regions) if regions else self._ocr_full(image)
            else:
                text = self._ocr_full(image)
            total_regions += region_count
            pages.append(
                PageContent(
                    page_number=index + 1,
                    text=text,
                    meta={"yolo_regions": region_count},
                )
            )
            log_event(
                logger,
                "extract.ocr.page",
                level=logging.DEBUG,
                page=index + 1,
                yolo_regions=region_count,
                chars=len(text),
            )

        result = ExtractionResult(
            method=self.method,
            pages=pages,
            meta={"yolo_enabled": self._layout is not None, "total_regions": total_regions},
        )
        log_event(
            logger,
            "extract.done",
            method=self.method,
            pages=result.page_count,
            chars=result.char_count,
            yolo_regions=total_regions,
            ms=round((time.perf_counter() - start) * 1000, 1),
        )
        return result
