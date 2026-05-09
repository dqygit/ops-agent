from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Literal, Protocol

ToolSource = Literal["local", "mcp", "skill"]
ToolErrorCode = Literal["not_found", "invalid_arguments", "forbidden", "timeout", "execution_error"]


@dataclass(frozen=True)
class ToolContext:
    conversation_id: str | None = None
    task_id: str | None = None
    user_id: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class ToolDefinition:
    name: str
    description: str
    input_schema: dict[str, Any]
    source: ToolSource = "local"
    timeout_seconds: int | None = None


@dataclass(frozen=True)
class ToolCall:
    id: str
    name: str
    arguments: dict[str, Any] = field(default_factory=dict)
    raw_arguments: str | None = None


@dataclass(frozen=True)
class ToolError:
    code: ToolErrorCode
    message: str
    details: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class ToolResult:
    ok: bool
    output: Any = None
    error: ToolError | None = None


@dataclass(frozen=True)
class ToolEvent:
    type: Literal["tool_started", "tool_succeeded", "tool_failed"]
    tool_name: str
    tool_call_id: str
    detail: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)


class ToolHandler(Protocol):
    def __call__(self, *, arguments: dict[str, Any], context: ToolContext) -> Any: ...
