import uuid
from collections.abc import Iterator
from dataclasses import dataclass
from time import sleep, time
from types import SimpleNamespace

from sqlmodel import Session

from app.db.repositories.models import get_default_model_config
from app.db.repositories.tasks import (
    create_agent_task,
    create_approval,
    create_command_execution,
    create_model_usage,
    create_task_steps,
    get_agent_task_by_run_id,
    list_task_steps_by_task_id,
    update_agent_task,
    update_command_execution,
    update_task_step,
)
from app.services.asset_service import get_asset_record
from app.services.executor_service import ExecutorService
from app.services.model_service import ModelService
from app.services.planner_service import PlannerService
from app.services.terminal_service import TerminalService
from app.shared.enums import ApprovalDecision, CommandExecutionStatus, TaskStatus
from app.shared.schemas import PlanStep


@dataclass
class OrchestratorDependencies:
    planner: PlannerService
    executor: ExecutorService
    model_service: ModelService
    terminal_service: TerminalService


class TaskOrchestrator:
    def __init__(self, deps: OrchestratorDependencies):
        self._deps = deps

    def run(self, *, session: Session, prompt: str, asset_id: int, terminal_id: str | None = None, model_name: str | None = None) -> list[dict]:
        return list(self.stream_run(session=session, prompt=prompt, asset_id=asset_id, terminal_id=terminal_id, model_name=model_name))

    def stream_run(self, *, session: Session, prompt: str, asset_id: int, terminal_id: str | None = None, model_name: str | None = None) -> Iterator[dict]:
        asset = get_asset_record(session, asset_id)
        if asset is None and asset_id == 0:
            asset = SimpleNamespace(
                id=0,
                name="本地终端",
                asset_type="local_terminal",
                host="localhost",
                username="",
            )

        model_config = self._resolve_model_config(session, model_name)
        conversation_id = f"conversation-{uuid.uuid4()}"
        
        asset_summary = (
            f"asset={getattr(asset, 'name', '')}, type={getattr(asset, 'asset_type', '')}, "
            f"host={getattr(asset, 'host', '')}, user={getattr(asset, 'username', '')}"
        )
        recent_output = self._deps.terminal_service.read_recent_output(terminal_id) if terminal_id else ""
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
            status=TaskStatus.PENDING_APPROVAL.value,
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
            update_agent_task(session, task_id, status=TaskStatus.FAILED.value, final_summary="未生成可执行计划，请补充更明确的任务目标。")
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
            total_steps=len(task_steps),
            asset_summary=asset_summary,
            recent_output=recent_output,
            model_config=model_config,
        )

    def approve(self, *, session: Session, run_id: str, approved: bool) -> list[dict]:
        return list(self.stream_approve(session=session, run_id=run_id, approved=approved))

    def stream_approve(self, *, session: Session, run_id: str, approved: bool) -> Iterator[dict]:
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
            update_agent_task(session, task.id, status=TaskStatus.PENDING_APPROVAL.value, final_summary="")
            yield {
                "id": f"approval-{run_id}-{current_step_id}-rejected",
                "kind": "approval",
                "text": "已拒绝当前命令，请调整后继续审批。",
                "command": current_step.command or "",
                "runId": run_id,
            }
            return

        active_terminal_id = task.terminal_id
        if active_terminal_id is not None and self._deps.terminal_service.get_session(active_terminal_id) is None:
            update_agent_task(session, task.id, status=TaskStatus.FAILED.value, final_summary="终端连接已失效，请重新建立连接后再试。")
            yield {"id": f"error-{run_id}", "kind": "error", "text": "终端连接已失效，请重新建立连接后再试。"}
            return

        update_agent_task(session, task.id, status=TaskStatus.RUNNING.value)
        approval = create_approval(
            session,
            task_id=task.id,
            step_id=current_step_id,
            asset_id=task.asset_id,
            terminal_id=active_terminal_id,
            command=current_step.command,
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
            command=current_step.command,
            status=CommandExecutionStatus.RUNNING.value,
            approval_id=approval.id,
            working_directory=current_step.working_directory,
        )
        execution_id = execution.id
        if execution_id is None:
            raise ValueError("command execution id is required")

        output_cursor = self._deps.terminal_service.get_output_cursor(active_terminal_id) if active_terminal_id else 0
        if active_terminal_id is not None:
            self._deps.terminal_service.send_input(active_terminal_id, f"{current_step.command}\n")
            output = self._collect_command_output(
                terminal_id=active_terminal_id,
                after_cursor=output_cursor,
            )
        else:
            output = ""

        update_task_step(session, current_step_id, status="completed", output=output)
        update_command_execution(session, execution_id, status=CommandExecutionStatus.COMPLETED.value, output=output)

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
            command_output=output,
            remaining_steps=remaining_steps,
        ):
            if isinstance(chunk, str):
                yield self._build_delta_event(message_id=review_message_id, text=chunk, stage="review")
                continue
            review = chunk

        yield {"id": f"output-{run_id}-{current_step_id}", "kind": "output", "text": output or "命令已发送，暂无输出。"}
        plan_id = f"task-{run_id}"

        if review is not None and review.decision == "retry":
            update_task_step(session, current_step_id, status="running")
            update_agent_task(session, task.id, status=TaskStatus.PENDING_APPROVAL.value)
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
                total_steps=len(task_steps),
                asset_summary=f"asset_id={task.asset_id}",
                recent_output=output,
                model_config=model_config,
            )
            return

        if not remaining_rows:
            plan_steps = self._load_plan_steps(session, task.id)
            execution_history: list[dict[str, str]] = []
            latest_rows = list_task_steps_by_task_id(session, task.id)
            for row in latest_rows:
                execution_history.append(
                    {
                        "step": row.title,
                        "command": row.command,
                        "output": row.output or "",
                    }
                )
            summary = self._deps.planner.summarize_task_result(
                config=model_config,
                user_input=task.user_input,
                completed_steps=plan_steps,
                execution_history=execution_history,
            )
            if not summary:
                summary = (review.summary if review is not None else "") or f"任务完成，最后执行步骤：{current_step.title}"
            update_agent_task(session, task.id, status=TaskStatus.COMPLETED.value, final_summary=summary)
            yield self._build_plan_event(task.id, plan_steps, current_index=len(plan_steps), version=2, plan_id=plan_id)
            yield {"id": f"final-{run_id}", "kind": "final", "text": summary}
            return

        if review is not None and review.decision != "advance":
            update_agent_task(session, task.id, status=TaskStatus.FAILED.value, final_summary="评估结果无效，无法推进任务。")
            yield {"id": f"error-{run_id}-review", "kind": "error", "text": "评估结果无效，无法推进任务。"}
            return

        next_row = remaining_rows[0]
        next_row_id = next_row.id
        if next_row_id is None:
            raise ValueError("next step id is required")
        update_task_step(session, next_row_id, status="running")
        update_agent_task(session, task.id, status=TaskStatus.PENDING_APPROVAL.value)
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
            total_steps=len(task_steps),
            asset_summary=f"asset_id={task.asset_id}",
            recent_output=output,
            model_config=model_config,
        )

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

    def _prepare_step_approval(
        self,
        *,
        session: Session,
        task_id: int,
        run_id: str,
        asset_id: int,
        terminal_id: str | None,
        step_row,
        step_index: int,
        total_steps: int,
        asset_summary: str,
        recent_output: str,
        model_config,
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

    def _collect_command_output(
        self,
        *,
        terminal_id: str,
        after_cursor: int,
        max_wait_seconds: float = 5.0,
        idle_timeout_seconds: float = 0.4,
        poll_interval_seconds: float = 0.1,
    ) -> str:
        deadline = time() + max_wait_seconds
        idle_deadline: float | None = None
        output_parts: list[str] = []
        cursor = after_cursor
        while time() < deadline:
            cursor, output = self._deps.terminal_service.read_output_since(terminal_id, cursor)
            if output:
                output_parts.append(output)
                idle_deadline = time() + idle_timeout_seconds
                sleep(poll_interval_seconds)
                continue
            if idle_deadline is not None and time() >= idle_deadline:
                break
            sleep(poll_interval_seconds)
        return "".join(output_parts)

    def _build_delta_event(self, *, message_id: str, text: str, stage: str) -> dict:
        return {
            "id": f"delta-{message_id}-{uuid.uuid4()}",
            "kind": "delta",
            "messageId": message_id,
            "stage": stage,
            "text": text,
        }

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
