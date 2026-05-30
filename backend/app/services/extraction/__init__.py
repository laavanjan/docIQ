"""Document extraction strategies (text / OCR / vision)."""

from app.services.extraction.base import ExtractionResult, Extractor, PageContent
from app.services.extraction.factory import get_extractor

__all__ = ["ExtractionResult", "Extractor", "PageContent", "get_extractor"]
