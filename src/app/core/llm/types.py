from dataclasses import dataclass, field
from typing import Any, Literal

from app.core.tool.schema import LLMToolCall, LLMToolChoice, LLMToolDefinition

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
    thinking: str = ""


@dataclass(frozen=True)
class LLMCompletionChunk:
    delta: str = ""
    tool_calls: list[LLMToolCall] = field(default_factory=list)
    finish_reason: str | None = None
    tool_arguments_delta: str = ""
    thinking_delta: str = ""
