from __future__ import annotations

import logging
import uuid
from collections.abc import Iterator
from types import SimpleNamespace
from typing import Any

from sqlmodel import Session

from app.core.loop import (
    AgentLoop,
    LLMPlanner,
    LLMRefiner,
    LoopContext,
    LoopEvent,
    LoopRuntimeStep,
    LoopState,
    TerminalExecutor,
)
from app.core.runtime.conversation import ConversationRuntime, RuntimeStepState
from app.core.runtime.conversation_manager import ConversationRuntimeManager
from app.db.repositories.assets import get_asset
from app.db.repositories.models import get_default_model_config
from app.services.model_service import ModelService
from app.services.terminal_service import TerminalService


logger = logging.getLogger(__name__)


class _TerminalSessionAdapter:
    """把 TerminalService + ConversationRuntimeManager 适配为 loop 的 TerminalSessionResolver。"""

    def __init__(self, terminal_service: TerminalService, runtime_manager: ConversationRuntimeManager) -> None:
        self._terminal_service = terminal_service
        self._runtime_manager = runtime_manager

    def get_session(self, terminal_id: str) -> Any | None:
        return self._terminal_service.get_session(terminal_id)

    def acquire_terminal_slot(self, runtime_id: str, terminal_id: str) -> bool:
        return self._runtime_manager.acquire_terminal_execution_slot(runtime_id, terminal_id)

    def release_terminal_slot(self, runtime_id: str, terminal_id: str) -> None:
        self._runtime_manager.release_terminal_execution_slot(runtime_id, terminal_id)


class TaskOrchestrator:
    def __init__(self, app_service: "ConsoleAppService", terminal_service: TerminalService) -> None:
        self._app_service = app_service
        self._terminal_service = terminal_service

    def stream_run(
        self,
        *,
        session: Session,
        prompt: str,
        asset_id: int,
        terminal_id: str | None = None,
        model_name: str | None = None,
        conversation_id: str = "console",
        mode: str = "agent",
    ) -> Iterator[dict]:
        return self._app_service.stream_run(
            session=session,
            prompt=prompt,
            asset_id=asset_id,
            terminal_id=terminal_id,
            model_name=model_name,
            conversation_id=conversation_id,
            mode=mode,
            terminal_service=self._terminal_service,
        )

    def stream_approve(self, *, session: Session, runtime_id: str, approved: bool) -> Iterator[dict]:
        return self._app_service.stream_approve(
            session=session,
            runtime_id=runtime_id,
            approved=approved,
            terminal_service=self._terminal_service,
        )


class ConsoleAppService:
    def __init__(
        self,
        *,
        planner: LLMPlanner | None = None,
        refiner: LLMRefiner | None = None,
        executor: TerminalExecutor | None = None,
        model_service: ModelService | None = None,
    ) -> None:
        self._planner = planner or LLMPlanner()
        self._refiner = refiner or LLMRefiner()
        self._executor = executor or TerminalExecutor()
        self._model_service = model_service or ModelService()
        self.runtime_manager = ConversationRuntimeManager()
        self._loop_states: dict[str, LoopState] = {}

    def build_orchestrator(self, terminal_service: TerminalService) -> TaskOrchestrator:
        return TaskOrchestrator(self, terminal_service)

    # ------------------------------------------------------------------
    # Public streaming entry points
    # ------------------------------------------------------------------

    def stream_run(
        self,
        *,
        session: Session,
        prompt: str,
        asset_id: int,
        terminal_id: str | None = None,
        model_name: str | None = None,
        conversation_id: str = "console",
        mode: str = "agent",
        terminal_service: TerminalService,
    ) -> Iterator[dict]:
        loop_mode = "plan" if mode == "plan" else "agent"

        asset = self._resolve_asset(session, asset_id)
        model_config = self._resolve_model_config(session, model_name)
        asset_summary = (
            f"asset={getattr(asset, 'name', '')}, type={getattr(asset, 'asset_type', '')}, "
            f"host={getattr(asset, 'host', '')}, user={getattr(asset, 'username', '')}"
        )
        recent_output = terminal_service.read_buffered_output(terminal_id) if terminal_id else ""
        shell_type = self._resolve_shell_type(terminal_service, terminal_id)
        os_type = self._infer_os_type(shell_type)

        runtime = self.runtime_manager.create_runtime(
            conversation_id=conversation_id,
            asset_id=asset_id,
            terminal_id=terminal_id,
        )
        runtime.mode = loop_mode  # type: ignore[assignment]

        context = LoopContext(
            runtime_id=runtime.runtime_id,
            conversation_id=conversation_id,
            asset_id=asset_id,
            terminal_id=terminal_id,
            asset_summary=asset_summary,
            shell_type=shell_type,
            os_type=os_type,
            user_prompt=prompt,
            model_config=model_config,
            mode=loop_mode,  # type: ignore[arg-type]
            recent_output=recent_output,
        )
        state = LoopState(phase="planning", context=context)
        self._loop_states[runtime.runtime_id] = state

        # 占位 plan SSE，与原行为保持一致（前端先看到 loading 计划面板）。
        plan_id = f"runtime-{runtime.runtime_id}"
        yield {
            "id": f"plan-{plan_id}-v0",
            "kind": "plan",
            "planId": plan_id,
            "title": "Task Plan",
            "version": 0,
            "isLatest": True,
            "updated": False,
            "loading": True,
            "steps": [],
            "runtimeId": runtime.runtime_id,
            "mode": loop_mode,
            "lockedPlan": False,
        }

        loop = self._build_loop(terminal_service)
        try:
            for event in loop.run(state):
                self._sync_runtime(runtime, event)
                sse = self._translate_event(event)
                if sse is not None:
                    yield sse
        except Exception as exc:
            logger.exception("stream_run failed conversation_id=%s runtime_id=%s", conversation_id, runtime.runtime_id)
            self.runtime_manager.append_event(runtime.runtime_id, "task_failed", error=str(exc))
            yield {"id": f"error-{runtime.runtime_id}", "kind": "error", "text": str(exc), "recoverable": True}

    def stream_approve(
        self,
        *,
        session: Session,
        runtime_id: str,
        approved: bool,
        terminal_service: TerminalService,
    ) -> Iterator[dict]:
        state = self._loop_states.get(runtime_id)
        runtime = self.runtime_manager.get_runtime(runtime_id)
        if state is None or runtime is None:
            yield {"id": f"error-{runtime_id}", "kind": "error", "text": "Runtime not found.", "recoverable": False}
            return

        loop = self._build_loop(terminal_service)
        try:
            for event in loop.resume_with_approval(state, approved=approved):
                self._sync_runtime(runtime, event)
                sse = self._translate_event(event)
                if sse is not None:
                    yield sse
        except Exception as exc:
            logger.exception("stream_approve failed runtime_id=%s", runtime_id)
            self.runtime_manager.append_event(runtime_id, "task_failed", error=str(exc))
            yield {"id": f"error-{runtime_id}", "kind": "error", "text": str(exc), "recoverable": True}

    # ------------------------------------------------------------------
    # Resolvers
    # ------------------------------------------------------------------

    def _resolve_asset(self, session: Session, asset_id: int):
        asset = get_asset(session, asset_id)
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
        default_record = get_default_model_config(session)
        default_config = (
            self._model_service.from_record(default_record)
            if default_record is not None
            else self._model_service.load_settings()
        )
        if model_name and model_name != default_config.model_name:
            default_config = default_config.model_copy(update={"model_name": model_name})
        return default_config

    def _resolve_shell_type(self, terminal_service: TerminalService, terminal_id: str | None) -> str:
        shell_type = "unknown"
        if terminal_id:
            try:
                shell_type = terminal_service.get_shell_kind(terminal_id)
            except ValueError:
                shell_type = "unknown"
        return shell_type

    def _infer_os_type(self, shell_type: str) -> str:
        if shell_type in {"powershell", "cmd"}:
            return "Windows"
        if shell_type in {"posix", "network", "serial"}:
            return "Darwin/Linux"
        return "unknown"

    # ------------------------------------------------------------------
    # Loop construction & event translation
    # ------------------------------------------------------------------

    def _build_loop(self, terminal_service: TerminalService) -> AgentLoop:
        terminal_adapter = _TerminalSessionAdapter(terminal_service, self.runtime_manager)
        return AgentLoop(
            planner=self._planner,
            refiner=self._refiner,
            executor=self._executor,
            terminal=terminal_adapter,
        )

    def _translate_event(self, event: LoopEvent) -> dict | None:
        runtime_id = event.runtime_id
        payload = event.payload
        kind = event.event_type

        if kind == "loop_delta":
            return {
                "id": f"delta-{event.message_id}-{uuid.uuid4()}",
                "kind": "delta",
                "messageId": event.message_id,
                "stage": event.stage,
                "text": payload.get("text", ""),
            }
        if kind == "loop_plan_updated":
            plan_payload = dict(payload.get("plan") or {})
            plan_payload.setdefault("kind", "plan")
            plan_payload.setdefault("runtimeId", runtime_id)
            return plan_payload
        if kind == "loop_approval_required":
            command = payload.get("command", "") or ""
            return {
                "id": f"approval-{runtime_id}-{event.step_id}",
                "kind": "approval",
                "text": f"第 {(event.step_index or 0) + 1} 步待审批命令：{command}",
                "command": command,
                "runtimeId": runtime_id,
                "stepId": event.step_id,
            }
        if kind == "loop_replan_pending_approval":
            return {
                "id": f"replan-{runtime_id}-{event.step_id}",
                "kind": "approval",
                "text": "当前步骤建议变更命令，已进入重规划审批。",
                "command": payload.get("proposed_command", "") or "",
                "runtimeId": runtime_id,
                "stepId": event.step_id,
            }
        if kind == "loop_execution_started":
            return {
                "id": f"command-start-{runtime_id}-{event.step_id}",
                "kind": "command_start",
                "commandId": payload.get("command_id"),
                "terminalId": payload.get("terminal_id"),
                "command": payload.get("command", ""),
                "title": payload.get("title", ""),
                "runtimeId": runtime_id,
            }
        if kind == "loop_execution_output":
            return {
                "id": f"command-chunk-{runtime_id}-{event.step_id}",
                "kind": "command_chunk",
                "commandId": payload.get("command_id"),
                "terminalId": payload.get("terminal_id"),
                "stream": payload.get("stream", "stdout"),
                "text": payload.get("text", ""),
                "runtimeId": runtime_id,
            }
        if kind == "loop_execution_completed":
            return {
                "id": f"command-end-{runtime_id}-{event.step_id}",
                "kind": "command_end",
                "commandId": payload.get("command_id"),
                "terminalId": payload.get("terminal_id"),
                "exitCode": payload.get("exit_code"),
                "summary": "completed" if payload.get("success") else "failed",
                "runtimeId": runtime_id,
            }
        if kind == "loop_completed":
            return {
                "id": f"final-{runtime_id}",
                "kind": "final",
                "text": payload.get("summary", ""),
                "runtimeId": runtime_id,
            }
        if kind == "loop_failed":
            return {
                "id": f"error-{runtime_id}",
                "kind": "error",
                "text": payload.get("error", ""),
                "runtimeId": runtime_id,
            }
        return None

    # ------------------------------------------------------------------
    # Runtime state sync (for /api/console/runtimes/{id}/snapshot & events)
    # ------------------------------------------------------------------

    def _sync_runtime(self, runtime: ConversationRuntime, event: LoopEvent) -> None:
        kind = event.event_type
        payload = event.payload
        state = self._loop_states.get(runtime.runtime_id)

        if kind == "loop_plan_updated" and state is not None:
            runtime.steps = [self._to_runtime_step(step) for step in state.steps]
            runtime.cursor = state.cursor
            runtime.plan_version = state.plan_version
            runtime.locked_plan = state.locked_plan
            runtime.touch()
            self.runtime_manager.append_event(runtime.runtime_id, "plan_updated", plan=payload.get("plan", {}))
            return

        if kind == "loop_approval_required":
            if event.step_id:
                runtime.mark_waiting_approval(event.step_id)
            self.runtime_manager.append_event(runtime.runtime_id, "task_waiting_input")
            self.runtime_manager.append_event(
                runtime.runtime_id,
                "approval_required",
                stepId=event.step_id,
                command=payload.get("command"),
                title=payload.get("title"),
                reason=payload.get("reason"),
                riskLevel=payload.get("risk_level"),
                workingDirectory=payload.get("working_directory"),
                expectedOutput=payload.get("expected_output"),
            )
            return

        if kind == "loop_replan_pending_approval":
            runtime.mark_replan_pending_approval(
                {
                    "step_id": event.step_id,
                    "locked_command": payload.get("locked_command"),
                    "proposed_command": payload.get("proposed_command"),
                }
            )
            self.runtime_manager.append_event(runtime.runtime_id, "task_waiting_input")
            return

        if kind == "loop_approval_granted":
            self.runtime_manager.append_event(
                runtime.runtime_id,
                "approval_resolved",
                approved=True,
                stepId=event.step_id,
            )
            if event.step_id:
                runtime.mark_executing(event.step_id)
            return

        if kind == "loop_approval_rejected":
            if event.step_id:
                runtime.mark_waiting_approval(event.step_id)
            self.runtime_manager.append_event(
                runtime.runtime_id,
                "approval_resolved",
                approved=False,
                stepId=event.step_id,
            )
            return

        if kind == "loop_execution_started":
            self.runtime_manager.append_event(
                runtime.runtime_id,
                "execution_started",
                stepId=event.step_id,
                commandId=payload.get("command_id"),
                terminalId=payload.get("terminal_id"),
                command=payload.get("command"),
                title=payload.get("title"),
            )
            return

        if kind == "loop_execution_output":
            self.runtime_manager.append_event(
                runtime.runtime_id,
                "execution_output",
                stepId=event.step_id,
                commandId=payload.get("command_id"),
                terminalId=payload.get("terminal_id"),
                stream=payload.get("stream", "stdout"),
                text=payload.get("text", ""),
            )
            if state is not None:
                runtime.update_last_output_excerpt(state.last_output_excerpt or "")
            return

        if kind == "loop_execution_completed":
            self.runtime_manager.append_event(
                runtime.runtime_id,
                "execution_completed",
                stepId=event.step_id,
                commandId=payload.get("command_id"),
                terminalId=payload.get("terminal_id"),
                exitCode=payload.get("exit_code"),
                completed=payload.get("completed"),
                success=payload.get("success"),
            )
            return

        if kind == "loop_completed":
            summary = payload.get("summary", "")
            runtime.mark_completed(summary)
            self.runtime_manager.append_event(runtime.runtime_id, "task_completed", summary=summary)
            return

        if kind == "loop_failed":
            error = payload.get("error", "")
            runtime.mark_failed(error)
            self.runtime_manager.append_event(runtime.runtime_id, "task_failed", error=error)
            return

    def _to_runtime_step(self, step: LoopRuntimeStep) -> RuntimeStepState:
        return RuntimeStepState(
            step_id=step.step_id,
            title=step.title,
            command=step.command,
            reason=step.reason,
            risk_level=step.risk_level,
            working_directory=step.working_directory,
            expected_output=step.expected_output,
            status=step.status,  # type: ignore[arg-type]
            output=step.output,
            exit_code=step.exit_code,
        )
