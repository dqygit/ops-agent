from __future__ import annotations

import uuid
from collections.abc import Iterator

from sqlmodel import Session

from app.db.repositories.tasks import create_agent_task, create_model_usage, create_task_steps, update_task_step
from app.shared.schemas import PlanStep

from .task_use_cases_base import BaseTaskUseCase
from .task_use_cases_resume import TaskResumeUseCase


class TaskRunUseCase(BaseTaskUseCase):
    def execute(
        self,
        *,
        session: Session,
        prompt: str,
        asset_id: int,
        terminal_id: str | None = None,
        model_name: str | None = None,
        conversation_id: str = "console",
    ) -> Iterator[dict]:
        asset = self._resolve_asset(session, asset_id)
        resume_stream = TaskResumeUseCase(self._deps).resume_if_possible(
            session=session,
            conversation_id=conversation_id,
            prompt=prompt,
            asset_id=asset_id,
            terminal_id=terminal_id,
            model_name=model_name,
        )
        if resume_stream is not None:
            yield from resume_stream
            return

        model_config = self._resolve_model_config(session, model_name)
        asset_summary = (
            f"asset={getattr(asset, 'name', '')}, type={getattr(asset, 'asset_type', '')}, "
            f"host={getattr(asset, 'host', '')}, user={getattr(asset, 'username', '')}"
        )
        recent_output = self._deps.terminal_service.read_buffered_output(terminal_id) if terminal_id else ""
        shell_type = "unknown"
        if terminal_id:
            try:
                shell_type = self._deps.terminal_service.get_shell_kind(terminal_id)
            except ValueError:
                shell_type = "unknown"
        os_type = self._infer_os_type(shell_type)
        run_id = str(uuid.uuid4())
        plan_stream_id = f"task-{run_id}"

        yield {
            "id": f"plan-{plan_stream_id}-v0",
            "kind": "plan",
            "planId": plan_stream_id,
            "title": "Task Plan",
            "version": 0,
            "isLatest": True,
            "updated": False,
            "loading": True,
            "steps": [],
        }

        planner_message_id = f"message-plan-{uuid.uuid4()}"
        steps: list[PlanStep] = []
        for chunk in self._deps.planner.stream_build_plan(
            config=model_config,
            user_input=prompt,
            asset_summary=asset_summary,
            recent_output=recent_output,
            shell_type=shell_type,
            os_type=os_type,
        ):
            if isinstance(chunk, str):
                yield self._build_delta_event(message_id=planner_message_id, text=chunk, stage="planner")
                continue
            steps = chunk

        task = create_agent_task(
            session,
            conversation_id=conversation_id,
            run_id=run_id,
            asset_id=asset_id,
            terminal_id=terminal_id,
            user_input=prompt,
            attached_terminal_context=recent_output,
            task_type="ops_plan_exec",
            risk_level=max((step.risk_level for step in steps), default="low"),
            status="pending_approval",
        )
        task_id = task.id
        if task_id is None:
            raise ValueError("task id is required")

        create_model_usage(
            session,
            task_id=task_id,
            provider=model_config.provider.value,
            model_name=model_config.model_name,
            base_url_snapshot=model_config.base_url,
            temperature_snapshot=model_config.temperature,
            max_tokens_snapshot=model_config.max_tokens,
        )

        if not steps:
            self._deps.state_machine.mark_failed(session, task_id, "未生成可执行计划，请补充更明确的任务目标。")
            yield {"id": f"error-{run_id}", "kind": "error", "text": "未生成可执行计划，请补充更明确的任务目标。"}
            return

        task_steps = create_task_steps(session, task_id, steps)
        current_step = task_steps[0]
        current_step_id = current_step.id
        if current_step_id is None:
            raise ValueError("current step id is required")
        update_task_step(session, current_step_id, status="running")

        yield self._build_plan_event(task_id, steps, current_index=0, version=1, plan_id=plan_stream_id)
        yield from self._prepare_step_approval(
            session=session,
            task_id=task_id,
            run_id=run_id,
            asset_id=asset_id,
            terminal_id=terminal_id,
            step_row=current_step,
            step_index=0,
            asset_summary=asset_summary,
            recent_output=recent_output,
            model_config=model_config,
            shell_type=shell_type,
            os_type=os_type,
        )


