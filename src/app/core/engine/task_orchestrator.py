import uuid
from collections.abc import Iterator
from types import SimpleNamespace
from dataclasses import dataclass
from time import sleep, time

from sqlmodel import Session

from app.db.repositories.assistant import get_or_create_assistant_session
from app.db.repositories.models import get_default_model_config
from app.db.repositories.tasks import (
    create_agent_task,
    create_approval,
    create_command_execution,
    create_model_usage,
    create_task_steps,
    get_agent_task_by_run_id,
    get_latest_approval_by_task_id,
    list_task_steps_by_task_id,
    update_agent_task,
    update_command_execution,
    update_task_step,
)
from app.db.repositories.terminal import list_terminal_output_events_after
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

    def run(self, *, session: Session, prompt: str, asset_id: int, model_name: str | None = None) -> list[dict]:
        return list(self.stream_run(session=session, prompt=prompt, asset_id=asset_id, model_name=model_name))

    def stream_run(self, *, session: Session, prompt: str, asset_id: int, model_name: str | None = None) -> Iterator[dict]:
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
        terminal_session_id = self._find_terminal_session_id(session, asset_id)
        assistant_session = get_or_create_assistant_session(
            session,
            asset_id=asset_id,
            title="console",
            active_model=model_config.model_name,
            terminal_session_id=terminal_session_id,
            model_config_id=getattr(get_default_model_config(session), "id", None),
        )
        assistant_session_id = assistant_session.id
        if assistant_session_id is None:
            raise ValueError("assistant session id is required")
        asset_summary = (
            f"asset={getattr(asset, 'name', '')}, type={getattr(asset, 'asset_type', '')}, "
            f"host={getattr(asset, 'host', '')}, user={getattr(asset, 'username', '')}"
        )
        recent_output = self._deps.terminal_service.read_recent_output(terminal_session_id) if terminal_session_id else ""
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
        planner_events: list[dict] = []
        steps = self._deps.planner.stream_build_plan(
            config=model_config,
            user_input=prompt,
            asset_summary=asset_summary,
            recent_output=recent_output,
            on_delta=lambda delta: planner_events.append(self._build_delta_event(message_id=planner_message_id, text=delta, stage="planner")),
        )
        for event in planner_events:
            yield event
        task = create_agent_task(
            session,
            session_id=assistant_session_id,
            run_id=run_id,
            asset_id=asset_id,
            user_input=prompt,
            attached_terminal_context=recent_output,
            task_type="ops_plan_exec",
            risk_level=max((step.risk_level for step in steps), default="low"),
            status=TaskStatus.PENDING_APPROVAL.value,
            terminal_session_id=terminal_session_id,
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
            terminal_session_id=terminal_session_id,
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
                terminal_session_id=task.terminal_session_id,
                command=current_step.command,
                working_directory=current_step.working_directory,
                risk_level=current_step.risk_level,
                llm_explanation=current_step.reason,
                expected_output=current_step.expected_output,
                decision=ApprovalDecision.REJECTED.value,
                operator="user",
            )
            update_agent_task(session, task.id, status=TaskStatus.REJECTED.value, final_summary="用户拒绝了当前命令。")
            yield {"id": f"error-{run_id}", "kind": "error", "text": "用户拒绝了当前命令。"}
            return

        active_terminal_session_id = task.terminal_session_id
        if active_terminal_session_id is not None and self._deps.terminal_service.get_session(active_terminal_session_id) is None:
            try:
                active_terminal_session_id = self._restore_terminal_session(session=session, asset_id=task.asset_id)
                update_agent_task(session, task.id, terminal_session_id=active_terminal_session_id)
                task.terminal_session_id = active_terminal_session_id
            except Exception as exc:
                update_agent_task(session, task.id, status=TaskStatus.FAILED.value, final_summary="终端会话已失效，自动重建失败。")
                yield {"id": f"error-{run_id}", "kind": "error", "text": f"终端会话已失效，自动重建失败：{exc}"}
                return

        update_agent_task(session, task.id, status=TaskStatus.RUNNING.value)
        approval = create_approval(
            session,
            task_id=task.id,
            step_id=current_step_id,
            asset_id=task.asset_id,
            terminal_session_id=active_terminal_session_id,
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
            terminal_session_id=active_terminal_session_id or 0,
            command=current_step.command,
            status=CommandExecutionStatus.RUNNING.value,
            approval_id=approval.id,
            working_directory=current_step.working_directory,
        )
        execution_id = execution.id
        if execution_id is None:
            raise ValueError("command execution id is required")
        last_terminal_output_event_id = self._get_last_terminal_output_event_id(session, active_terminal_session_id)
        if active_terminal_session_id is not None:
            self._deps.terminal_service.send_input(active_terminal_session_id, f"{current_step.command}\n")
            output = self._collect_command_output(
                session=session,
                terminal_session_id=active_terminal_session_id,
                after_event_id=last_terminal_output_event_id,
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
        review_events: list[dict] = []
        review = self._deps.planner.stream_review_step_result(
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
            on_delta=lambda delta: review_events.append(self._build_delta_event(message_id=review_message_id, text=delta, stage="review")),
        )

        events: list[dict] = [*review_events]
        events.append({"id": f"output-{run_id}-{current_step_id}", "kind": "output", "text": output or "命令已发送，暂无输出。"})
        plan_id = f"task-{run_id}"
        if review.decision == "complete" or not remaining_rows:
            summary = review.summary or f"任务完成，最后执行步骤：{current_step.title}"
            update_agent_task(session, task.id, status=TaskStatus.COMPLETED.value, final_summary=summary)
            plan_steps = self._load_plan_steps(session, task.id)
            events.append(self._build_plan_event(task.id, plan_steps, current_index=len(plan_steps), version=2, plan_id=plan_id))
            events.append({"id": f"final-{run_id}", "kind": "final", "text": summary})
            yield from events
            return

        next_row = remaining_rows[0]
        next_row_id = next_row.id
        if next_row_id is None:
            raise ValueError("next step id is required")
        update_task_step(session, next_row_id, status="running")
        update_agent_task(session, task.id, status=TaskStatus.PENDING_APPROVAL.value)
        plan_steps = self._load_plan_steps(session, task.id)
        events.append(self._build_plan_event(task.id, plan_steps, current_index=current_index + 1, version=2, plan_id=plan_id))
        yield from events
        yield from self._prepare_step_approval(
            session=session,
            task_id=task.id,
            run_id=run_id,
            asset_id=task.asset_id,
            terminal_session_id=task.terminal_session_id,
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

    def _find_terminal_session_id(self, session: Session, asset_id: int) -> int | None:
        from app.db.repositories.terminal import list_terminal_sessions_by_asset_id

        rows = list_terminal_sessions_by_asset_id(session, asset_id)
        return rows[0].id if rows else None

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
        terminal_session_id: int | None,
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
        executor_events: list[dict] = []
        refined_step = self._deps.executor.stream_refine_step(
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
            on_delta=lambda delta: executor_events.append(self._build_delta_event(message_id=executor_message_id, text=delta, stage="executor")),
        )
        for event in executor_events:
            yield event
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
            terminal_session_id=terminal_session_id,
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
            "runId": run_id,
        }

    def _collect_command_output(
        self,
        *,
        session: Session,
        terminal_session_id: int,
        after_event_id: int,
        max_wait_seconds: float = 5.0,
        idle_timeout_seconds: float = 0.4,
        poll_interval_seconds: float = 0.1,
    ) -> str:
        deadline = time() + max_wait_seconds
        idle_deadline: float | None = None
        output_parts: list[str] = []
        seen_event_id = after_event_id
        while time() < deadline:
            events = list_terminal_output_events_after(session, terminal_session_id, seen_event_id)
            if events:
                output_parts.extend(event.event_data for event in events)
                seen_event_id = max(event.id or seen_event_id for event in events)
                idle_deadline = time() + idle_timeout_seconds
                sleep(poll_interval_seconds)
                continue
            if idle_deadline is not None and time() >= idle_deadline:
                break
            sleep(poll_interval_seconds)
        return "".join(output_parts)

    def _get_last_terminal_output_event_id(self, session: Session, terminal_session_id: int | None) -> int:
        if terminal_session_id is None:
            return 0
        events = list_terminal_output_events_after(session, terminal_session_id, 0)
        if not events:
            return 0
        return max(event.id or 0 for event in events)

    def _restore_terminal_session(self, *, session: Session, asset_id: int) -> int:
        asset = get_asset_record(session, asset_id)
        if asset is None and asset_id == 0:
            asset = SimpleNamespace(
                id=0,
                name="本地终端",
                asset_type="local_terminal",
                host="localhost",
                username="",
            )
        if asset is None:
            raise ValueError("asset not found")
        result = self._deps.terminal_service.open_session(asset)
        terminal_session_id = result.get("terminal_session_id")
        if not isinstance(terminal_session_id, int):
            raise ValueError(result.get("error") or "terminal session restore failed")
        return terminal_session_id

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
