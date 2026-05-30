"""Common types for extractors."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Protocol, runtime_checkable


@dataclass
class PageContent:
    page_number: int           # 1-based
    text: str
    meta: dict = field(default_factory=dict)


@dataclass
class ExtractionResult:
    method: str
    pages: list[PageContent]
    meta: dict = field(default_factory=dict)

    @property
    def text(self) -> str:
        return "\n\n".join(p.text for p in self.pages if p.text.strip())

    @property
    def page_count(self) -> int:
        return len(self.pages)

    @property
    def char_count(self) -> int:
        return sum(len(p.text) for p in self.pages)


@runtime_checkable
class Extractor(Protocol):
    method: str

    def extract(self, file_path: str) -> ExtractionResult:
        ...
