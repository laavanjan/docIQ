"""Resolve an extraction-method string to a concrete extractor."""

from __future__ import annotations

from app.models.constants import ExtractionMethod
from app.services.extraction.base import Extractor
from app.services.extraction.ocr_extractor import OCRExtractor
from app.services.extraction.text_extractor import TextExtractor
from app.services.extraction.vision_extractor import VisionExtractor


def get_extractor(method: str) -> Extractor:
    if method == ExtractionMethod.TEXT:
        return TextExtractor()
    if method == ExtractionMethod.OCR:
        return OCRExtractor()
    if method == ExtractionMethod.VISION:
        return VisionExtractor()
    raise ValueError(
        f"Unknown extraction method: {method!r}. Expected one of {ExtractionMethod.ALL}."
    )
