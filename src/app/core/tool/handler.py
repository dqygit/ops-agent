from __future__ import annotations

from collections.abc import Iterator
from dataclasses import dataclass, field
from typing import Any, Protocol

from app.core.loop.loop_events import LoopEvent
from app.core.loop.loop_state import LoopState
from app.core.loop.message_manager import MessageManager
from app.core.tool.schema import LLMToolDefinition


@dataclass(frozen=True)
class ToolDisplayMetadata:
    description: str = ""
    display_text: str = ""
    extra: dict[str, Any] = field(default_factory=dict)


class ToolHandler(Protocol):
    """Protocol for tools that can be executed by the AgentLoop."""

    @property
    def definition(self) -> LLMToolDefinition:
        """The tool's schema definition passed to the LLM."""
        ...

    def needs_approval(self, args: dict[str, Any]) -> tuple[str, str]:
        """
        Check if the tool call requires user approval.
        Returns a tuple of (action, reason), where action is 'allow', 'ask', or 'deny'.
        """
        ...

    def display_metadata(self, args: dict[str, Any]) -> ToolDisplayMetadata:
        """Build display metadata for approval/tool use payloads."""
        ...

    def execute(self, *, state: LoopState, step_id: str, args: dict[str, Any], manager: MessageManager | None = None) -> Iterator[LoopEvent]:
        """
        Executes the tool and yields events to stream to the client.
        Must return a tuple of (success: bool, output: str) when complete.
        """
        ...
