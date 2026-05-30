"""Shared string constants for model enum-like columns.

Kept as plain ``str`` values (not native PG enums) so adding a new method/status
never requires a database migration.
"""

from __future__ import annotations


class ExtractionMethod:
    TEXT = "text"
    OCR = "ocr"
    VISION = "vision"

    ALL = (TEXT, OCR, VISION)


class DocumentStatus:
    PROCESSING = "processing"
    READY = "ready"
    ERROR = "error"
