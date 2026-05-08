from __future__ import annotations

import uuid
from collections.abc import Iterator
from dataclasses import dataclass
from time import sleep, time
from types import SimpleNamespace
from typing import Any

from sqlmodel import Session

from app.db.repositories.models import get_default_model_config
from app.db.repositories.tasks import create_approval, list_task_steps_by_task_id, update_task_step
from app.services.asset_service import get_asset_record
from app.services.executor_service import ExecutorService
from app.services.model_service import ModelService
from app.services.planner_service import PlannerService
from app.services.terminal_service import TerminalService
from app.shared.schemas import PlanStep

from .task_state_machine import TaskStateMachine


COMMAND_SENTINEL = "__OPS_AGENT_COMMAND_DONE__"
COMMAND_WRAP_START = "__OPS_AGENT_WRAP_START__"
COMMAND_WRAP_END = "__OPS_AGENT_WRAP_END__"


@dataclass
class TaskUseCaseDependencies:
    planner: PlannerService
    executor: ExecutorService
    model_service: ModelService
    terminal_service: TerminalService
    state_machine: TaskStateMachine


@dataclass
class CommandRunResult:
    output: str
    exit_code: int | None
    completed: bool
    command_id: str | None = None


class BaseTaskUseCase:
    def __init__(self, deps: TaskUseCaseDependencies):
        self._deps = deps

    def _resolve_asset(self, session: Session, asset_id: int):
        asset = get_asset_record(session, asset_id)
        if asset is None and asset_id == 0:
            asset = SimpleNamespace(
                id=0,
                name="本地终端",
                asset_type="local_terminal",
                host="localhost",
                username="",
            )
        return asset

    def _resolve_model_config(self, session: Session, model_name: str | None):
        model_service = self._deps.model_service
        default_record = get_default_model_config(session)
        default_config = model_service.from_record(default_record) if default_record is not None else model_service.load_settings()
        if model_name and model_name != default_config.model_name:
            default_config = default_config.model_copy(update={"model_name": model_name})
        return default_config

    def _build_plan_event(self, task_id: int, steps: list[PlanStep], *, current_index: int, version: int, plan_id: str | None = None) -> dict:
        rendered_steps = []
        for index, step in enumerate(steps):
            status = "completed" if index < current_index else "running" if index == current_index else "pending"
            rendered_steps.append(
                {
                    "id": f"task-{task_id}-step-{index + 1}",
                    "title": step.title,
                    "summary": step.reason,
                    "status": status,
                }
            )
        return {
            "id": f"plan-{task_id}-v{version}",
            "kind": "plan",
            "planId": plan_id or f"task-{task_id}",
            "title": "Task Plan",
            "loading": False,
            "version": version,
            "isLatest": True,
            "updated": version > 1,
            "steps": rendered_steps,
        }

    def _build_delta_event(self, *, message_id: str, text: str, stage: str) -> dict:
        return {
            "id": f"delta-{message_id}-{uuid.uuid4()}",
            "kind": "delta",
            "messageId": message_id,
            "stage": stage,
            "text": text,
        }

    def _infer_os_type(self, shell_type: str) -> str:
        if shell_type in {"powershell", "cmd"}:
            return "Windows"
        if shell_type in {"posix", "network", "serial"}:
            return "Darwin/Linux"
        return "unknown"

    def _parse_command_result(self, output: str) -> CommandRunResult:
        sentinel_prefix = f"{COMMAND_SENTINEL}:"
        marker_index = output.rfind(sentinel_prefix)
        if marker_index < 0:
            return CommandRunResult(output=output.strip(), exit_code=None, completed=False)
        visible_output = output[:marker_index].rstrip()
        remainder = output[marker_index + len(sentinel_prefix):].strip()
        exit_code: int | None
        try:
            exit_code = int(remainder.splitlines()[0]) if remainder else None
        except ValueError:
            exit_code = None
        return CommandRunResult(output=visible_output, exit_code=exit_code, completed=True)

    def _collect_command_output(
        self,
        *,
        terminal_id: str,
        command_id: str,
        after_cursor: int,
        max_wait_seconds: float = 20.0,
        poll_interval_seconds: float = 0.1,
    ) -> CommandRunResult:
        deadline = time() + max_wait_seconds
        output_parts: list[str] = []
        cursor = after_cursor
        while time() < deadline:
            cursor, events = self._deps.terminal_service.read_command_events_since(terminal_id, cursor)
            if events:
                for event in events:
                    if event.get("commandId") != command_id:
                        continue
                    if event.get("kind") == "command_chunk":
                        output_parts.append(str(event.get("text", "")))
                        continue
                    if event.get("kind") == "command_end":
                        return CommandRunResult(
                            output="".join(output_parts).strip(),
                            exit_code=event.get("exitCode"),
                            completed=True,
                            command_id=command_id,
                        )
            sleep(poll_interval_seconds)
        return CommandRunResult(output="".join(output_parts).strip(), exit_code=None, completed=False, command_id=command_id)

    def _load_plan_steps(self, session: Session, task_id: int, override_step: PlanStep | None = None, override_step_id: int | None = None) -> list[PlanStep]:
        rows = list_task_steps_by_task_id(session, task_id)
        steps: list[PlanStep] = []
        for row in rows:
            if override_step is not None and override_step_id == row.id:
                steps.append(override_step)
                continue
            steps.append(
                PlanStep(
                    title=row.title,
                    command=row.command,
                    reason=row.reason,
                    risk_level=row.risk_level,
                    working_directory=row.working_directory,
                    expected_output=row.expected_output,
                )
            )
        return steps

    def _prepare_step_approval(
        self,
        *,
        session: Session,
        task_id: int,
        run_id: str,
        asset_id: int,
        terminal_id: str | None,
        step_row: Any,
        step_index: int,
        asset_summary: str,
        recent_output: str,
        model_config: Any,
        shell_type: str,
        os_type: str,
    ) -> Iterator[dict]:
        step_id = step_row.id
        if step_id is None:
            raise ValueError("step id is required")
        executor_message_id = f"message-executor-{run_id}-{step_id}"
        refined_step = None
        for chunk in self._deps.executor.stream_refine_step(
            config=model_config,
            step=PlanStep(
                title=step_row.title,
                command=step_row.command,
                reason=step_row.reason,
                risk_level=step_row.risk_level,
                working_directory=step_row.working_directory,
                expected_output=step_row.expected_output,
            ),
            asset_summary=asset_summary,
            recent_output=recent_output,
            shell_type=shell_type,
            os_type=os_type,
        ):
            if isinstance(chunk, str):
                yield self._build_delta_event(message_id=executor_message_id, text=chunk, stage="executor")
                continue
            refined_step = chunk
        if refined_step is None:
            raise ValueError("executor did not return refined step")
        update_task_step(
            session,
            step_id,
            title=refined_step.title,
            command=refined_step.command,
            reason=refined_step.reason,
            working_directory=refined_step.working_directory,
            expected_output=refined_step.expected_output,
            risk_level=refined_step.risk_level,
            status="running",
        )
        create_approval(
            session,
            task_id=task_id,
            step_id=step_id,
            asset_id=asset_id,
            terminal_id=terminal_id,
            command=refined_step.command,
            working_directory=refined_step.working_directory,
            risk_level=refined_step.risk_level,
            llm_explanation=refined_step.reason,
            expected_output=refined_step.expected_output,
            decision="pending",
            operator="system",
        )
        yield {
            "id": f"approval-{run_id}-{step_id}",
            "kind": "approval",
            "text": f"第 {step_index + 1} 步待审批命令：{refined_step.command}",
            "command": refined_step.command or "",
            "runId": run_id,
        }


