from __future__ import annotations

from dataclasses import dataclass, field, replace
from datetime import UTC, datetime
from typing import Any, Literal

from app.shared.schemas import PlanStep


RuntimeStatus = Literal[
    "planning",
    "waiting_approval",
    "executing",
    "waiting_user_input",
    "replan_pending_approval",
    "completed",
    "failed",
]
RuntimeMode = Literal["agent", "plan"]

RuntimeStepStatus = Literal["pending", "running", "completed", "failed"]
RuntimePatch = dict[str, Any]


@dataclass(slots=True)
class RuntimeStepState:
    step_id: str
    title: str
    command: str
    reason: str
    risk_level: str
    working_directory: str | None = None
    expected_output: str | None = None
    status: RuntimeStepStatus = "pending"
    output: str = ""
    exit_code: int | None = None

    @classmethod
    def from_plan_step(cls, *, step_id: str, step: PlanStep, status: RuntimeStepStatus = "pending") -> RuntimeStepState:
        return cls(
            step_id=step_id,
            title=step.title,
            command=step.command,
            reason=step.reason,
            risk_level=step.risk_level,
            working_directory=step.working_directory,
            expected_output=step.expected_output,
            status=status,
        )


@dataclass(slots=True)
class RuntimeSnapshot:
    runtime_id: str
    conversation_id: str
    asset_id: int
    terminal_id: str | None
    status: RuntimeStatus
    mode: RuntimeMode
    plan_version: int
    locked_plan: bool
    cursor: int
    pending_patch: RuntimePatch | None
    steps: list[RuntimeStepState]
    current_step_id: str | None
    pending_approval_step_id: str | None
    last_output_excerpt: str
    summary: str | None
    error_message: str | None
    created_at: datetime
    updated_at: datetime
    last_sequence: int = 0


@dataclass(slots=True)
class ConversationRuntime:
    runtime_id: str
    conversation_id: str
    asset_id: int
    terminal_id: str | None
    status: RuntimeStatus = "planning"
    mode: RuntimeMode = "agent"
    plan_version: int = 1
    locked_plan: bool = False
    cursor: int = 0
    pending_patch: RuntimePatch | None = None
    steps: list[RuntimeStepState] = field(default_factory=list)
    current_step_id: str | None = None
    pending_approval_step_id: str | None = None
    last_output_excerpt: str = ""
    summary: str | None = None
    error_message: str | None = None
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    updated_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    last_sequence: int = 0

    def replace_steps(self, steps: list[RuntimeStepState]) -> None:
        self.steps = steps
        self.touch()

    def update_last_output_excerpt(self, output: str, *, limit: int = 4000) -> None:
        self.last_output_excerpt = output[-limit:]
        self.touch()

    def mark_planning(self) -> None:
        self.status = "planning"
        self.current_step_id = None
        self.pending_approval_step_id = None
        self.error_message = None
        self.touch()

    def mark_waiting_approval(self, step_id: str) -> None:
        self.status = "waiting_approval"
        self.current_step_id = step_id
        self.pending_approval_step_id = step_id
        self.pending_patch = None
        self.error_message = None
        self.touch()

    def mark_executing(self, step_id: str) -> None:
        self.status = "executing"
        self.current_step_id = step_id
        self.pending_approval_step_id = None
        self.pending_patch = None
        self.error_message = None
        self.touch()

    def mark_waiting_user_input(self) -> None:
        self.status = "waiting_user_input"
        self.pending_approval_step_id = None
        self.error_message = None
        self.touch()

    def mark_replan_pending_approval(self, patch: RuntimePatch) -> None:
        self.status = "replan_pending_approval"
        self.pending_patch = dict(patch)
        self.pending_approval_step_id = None
        self.error_message = None
        self.summary = None
        self.touch()

    def mark_completed(self, summary: str) -> None:
        self.status = "completed"
        self.summary = summary
        self.current_step_id = None
        self.pending_approval_step_id = None
        self.pending_patch = None
        self.error_message = None
        self.touch()

    def mark_failed(self, reason: str) -> None:
        self.status = "failed"
        self.current_step_id = None
        self.error_message = reason
        self.pending_approval_step_id = None
        self.pending_patch = None
        self.touch()

    def touch(self) -> None:
        self.updated_at = datetime.now(UTC)

    def to_snapshot(self) -> RuntimeSnapshot:
        return RuntimeSnapshot(
            runtime_id=self.runtime_id,
            conversation_id=self.conversation_id,
            asset_id=self.asset_id,
            terminal_id=self.terminal_id,
            status=self.status,
            mode=self.mode,
            plan_version=self.plan_version,
            locked_plan=self.locked_plan,
            cursor=self.cursor,
            pending_patch=dict(self.pending_patch) if self.pending_patch is not None else None,
            steps=[replace(step) for step in self.steps],
            current_step_id=self.current_step_id,
            pending_approval_step_id=self.pending_approval_step_id,
            last_output_excerpt=self.last_output_excerpt,
            summary=self.summary,
            error_message=self.error_message,
            created_at=self.created_at,
            updated_at=self.updated_at,
            last_sequence=self.last_sequence,
        )
