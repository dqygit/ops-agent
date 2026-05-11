from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Literal


LoopEventType = Literal[
    "loop_delta",
    "loop_plan_updated",
    "loop_approval_required",
    "loop_approval_granted",
    "loop_approval_rejected",
    "loop_execution_started",
    "loop_execution_output",
    "loop_execution_completed",
    "loop_completed",
    "loop_failed",
]


@dataclass(slots=True)
class LoopEvent:
    """Single loop event emitted via the event callback.

    The `payload` dict carries event-specific fields. The `stage` is used by
    `loop_delta` to distinguish planner / executor / review token streams.
    """

    event_type: LoopEventType
    runtime_id: str
    phase: str
    step_id: str | None = None
    step_index: int | None = None
    stage: str | None = None
    message_id: str | None = None
    payload: dict[str, Any] = field(default_factory=dict)

def emit_delta(*, runtime_id: str, message_id: str, stage: str, text: str) -> LoopEvent:
    return LoopEvent(
        event_type="loop_delta",
        runtime_id=runtime_id,
        phase=stage,
        stage=stage,
        message_id=message_id,
        payload={"text": text},
    )


def emit_plan_updated(*, runtime_id: str, plan_payload: dict[str, Any]) -> LoopEvent:
    return LoopEvent(
        event_type="loop_plan_updated",
        runtime_id=runtime_id,
        phase="planning",
        payload={"plan": plan_payload},
    )


def emit_approval_required(
    *,
    runtime_id: str,
    step_id: str,
    step_index: int,
    command: str,
    title: str,
    reason: str,
    risk_level: str,
    working_directory: str | None,
    expected_output: str | None,
) -> LoopEvent:
    return LoopEvent(
        event_type="loop_approval_required",
        runtime_id=runtime_id,
        phase="approving",
        step_id=step_id,
        step_index=step_index,
        payload={
            "command": command,
            "title": title,
            "reason": reason,
            "risk_level": risk_level,
            "working_directory": working_directory,
            "expected_output": expected_output,
        },
    )

def emit_approval_granted(*, runtime_id: str, step_id: str) -> LoopEvent:
    return LoopEvent(
        event_type="loop_approval_granted",
        runtime_id=runtime_id,
        phase="approving",
        step_id=step_id,
    )


def emit_approval_rejected(*, runtime_id: str, step_id: str) -> LoopEvent:
    return LoopEvent(
        event_type="loop_approval_rejected",
        runtime_id=runtime_id,
        phase="approving",
        step_id=step_id,
    )


def emit_execution_started(
    *,
    runtime_id: str,
    step_id: str,
    step_index: int,
    command_id: str,
    terminal_id: str | None,
    command: str,
    title: str,
) -> LoopEvent:
    return LoopEvent(
        event_type="loop_execution_started",
        runtime_id=runtime_id,
        phase="executing",
        step_id=step_id,
        step_index=step_index,
        payload={
            "command_id": command_id,
            "terminal_id": terminal_id,
            "command": command,
            "title": title,
        },
    )


def emit_execution_output(
    *,
    runtime_id: str,
    step_id: str,
    command_id: str,
    terminal_id: str | None,
    text: str,
    stream: str = "stdout",
) -> LoopEvent:
    return LoopEvent(
        event_type="loop_execution_output",
        runtime_id=runtime_id,
        phase="executing",
        step_id=step_id,
        payload={
            "command_id": command_id,
            "terminal_id": terminal_id,
            "stream": stream,
            "text": text,
        },
    )


def emit_execution_completed(
    *,
    runtime_id: str,
    step_id: str,
    step_index: int,
    command_id: str,
    terminal_id: str | None,
    exit_code: int | None,
    completed: bool,
    success: bool,
) -> LoopEvent:
    return LoopEvent(
        event_type="loop_execution_completed",
        runtime_id=runtime_id,
        phase="executing",
        step_id=step_id,
        step_index=step_index,
        payload={
            "command_id": command_id,
            "terminal_id": terminal_id,
            "exit_code": exit_code,
            "completed": completed,
            "success": success,
        },
    )

def emit_completed(*, runtime_id: str, summary: str) -> LoopEvent:
    return LoopEvent(
        event_type="loop_completed",
        runtime_id=runtime_id,
        phase="completed",
        payload={"summary": summary},
    )


def emit_failed(*, runtime_id: str, error: str) -> LoopEvent:
    return LoopEvent(
        event_type="loop_failed",
        runtime_id=runtime_id,
        phase="failed",
        payload={"error": error},
    )
