from collections.abc import Iterator
from dataclasses import dataclass, field
from typing import Any, Literal, Protocol, runtime_checkable

from app.core.tool import LLMToolCall, LLMToolChoice, LLMToolDefinition
from app.shared.schemas import ModelConfig

LLMMessageRole = Literal["system", "user", "assistant", "tool"]


@dataclass(frozen=True)
class LLMMessage:
    role: LLMMessageRole
    content: str
    tool_call_id: str | None = None
    name: str | None = None
    tool_calls: list[LLMToolCall] = field(default_factory=list)


@dataclass(frozen=True)
class LLMCompletionRequest:
    messages: list[LLMMessage]
    tools: list[LLMToolDefinition] = field(default_factory=list)
    tool_choice: LLMToolChoice | None = None
    temperature: float | None = None
    max_tokens: int | None = None
    json_mode: bool = False


@dataclass(frozen=True)
class LLMCompletionResponse:
    text: str = ""
    tool_calls: list[LLMToolCall] = field(default_factory=list)
    finish_reason: str | None = None


@dataclass(frozen=True)
class LLMCompletionChunk:
    delta: str = ""
    tool_calls: list[LLMToolCall] = field(default_factory=list)
    finish_reason: str | None = None
    tool_arguments_delta: str = ""


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
