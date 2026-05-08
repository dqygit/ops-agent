from __future__ import annotations

import uuid
from collections.abc import Iterator
from datetime import UTC, datetime

from sqlmodel import Session

from app.db.repositories.tasks import (
    create_approval,
    create_command_execution,
    get_agent_task_by_run_id,
    list_task_steps_by_task_id,
    update_agent_task,
    update_command_execution,
    update_task_step,
)
from app.shared.enums import ApprovalDecision, CommandExecutionStatus
from app.shared.schemas import PlanStep

from .task_use_cases_base import COMMAND_SENTINEL, COMMAND_WRAP_END, COMMAND_WRAP_START, BaseTaskUseCase, CommandRunResult


class TaskApprovalUseCase(BaseTaskUseCase):
    def execute(self, *, session: Session, run_id: str, approved: bool) -> Iterator[dict]:
        task = get_agent_task_by_run_id(session, run_id)
        if task is None or task.id is None:
            raise ValueError("Task not found")

        task_steps = list_task_steps_by_task_id(session, task.id)
        current_step = next((step for step in task_steps if step.status == "running"), None)
        if current_step is None:
            current_step = next((step for step in task_steps if step.status == "pending"), None)
        if current_step is None or current_step.id is None:
            yield {"id": f"final-{run_id}", "kind": "final", "text": task.final_summary or "任务已结束。"}
            return

        current_step_id = current_step.id
        if not approved:
            create_approval(
                session,
                task_id=task.id,
                step_id=current_step_id,
                asset_id=task.asset_id,
                terminal_id=task.terminal_id,
                command=current_step.command,
                working_directory=current_step.working_directory,
                risk_level=current_step.risk_level,
                llm_explanation=current_step.reason,
                expected_output=current_step.expected_output,
                decision=ApprovalDecision.REJECTED.value,
                operator="user",
            )
            update_task_step(session, current_step_id, status="pending")
            self._deps.state_machine.mark_pending_approval(session, task.id, final_summary="")
            yield {
                "id": f"approval-{run_id}-{current_step_id}-rejected",
                "kind": "approval",
                "text": "已拒绝当前命令，请调整后继续审批。",
                "command": current_step.command or "",
                "runId": run_id,
            }
            return

        active_terminal_id = task.terminal_id
        if active_terminal_id is None or self._deps.terminal_service.get_session(active_terminal_id) is None:
            asset = self._resolve_asset(session, task.asset_id)
            if asset is None:
                self._deps.state_machine.mark_failed(session, task.id, "资产不存在，无法重建终端会话。")
                yield {"id": f"error-{run_id}", "kind": "error", "text": "资产不存在，无法重建终端会话。"}
                return
            reopen_result = self._deps.terminal_service.open_session(asset, reuse_existing=True)
            reopened_terminal_id = reopen_result.get("terminal_id")
            if not reopened_terminal_id:
                self._deps.state_machine.mark_failed(session, task.id, "终端连接已失效，且重建失败，请重新建立连接后再试。")
                yield {"id": f"error-{run_id}", "kind": "error", "text": "终端连接已失效，且重建失败，请重新建立连接后再试。"}
                return
            active_terminal_id = reopened_terminal_id
            update_agent_task(session, task.id, terminal_id=active_terminal_id)

        execution_shell_type = "unknown"
        if active_terminal_id:
            try:
                execution_shell_type = self._deps.terminal_service.get_shell_kind(active_terminal_id)
            except ValueError:
                execution_shell_type = "unknown"

        self._deps.state_machine.mark_running(session, task.id)
        approval = create_approval(
            session,
            task_id=task.id,
            step_id=current_step_id,
            asset_id=task.asset_id,
            terminal_id=active_terminal_id,
            command=f"{current_step.command}\n",
            working_directory=current_step.working_directory,
            risk_level=current_step.risk_level,
            llm_explanation=current_step.reason,
            expected_output=current_step.expected_output,
            decision=ApprovalDecision.APPROVED.value,
            operator="user",
        )
        execution = create_command_execution(
            session,
            task_id=task.id,
            step_id=current_step_id,
            asset_id=task.asset_id,
            terminal_id=active_terminal_id or "",
            command=f"{current_step.command}\n",
            status=CommandExecutionStatus.RUNNING.value,
            approval_id=approval.id,
            working_directory=current_step.working_directory,
        )
        execution_id = execution.id
        if execution_id is None:
            raise ValueError("command execution id is required")

        output_cursor = self._deps.terminal_service.get_command_event_cursor(active_terminal_id) if active_terminal_id else 0
        if active_terminal_id is not None:
            wrapped_command = (
                f"printf '%s\\n' '{COMMAND_WRAP_START}'\n"
                f"{current_step.command}\n"
                "__ops_agent_exit_code=$?\n"
                f"printf '%s%s\\n' '{COMMAND_SENTINEL}:' \"${{__ops_agent_exit_code}}\"\n"
                f"printf '%s\\n' '{COMMAND_WRAP_END}'"
            )
            command_id = self._deps.terminal_service.send_input(
                active_terminal_id,
                wrapped_command,
                output_markers={
                    "start_marker": COMMAND_WRAP_START,
                    "end_marker": COMMAND_WRAP_END,
                    "done_marker_prefix": f"{COMMAND_SENTINEL}:",
                },
            )
            if command_id is None:
                command_result = CommandRunResult(output="", exit_code=None, completed=False)
            else:
                command_result = self._collect_command_output(terminal_id=active_terminal_id, command_id=command_id, after_cursor=output_cursor)
        else:
            command_result = CommandRunResult(output="", exit_code=None, completed=False)

        step_status = "completed"
        execution_status = CommandExecutionStatus.COMPLETED.value
        if not command_result.completed or command_result.exit_code not in {None, 0}:
            step_status = "failed"
            execution_status = CommandExecutionStatus.FAILED.value

        update_task_step(
            session,
            current_step_id,
            status=step_status,
            output=command_result.output,
            exit_code=command_result.exit_code,
            finished_at=datetime.now(UTC),
        )
        update_command_execution(
            session,
            execution_id,
            status=execution_status,
            output=command_result.output,
            exit_code=command_result.exit_code,
            finished_at=datetime.now(UTC),
        )

        current_index = next((index for index, step in enumerate(task_steps) if step.id == current_step.id), 0)
        remaining_rows = task_steps[current_index + 1 :]
        remaining_steps = [
            PlanStep(
                title=row.title,
                command=row.command,
                reason=row.reason,
                risk_level=row.risk_level,
                working_directory=row.working_directory,
                expected_output=row.expected_output,
            )
            for row in remaining_rows
        ]
        model_config = self._resolve_model_config(session, None)
        active_shell_type = execution_shell_type
        active_os_type = self._infer_os_type(active_shell_type)
        review_message_id = f"message-review-{uuid.uuid4()}"
        review = None
        for chunk in self._deps.planner.stream_review_step_result(
            config=model_config,
            user_input=task.user_input,
            current_step=PlanStep(
                title=current_step.title,
                command=current_step.command,
                reason=current_step.reason,
                risk_level=current_step.risk_level,
                working_directory=current_step.working_directory,
                expected_output=current_step.expected_output,
            ),
            command_output=command_result.output,
            remaining_steps=remaining_steps,
        ):
            if isinstance(chunk, str):
                yield self._build_delta_event(message_id=review_message_id, text=chunk, stage="review")
                continue
            review = chunk

        yield {
            "id": f"command-start-{run_id}-{current_step_id}",
            "kind": "command_start",
            "commandId": command_result.command_id or f"task-step-{current_step_id}",
            "terminalId": active_terminal_id,
            "command": current_step.command,
            "title": current_step.title,
        }
        if command_result.output:
            yield {
                "id": f"command-chunk-{run_id}-{current_step_id}",
                "kind": "command_chunk",
                "commandId": command_result.command_id or f"task-step-{current_step_id}",
                "terminalId": active_terminal_id,
                "stream": "stdout",
                "text": command_result.output,
            }
        yield {
            "id": f"command-end-{run_id}-{current_step_id}",
            "kind": "command_end",
            "commandId": command_result.command_id or f"task-step-{current_step_id}",
            "terminalId": active_terminal_id,
            "exitCode": command_result.exit_code,
            "summary": "completed" if command_result.completed and command_result.exit_code in {None, 0} else "failed",
        }

        output_text = command_result.output
        if not command_result.completed:
            output_text = (output_text + "\n\n命令未在预期时间内完成，可能仍在运行或进入了交互状态。").strip()
        elif command_result.exit_code not in {None, 0}:
            output_text = (output_text + f"\n\n命令以非零退出码结束: {command_result.exit_code}").strip()
        plan_id = f"task-{run_id}"

        if not command_result.completed or command_result.exit_code not in {None, 0}:
            self._deps.state_machine.mark_pending_approval(session, task.id)
            yield {"id": f"error-{run_id}-{current_step_id}", "kind": "error", "text": "命令未成功完成，请根据输出调整后重试。"}
            return

        if review is not None and review.decision == "retry":
            update_task_step(session, current_step_id, status="running")
            self._deps.state_machine.mark_pending_approval(session, task.id)
            plan_steps = self._load_plan_steps(session, task.id)
            yield self._build_plan_event(task.id, plan_steps, current_index=current_index, version=2, plan_id=plan_id)
            yield from self._prepare_step_approval(
                session=session,
                task_id=task.id,
                run_id=run_id,
                asset_id=task.asset_id,
                terminal_id=task.terminal_id,
                step_row=current_step,
                step_index=current_index,
                asset_summary=f"asset_id={task.asset_id}",
                recent_output=command_result.output,
                model_config=model_config,
                shell_type=active_shell_type,
                os_type=active_os_type,
            )
            return

        if not remaining_rows:
            plan_steps = self._load_plan_steps(session, task.id)
            execution_history: list[dict[str, str]] = []
            latest_rows = list_task_steps_by_task_id(session, task.id)
            for row in latest_rows:
                execution_history.append({"step": row.title, "command": row.command, "output": row.output or ""})
            summary = self._deps.planner.summarize_task_result(
                config=model_config,
                user_input=task.user_input,
                completed_steps=plan_steps,
                execution_history=execution_history,
            )
            if not summary:
                summary = (review.summary if review is not None else "") or f"任务完成，最后执行步骤：{current_step.title}"
            self._deps.state_machine.mark_completed(session, task.id, summary)
            yield self._build_plan_event(task.id, plan_steps, current_index=len(plan_steps), version=2, plan_id=plan_id)
            yield {"id": f"final-{run_id}", "kind": "final", "text": summary}
            return

        if review is not None and review.decision != "advance":
            self._deps.state_machine.mark_failed(session, task.id, "评估结果无效，无法推进任务。")
            yield {"id": f"error-{run_id}-review", "kind": "error", "text": "评估结果无效，无法推进任务。"}
            return

        next_row = remaining_rows[0]
        next_row_id = next_row.id
        if next_row_id is None:
            raise ValueError("next step id is required")
        update_task_step(session, next_row_id, status="running")
        self._deps.state_machine.mark_pending_approval(session, task.id)
        plan_steps = self._load_plan_steps(session, task.id)
        yield self._build_plan_event(task.id, plan_steps, current_index=current_index + 1, version=2, plan_id=plan_id)
        yield from self._prepare_step_approval(
            session=session,
            task_id=task.id,
            run_id=run_id,
            asset_id=task.asset_id,
            terminal_id=task.terminal_id,
            step_row=next_row,
            step_index=current_index + 1,
            asset_summary=f"asset_id={task.asset_id}",
            recent_output=command_result.output,
            model_config=model_config,
            shell_type=active_shell_type,
            os_type=active_os_type,
        )
