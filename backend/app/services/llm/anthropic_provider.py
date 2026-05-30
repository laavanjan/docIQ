"""Anthropic (Claude) provider — the primary LLM."""

from __future__ import annotations

import logging
from collections.abc import Iterator

from app.core.config import settings
from app.services.llm.base import (
    ImageBlock,
    LLMError,
    LLMResponse,
    Message,
    StreamChunk,
    TextBlock,
)

logger = logging.getLogger(__name__)


class AnthropicProvider:
    name = "anthropic"

    def __init__(self, api_key: str | None = None, model: str | None = None) -> None:
        self._api_key = api_key or settings.anthropic_api_key
        self.model = model or settings.anthropic_model
        self._client = None

    def is_available(self) -> bool:
        return bool(self._api_key)

    def _get_client(self):
        if self._client is None:
            import anthropic  # imported lazily so the dep is optional at import time

            self._client = anthropic.Anthropic(api_key=self._api_key)
        return self._client

    def _to_api_messages(self, messages: list[Message]) -> list[dict]:
        out: list[dict] = []
        for msg in messages:
            content: list[dict] = []
            for block in msg.blocks:
                if isinstance(block, TextBlock):
                    content.append({"type": "text", "text": block.text})
                elif isinstance(block, ImageBlock):
                    content.append(
                        {
                            "type": "image",
                            "source": {
                                "type": "base64",
                                "media_type": block.media_type,
                                "data": block.b64(),
                            },
                        }
                    )
            out.append({"role": msg.role, "content": content})
        return out

    def _build_kwargs(
        self, *, system: str, messages: list[Message], max_tokens: int, temperature: float | None
    ) -> dict:
        kwargs: dict = {
            "model": self.model,
            "max_tokens": max_tokens,
            "system": system or None,
            "messages": self._to_api_messages(messages),
        }
        if temperature is not None:
            kwargs["temperature"] = temperature
        return kwargs

    def complete(
        self, *, system: str, messages: list[Message], max_tokens: int, temperature: float | None
    ) -> LLMResponse:
        client = self._get_client()
        try:
            resp = client.messages.create(
                **self._build_kwargs(
                    system=system, messages=messages, max_tokens=max_tokens, temperature=temperature
                )
            )
        except Exception as exc:  # noqa: BLE001 - normalise all SDK errors
            raise LLMError(f"anthropic completion failed: {exc}") from exc

        text = "".join(part.text for part in resp.content if getattr(part, "type", None) == "text")
        return LLMResponse(
            text=text,
            provider=self.name,
            model=self.model,
            input_tokens=resp.usage.input_tokens,
            output_tokens=resp.usage.output_tokens,
        )

    def stream(
        self, *, system: str, messages: list[Message], max_tokens: int, temperature: float | None
    ) -> Iterator[StreamChunk]:
        client = self._get_client()
        try:
            with client.messages.stream(
                **self._build_kwargs(
                    system=system, messages=messages, max_tokens=max_tokens, temperature=temperature
                )
            ) as stream:
                for text in stream.text_stream:
                    yield StreamChunk(type="delta", text=text, provider=self.name, model=self.model)
                final = stream.get_final_message()
                yield StreamChunk(
                    type="done",
                    provider=self.name,
                    model=self.model,
                    input_tokens=final.usage.input_tokens,
                    output_tokens=final.usage.output_tokens,
                )
        except Exception as exc:  # noqa: BLE001
            raise LLMError(f"anthropic stream failed: {exc}") from exc
