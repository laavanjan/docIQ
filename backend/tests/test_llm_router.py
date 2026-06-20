"""Unit tests for the LLM router's fallback behaviour (providers faked)."""

from __future__ import annotations

from collections.abc import Iterator

import pytest

from app.core.config import settings
from app.services.llm.base import LLMError, LLMResponse, StreamChunk, user_text
from app.services.llm.router import LLMRouter


class FakeProvider:
    def __init__(self, name: str, *, available: bool = True, fail: bool = False) -> None:
        self.name = name
        self.model = f"{name}-model"
        self._available = available
        self._fail = fail

    def is_available(self) -> bool:
        return self._available

    def complete(self, **_) -> LLMResponse:
        if self._fail:
            raise LLMError(f"{self.name} boom")
        return LLMResponse(
            text=f"hi from {self.name}",
            provider=self.name,
            model=self.model,
            input_tokens=1,
            output_tokens=2,
        )

    def stream(self, **_) -> Iterator[StreamChunk]:
        if self._fail:
            raise LLMError(f"{self.name} boom")
        yield StreamChunk(type="delta", text="hi", provider=self.name, model=self.model)
        yield StreamChunk(type="done", provider=self.name, model=self.model)


def _router(primary: FakeProvider, fallback: FakeProvider, monkeypatch) -> LLMRouter:
    monkeypatch.setattr(settings, "llm_primary", "anthropic")
    monkeypatch.setattr(settings, "llm_fallback_enabled", True)
    router = LLMRouter()
    router._providers = {"anthropic": primary, "openai": fallback}
    return router


def test_primary_used_when_healthy(monkeypatch):
    router = _router(FakeProvider("anthropic"), FakeProvider("openai"), monkeypatch)
    resp = router.complete(system="", messages=[user_text("q")])
    assert resp.provider == "anthropic"


def test_falls_back_when_primary_fails(monkeypatch):
    router = _router(FakeProvider("anthropic", fail=True), FakeProvider("openai"), monkeypatch)
    resp = router.complete(system="", messages=[user_text("q")])
    assert resp.provider == "openai"


def test_skips_unavailable_primary(monkeypatch):
    router = _router(
        FakeProvider("anthropic", available=False), FakeProvider("openai"), monkeypatch
    )
    resp = router.complete(system="", messages=[user_text("q")])
    assert resp.provider == "openai"


def test_raises_when_no_provider_available(monkeypatch):
    router = _router(
        FakeProvider("anthropic", available=False),
        FakeProvider("openai", available=False),
        monkeypatch,
    )
    with pytest.raises(LLMError):
        router.complete(system="", messages=[user_text("q")])


def test_stream_falls_back_before_first_token(monkeypatch):
    router = _router(FakeProvider("anthropic", fail=True), FakeProvider("openai"), monkeypatch)
    chunks = list(router.stream(system="", messages=[user_text("q")]))
    assert chunks[-1].type == "done"
    assert chunks[-1].provider == "openai"
