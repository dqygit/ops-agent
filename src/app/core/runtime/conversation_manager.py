from __future__ import annotations

import logging
import uuid
from collections import deque

from .conversation import ConversationRuntime, RuntimeSnapshot
from .events import RuntimeEvent, build_runtime_event

logger = logging.getLogger(__name__)


class ConversationRuntimeManager:
    def __init__(self) -> None:
        self._runtimes_by_conversation: dict[str, dict[str, ConversationRuntime]] = {}
        self._runtime_index: dict[str, ConversationRuntime] = {}
        self._event_buffers: dict[str, deque[RuntimeEvent]] = {}
        self._sequences: dict[str, int] = {}
        self._terminal_execution_slots: dict[str, str] = {}

    def create_runtime(self, *, conversation_id: str, asset_id: int, terminal_id: str | None = None) -> ConversationRuntime:
        runtime_id = str(uuid.uuid4())
        runtime = ConversationRuntime(
            runtime_id=runtime_id,
            conversation_id=conversation_id,
            asset_id=asset_id,
            terminal_id=terminal_id,
        )
        self._runtimes_by_conversation.setdefault(conversation_id, {})[runtime_id] = runtime
        self._runtime_index[runtime_id] = runtime
        self._event_buffers[runtime_id] = deque(maxlen=1000)
        self._sequences[runtime_id] = 0
        logger.warning("runtime_manager.create_runtime conversation_id=%s runtime_id=%s asset_id=%s terminal_id=%s", conversation_id, runtime_id, asset_id, terminal_id)
        return runtime

    def get_runtime(self, runtime_id: str) -> ConversationRuntime | None:
        return self._runtime_index.get(runtime_id)

    def list_runtimes(self, conversation_id: str) -> list[ConversationRuntime]:
        runtimes = self._runtimes_by_conversation.get(conversation_id, {})
        return list(runtimes.values())

    def get_snapshot(self, runtime_id: str) -> RuntimeSnapshot:
        runtime = self._runtime_index.get(runtime_id)
        if runtime is None:
            raise ValueError("runtime not found")
        runtime.last_sequence = self._sequences.get(runtime_id, 0)
        return runtime.to_snapshot()

    def append_event(self, runtime_id: str, event_type: str, **payload: object) -> RuntimeEvent:
        runtime = self._runtime_index.get(runtime_id)
        if runtime is None:
            raise ValueError("runtime not found")
        sequence = self._sequences.get(runtime_id, 0) + 1
        self._sequences[runtime_id] = sequence
        runtime.last_sequence = sequence
        runtime.touch()
        event = build_runtime_event(
            event_type,  # type: ignore[arg-type]
            conversation_id=runtime.conversation_id,
            runtime_id=runtime.runtime_id,
            sequence=sequence,
            **payload,
        )
        self._event_buffers.setdefault(runtime_id, deque(maxlen=1000)).append(event)
        return event

    def events_since(self, runtime_id: str, sequence: int) -> tuple[int, list[RuntimeEvent]]:
        runtime = self._runtime_index.get(runtime_id)
        if runtime is None:
            raise ValueError("runtime not found")
        events = self._event_buffers.get(runtime_id, deque())
        payloads = [event for event in events if event["sequence"] > sequence]
        return self._sequences.get(runtime_id, sequence), payloads

    def acquire_terminal_execution_slot(self, runtime_id: str, terminal_id: str) -> bool:
        holder = self._terminal_execution_slots.get(terminal_id)
        if holder is not None and holder != runtime_id:
            return False
        self._terminal_execution_slots[terminal_id] = runtime_id
        return True

    def release_terminal_execution_slot(self, runtime_id: str, terminal_id: str) -> None:
        holder = self._terminal_execution_slots.get(terminal_id)
        if holder == runtime_id:
            self._terminal_execution_slots.pop(terminal_id, None)
