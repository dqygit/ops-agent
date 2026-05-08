from __future__ import annotations

from collections.abc import Iterator
from typing import Any

from sqlmodel import Session

from app.db.repositories.tasks import get_latest_recoverable_task_by_conversation_id, list_task_steps_by_task_id

from .task_use_cases_base import BaseTaskUseCase


class TaskResumeUseCase(BaseTaskUseCase):
    def resume_if_possible(
        self,
        *,
        session: Session,
        conversation_id: str,
        prompt: str,
        asset_id: int,
        terminal_id: str | None,
        model_name: str | None,
    ) -> Iterator[dict] | None:
        task = get_latest_recoverable_task_by_conversation_id(session, conversation_id)
        if task is None:
            return None
        return self._resume_task(
            session=session,
            task=task,
            prompt=prompt,
            asset_id=asset_id,
            terminal_id=terminal_id,
            model_name=model_name,
        )

    def _resume_task(
        self,
        *,
        session: Session,
        task: Any,
        prompt: str,
        asset_id: int,
        terminal_id: str | None,
        model_name: str | None,
    ) -> Iterator[dict]:
        del prompt, asset_id, terminal_id, model_name
        if task.id is None:
            raise ValueError("task id is required")

        task_steps = list_task_steps_by_task_id(session, task.id)
        if not task_steps:
            self._deps.state_machine.mark_failed(session, task.id, "任务缺少可恢复步骤，无法继续执行。")
            yield {"id": f"error-{task.run_id}-resume", "kind": "error", "text": "任务缺少可恢复步骤，无法继续执行。"}
            return

        current_step = next((step for step in task_steps if step.status == "running"), None)
        if current_step is None:
            current_step = next((step for step in task_steps if step.status == "pending"), None)
        if current_step is None or current_step.id is None:
            yield {"id": f"final-{task.run_id}", "kind": "final", "text": task.final_summary or "任务已结束。"}
            return

        current_index = next((index for index, step in enumerate(task_steps) if step.id == current_step.id), 0)
        plan_steps = self._load_plan_steps(session, task.id)
        plan_id = f"task-{task.run_id}"

        if task.status == "running":
            yield {"id": f"status-{task.run_id}-resume", "kind": "status", "text": "检测到未完成任务，正在恢复执行上下文。"}
            from .task_use_cases_approval import TaskApprovalUseCase

            approval_use_case = TaskApprovalUseCase(self._deps)
            yield from approval_use_case.execute(session=session, run_id=task.run_id, approved=True)
            return

        yield {"id": f"status-{task.run_id}-resume", "kind": "status", "text": "检测到未完成任务，已恢复到待审批步骤。"}
        yield self._build_plan_event(task.id, plan_steps, current_index=current_index, version=2, plan_id=plan_id)
        yield {
            "id": f"approval-{task.run_id}-{current_step.id}-resume",
            "kind": "approval",
            "text": f"第 {current_index + 1} 步待审批命令：{current_step.command}",
            "command": current_step.command or "",
            "runId": task.run_id,
        }


