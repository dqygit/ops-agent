from dataclasses import dataclass, field
from typing import Any, Literal

ToolChoiceMode = Literal["auto", "none", "required"]


@dataclass(frozen=True)
class LLMToolDefinition:
    name: str
    description: str
    input_schema: dict[str, Any]


@dataclass(frozen=True)
class LLMToolChoice:
    mode: ToolChoiceMode = "auto"
    name: str | None = None


@dataclass(frozen=True)
class LLMToolCall:
    id: str
    name: str
    arguments: dict[str, Any] = field(default_factory=dict)
    raw_arguments: str | None = None
