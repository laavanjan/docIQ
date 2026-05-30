"""Unit tests for the text chunker (no DB / network needed)."""

from __future__ import annotations

from app.services.chunking import Chunker
from app.services.extraction.base import PageContent


def test_long_text_splits_into_multiple_chunks():
    text = "This is a sentence. " * 200  # ~4000 chars
    chunks = Chunker(chunk_size=200, overlap=20).chunk([PageContent(page_number=1, text=text)])
    assert len(chunks) > 1
    # chunks may exceed chunk_size by up to the overlap carry-over, plus a small slack
    assert all(len(c.content) <= 200 + 20 + 2 for c in chunks)
    assert all(c.page_number == 1 for c in chunks)
    # indices are contiguous from 0
    assert [c.chunk_index for c in chunks] == list(range(len(chunks)))


def test_short_text_is_single_chunk():
    chunks = Chunker(chunk_size=1000, overlap=100).chunk(
        [PageContent(page_number=3, text="short content")]
    )
    assert len(chunks) == 1
    assert chunks[0].page_number == 3
    assert chunks[0].content == "short content"


def test_empty_pages_produce_no_chunks():
    chunks = Chunker().chunk([PageContent(page_number=1, text="   \n  ")])
    assert chunks == []


def test_page_numbers_preserved_across_pages():
    pages = [PageContent(page_number=i, text=f"content for page {i}") for i in (1, 2, 3)]
    chunks = Chunker().chunk(pages)
    assert {c.page_number for c in chunks} == {1, 2, 3}
