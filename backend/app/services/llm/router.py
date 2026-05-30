"""LLM router: try the primary provider, transparently fall back to the secondary.

Fallback rules:
* Only *available* providers (those with an API key) are considered.
* For ``complete()``, any failure of the primary triggers the fallback.
* For ``stream()``, fallback only happens if the primary fails **before** emitting any
  output — once bytes have been streamed to the client we cannot safely switch mid-answer.
"""

from __future__ import annotations

import logging
from collections.abc import Iterator
from functools import lru_cache

from app.core.config import settings
from app.core.logging_config import log_event
from app.services.llm.anthropic_provider import AnthropicProvider
from app.services.llm.base import (
    LLMProvider,
    LLMResponse,
    LLMUnavailableError,
    Message,
    StreamChunk,
)
from app.services.llm.openai_provider import OpenAIProvider

logger = logging.getLogger(__name__)


class LLMRouter:
    def __init__(self) -> None:
        self._providers: dict[str, LLMProvider] = {
            "anthropic": AnthropicProvider(),
            "openai": OpenAIProvider(),
        }

    def _ordered(self) -> list[LLMProvider]:
        primary = settings.llm_primary
        secondary = "openai" if primary == "anthropic" else "anthropic"
        order = [primary]
        if settings.llm_fallback_enabled:
            order.append(secondary)
        available = [self._providers[name] for name in order if self._providers[name].is_available()]
        return available

    def complete(
        self,
        *,
        system: str,
        messages: list[Message],
        max_tokens: int | None = None,
        temperature: float | None = None,
    ) -> LLMResponse:
        providers = self._ordered()
        if not providers:
            raise LLMUnavailableError(
                "No LLM provider is configured. Set ANTHROPIC_API_KEY and/or OPENAI_API_KEY."
            )
        max_tokens = max_tokens or settings.llm_max_tokens
        temperature = settings.llm_temperature if temperature is None else temperature

        last_err: Exception | None = None
        for index, provider in enumerate(providers):
            try:
                resp = provider.complete(
                    system=system, messages=messages, max_tokens=max_tokens, temperature=temperature
                )
                log_event(
                    logger,
                    "llm.complete",
                    provider=resp.provider,
                    model=resp.model,
                    fallback=index > 0,
                    input_tokens=resp.input_tokens,
                    output_tokens=resp.output_tokens,
                )
                return resp
            except Exception as exc:  # noqa: BLE001
                last_err = exc
                log_event(
                    logger,
                    "llm.provider_failed",
                    level=logging.WARNING,
                    provider=provider.name,
                    will_fallback=index + 1 < len(providers),
                    error=str(exc),
                )
        raise LLMUnavailableError(f"All LLM providers failed; last error: {last_err}")

    def stream(
        self,
        *,
        system: str,
        messages: list[Message],
        max_tokens: int | None = None,
        temperature: float | None = None,
    ) -> Iterator[StreamChunk]:
        providers = self._ordered()
        if not providers:
            raise LLMUnavailableError(
                "No LLM provider is configured. Set ANTHROPIC_API_KEY and/or OPENAI_API_KEY."
            )
        max_tokens = max_tokens or settings.llm_max_tokens
        temperature = settings.llm_temperature if temperature is None else temperature

        last_err: Exception | None = None
        for index, provider in enumerate(providers):
            started = False
            try:
                for chunk in provider.stream(
                    system=system, messages=messages, max_tokens=max_tokens, temperature=temperature
                ):
                    started = True
                    yield chunk
                log_event(logger, "llm.stream", provider=provider.name, fallback=index > 0)
                return
            except Exception as exc:  # noqa: BLE001
                last_err = exc
                log_event(
                    logger,
                    "llm.provider_failed",
                    level=logging.WARNING,
                    provider=provider.name,
                    streamed_partial=started,
                    error=str(exc),
                )
                if started:
                    # Output already sent downstream; cannot switch providers now.
                    raise
        raise LLMUnavailableError(f"All LLM providers failed; last error: {last_err}")


@lru_cache
def get_llm_router() -> LLMRouter:
    return LLMRouter()
