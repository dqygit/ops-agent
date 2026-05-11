from collections.abc import Iterator
from typing import Any, Protocol, runtime_checkable

from app.core.llm.types import (
    LLMCompletionChunk,
    LLMCompletionRequest,
    LLMCompletionResponse,
    LLMMessage,
    LLMMessageRole,
)
from app.shared.schemas import ModelConfig


@runtime_checkable
class SupportsSummarize(Protocol):
    def stream_summarize(
        self,
        *,
        config: ModelConfig,
        user_input: str,
        command_outputs: list[str],
        recent_messages: list[dict[str, Any]] | None = None,
    ) -> Iterator[str]: ...


@runtime_checkable
class SupportsCompletion(Protocol):
    def stream_complete(
        self,
        *,
        config: ModelConfig,
        request: LLMCompletionRequest,
    ) -> Iterator[LLMCompletionChunk]: ...

    def complete(
        self,
        *,
        config: ModelConfig,
        request: LLMCompletionRequest,
    ) -> LLMCompletionResponse: ...
