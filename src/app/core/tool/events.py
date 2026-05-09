from __future__ import annotations

from typing import Any

from app.core.tool.contracts import ToolEvent


class ToolEventPublisher:
    def __init__(self) -> None:
        self._events: list[ToolEvent] = []

    def publish(self, event: ToolEvent) -> None:
        self._events.append(event)

    def list_events(self) -> list[ToolEvent]:
        return list(self._events)

    def clear(self) -> None:
        self._events.clear()
