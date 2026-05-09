from __future__ import annotations

from dataclasses import dataclass


@dataclass(slots=True)
class ApproveRuntimeStepAction:
    conversation_id: str
    runtime_id: str
    step_id: str


@dataclass(slots=True)
class RejectRuntimeStepAction:
    conversation_id: str
    runtime_id: str
    step_id: str


@dataclass(slots=True)
class RuntimeUserInputAction:
    conversation_id: str
    message: str
    runtime_id: str | None = None


@dataclass(slots=True)
class CancelRuntimeAction:
    conversation_id: str
    runtime_id: str
