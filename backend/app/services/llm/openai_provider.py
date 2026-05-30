"""OpenAI provider — automatic fallback when Claude is unavailable/failing."""

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


class OpenAIProvider:
    name = "openai"

    def __init__(self, api_key: str | None = None, model: str | None = None) -> None:
        self._api_key = api_key or settings.openai_api_key
        self.model = model or settings.openai_model
        self._client = None

    def is_available(self) -> bool:
        return bool(self._api_key)

    def _get_client(self):
        if self._client is None:
            from openai import OpenAI  # lazy import

            self._client = OpenAI(api_key=self._api_key)
        return self._client

    def _to_api_messages(self, system: str, messages: list[Message]) -> list[dict]:
        out: list[dict] = []
        if system:
            out.append({"role": "system", "content": system})
        for msg in messages:
            content: list[dict] = []
            for block in msg.blocks:
                if isinstance(block, TextBlock):
                    content.append({"type": "text", "text": block.text})
                elif isinstance(block, ImageBlock):
                    data_url = f"data:{block.media_type};base64,{block.b64()}"
                    content.append({"type": "image_url", "image_url": {"url": data_url}})
            out.append({"role": msg.role, "content": content})
        return out

    def _build_kwargs(
        self,
        *,
        system: str,
        messages: list[Message],
        max_tokens: int,
        temperature: float | None,
        stream: bool,
    ) -> dict:
        # Newer OpenAI models require `max_completion_tokens` (and reject the legacy
        # `max_tokens`); it is also accepted by current models like gpt-4o.
        kwargs: dict = {
            "model": self.model,
            "max_completion_tokens": max_tokens,
            "messages": self._to_api_messages(system, messages),
        }
        if temperature is not None:
            kwargs["temperature"] = temperature
        if stream:
            kwargs["stream"] = True
            kwargs["stream_options"] = {"include_usage": True}
        return kwargs

    def complete(
        self, *, system: str, messages: list[Message], max_tokens: int, temperature: float | None
    ) -> LLMResponse:
        client = self._get_client()
        try:
            resp = client.chat.completions.create(
                **self._build_kwargs(
                    system=system,
                    messages=messages,
                    max_tokens=max_tokens,
                    temperature=temperature,
                    stream=False,
                )
            )
        except Exception as exc:  # noqa: BLE001
            raise LLMError(f"openai completion failed: {exc}") from exc

        usage = resp.usage
        return LLMResponse(
            text=resp.choices[0].message.content or "",
            provider=self.name,
            model=self.model,
            input_tokens=getattr(usage, "prompt_tokens", 0) if usage else 0,
            output_tokens=getattr(usage, "completion_tokens", 0) if usage else 0,
        )

    def stream(
        self, *, system: str, messages: list[Message], max_tokens: int, temperature: float | None
    ) -> Iterator[StreamChunk]:
        client = self._get_client()
        try:
            stream = client.chat.completions.create(
                **self._build_kwargs(
                    system=system,
                    messages=messages,
                    max_tokens=max_tokens,
                    temperature=temperature,
                    stream=True,
                )
            )
            in_tok = out_tok = 0
            for chunk in stream:
                if chunk.usage:  # final usage-only chunk
                    in_tok = chunk.usage.prompt_tokens
                    out_tok = chunk.usage.completion_tokens
                if chunk.choices and chunk.choices[0].delta.content:
                    yield StreamChunk(
                        type="delta",
                        text=chunk.choices[0].delta.content,
                        provider=self.name,
                        model=self.model,
                    )
            yield StreamChunk(
                type="done",
                provider=self.name,
                model=self.model,
                input_tokens=in_tok,
                output_tokens=out_tok,
            )
        except Exception as exc:  # noqa: BLE001
            raise LLMError(f"openai stream failed: {exc}") from exc
