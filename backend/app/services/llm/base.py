"""Provider-neutral message/response types shared by every LLM backend.

A :class:`Message` carries a list of content blocks (text and/or images) so the same
abstraction handles plain chat *and* multimodal vision extraction. Each concrete provider
translates these blocks into its own wire format.
"""

from __future__ import annotations

import base64
from collections.abc import Iterator, Sequence
from dataclasses import dataclass, field
from typing import Protocol, runtime_checkable


class LLMError(Exception):
    """A provider call failed (network, API error, bad response)."""


class LLMUnavailableError(LLMError):
    """No provider is configured/available to serve the request."""


@dataclass
class TextBlock:
    text: str


@dataclass
class ImageBlock:
    data: bytes
    media_type: str = "image/png"

    def b64(self) -> str:
        return base64.b64encode(self.data).decode("ascii")


ContentBlock = TextBlock | ImageBlock


@dataclass
class Message:
    role: str  # "user" | "assistant"
    blocks: list[ContentBlock] = field(default_factory=list)


@dataclass
class LLMResponse:
    text: str
    provider: str
    model: str
    input_tokens: int = 0
    output_tokens: int = 0


@dataclass
class StreamChunk:
    """One streaming event: a text ``delta`` or a terminal ``done`` carrying usage."""

    type: str  # "delta" | "done"
    text: str = ""
    provider: str = ""
    model: str = ""
    input_tokens: int = 0
    output_tokens: int = 0


# ---- Convenience builders -------------------------------------------------

def user_text(text: str) -> Message:
    return Message(role="user", blocks=[TextBlock(text)])


def user_text_and_images(text: str, images: Sequence[bytes], media_type: str = "image/png") -> Message:
    blocks: list[ContentBlock] = [TextBlock(text)]
    blocks.extend(ImageBlock(data=img, media_type=media_type) for img in images)
    return Message(role="user", blocks=blocks)


@runtime_checkable
class LLMProvider(Protocol):
    """Interface implemented by every concrete provider."""

    name: str
    model: str

    def is_available(self) -> bool:
        """True when the provider has the credentials/config needed to run."""
        ...

    def complete(
        self, *, system: str, messages: list[Message], max_tokens: int, temperature: float
    ) -> LLMResponse:
        ...

    def stream(
        self, *, system: str, messages: list[Message], max_tokens: int, temperature: float
    ) -> Iterator[StreamChunk]:
        ...
