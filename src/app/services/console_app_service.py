from __future__ import annotations

import logging
from collections.abc import Iterator
from types import SimpleNamespace
from typing import Any

from sqlmodel import Session

from app.core.loop.loop_state import LoopContext
from app.core.loop.runtime_manager import LoopRuntimeManager, new_runtime_id
from app.core.tool.execute_command import ExecuteCommandHandler
from app.db.repositories.assets import get_asset
from app.db.repositories.models import get_default_model_config
from app.services.approval_service import get_approval_service
from app.services.model_service import ModelService
from app.services.terminal_service import TerminalService


logger = logging.getLogger(__name__)


class _TerminalSessionAdapter:
    def __init__(self, terminal_service: TerminalService, runtime_manager: LoopRuntimeManager) -> None:
        self._terminal_service = terminal_service
        self._runtime_manager = runtime_manager

    def get_session(self, terminal_id: str) -> Any | None:
        return self._terminal_service.get_session(terminal_id)

    def acquire_terminal_slot(self, runtime_id: str, terminal_id: str) -> bool:
        return self._runtime_manager.acquire_terminal_slot(runtime_id, terminal_id)

    def release_terminal_slot(self, runtime_id: str, terminal_id: str) -> None:
        self._runtime_manager.release_terminal_slot(runtime_id, terminal_id)


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

    def stream_approve(self, *, session: Session, runtime_id: str, approved: bool, approval_token: str | None = None, allow_prefix: str | None = None) -> Iterator[dict]:
        return self._app_service.stream_approve(
            session=session,
            runtime_id=runtime_id,
            approved=approved,
            approval_token=approval_token,
            allow_prefix=allow_prefix,
            terminal_service=self._terminal_service,
        )

    def stream_plan_approval(self, *, runtime_id: str) -> Iterator[dict]:
        return self._app_service.stream_plan_approval(
            runtime_id=runtime_id,
            terminal_service=self._terminal_service,
        )

class ConsoleAppService:
    def __init__(
        self,
        *,
        model_service: ModelService | None = None,
    ) -> None:
        self._model_service = model_service or ModelService()
        self.runtime_manager = LoopRuntimeManager(
            tools_factory=lambda ts: [
                ExecuteCommandHandler(_TerminalSessionAdapter(ts, self.runtime_manager)),
            ]
        )

    def build_orchestrator(self, terminal_service: TerminalService) -> TaskOrchestrator:
        return TaskOrchestrator(self, terminal_service)

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
        import time as _time
        t0 = _time.monotonic()
        asset = self._resolve_asset(session, asset_id)
        t1 = _time.monotonic()
        model_config = self._resolve_model_config(session, model_name)
        t2 = _time.monotonic()
        asset_summary = (
            f"asset={getattr(asset, 'name', '')}, type={getattr(asset, 'asset_type', '')}, "
            f"host={getattr(asset, 'host', '')}, user={getattr(asset, 'username', '')}"
        )
        shell_type = self._resolve_shell_type(terminal_service, terminal_id)
        os_type = self._infer_os_type(shell_type)

        # Load conversation history for multi-turn context (Roo Code style)
        conversation_history = self._build_conversation_history(conversation_id)

        runtime_id = new_runtime_id()
        context = LoopContext(
            runtime_id=runtime_id,
            conversation_id=conversation_id,
            asset_id=asset_id,
            terminal_id=terminal_id,
            asset_summary=asset_summary,
            shell_type=shell_type,
            os_type=os_type,
            user_prompt=prompt,
            model_config=model_config,
            mode=mode,
            conversation_history=conversation_history,
        )
        
        self.runtime_manager.create_runtime(
            conversation_id=conversation_id,
            asset_id=asset_id,
            terminal_id=terminal_id,
            context=context,
        )
        t3 = _time.monotonic()
        logger.warning(
            "stream_run setup: asset=%.3fs model=%.3fs runtime=%.3fs history_msgs=%d total=%.3fs",
            t1 - t0, t2 - t1, t3 - t2, len(conversation_history), t3 - t0,
        )

        try:
            events = self.runtime_manager.run(runtime_id=runtime_id, terminal_service=terminal_service)
            for event in events:
                yield event
        except Exception as exc:
            logger.exception("stream_run failed conversation_id=%s runtime_id=%s", conversation_id, runtime_id)
            yield {
                "id": f"evt-error-{runtime_id}",
                "kind": "error",
                "runtimeId": runtime_id,
                "sequence": -1,
                "ts": "",
                "text": str(exc),
                "recoverable": True,
            }

    def stream_approve(
        self,
        *,
        session: Session,
        runtime_id: str,
        approved: bool,
        approval_token: str | None,
        allow_prefix: str | None,
        terminal_service: TerminalService,
    ) -> Iterator[dict]:
        _ = session
        runtime = self.runtime_manager.get_runtime(runtime_id)
        if runtime is None:
            yield {
                "id": f"evt-error-{runtime_id}",
                "kind": "error",
                "runtimeId": runtime_id,
                "sequence": -1,
                "ts": "",
                "text": "Runtime not found.",
                "recoverable": False,
            }
            return

        try:
            if approved and allow_prefix:
                get_approval_service().add_allow_prefix(allow_prefix)
            events = self.runtime_manager.resume(
                runtime_id=runtime_id,
                approved=approved,
                approval_token=approval_token,
                terminal_service=terminal_service,
            )
            for event in events:
                yield event
        except Exception as exc:
            logger.exception("stream_approve failed runtime_id=%s", runtime_id)
            yield {
                "id": f"evt-error-{runtime_id}",
                "kind": "error",
                "runtimeId": runtime_id,
                "sequence": -1,
                "ts": "",
                "text": str(exc),
                "recoverable": True,
            }

    def update_plan(self, *, runtime_id: str, steps: list[dict]) -> dict:
        return self.runtime_manager.update_plan(runtime_id=runtime_id, steps=steps)

    def stream_plan_approval(self, *, runtime_id: str, terminal_service: TerminalService) -> Iterator[dict]:
        try:
            events = self.runtime_manager.approve_plan(runtime_id=runtime_id, terminal_service=terminal_service)
            for event in events:
                yield event
        except Exception as exc:
            logger.exception("stream_plan_approval failed runtime_id=%s", runtime_id)
            yield {
                "id": f"evt-error-{runtime_id}",
                "kind": "error",
                "runtimeId": runtime_id,
                "sequence": -1,
                "ts": "",
                "text": str(exc),
                "recoverable": True,
            }

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

    def _build_conversation_history(self, conversation_id: str) -> list:
        """Load persisted conversation events and convert to LLMMessage list.

        Follows the Roo Code pattern: each previous turn's user message and
        assistant response are included so the LLM has full multi-turn context.
        Tool calls/results from prior turns are condensed into a single
        assistant message summarizing what was done.
        """
        from app.core.llm.types import LLMMessage

        if not conversation_id or conversation_id == "console":
            return []

        try:
            from app.api.conversations import get_conversation_service
            service = get_conversation_service()
            detail = service.get_conversation(conversation_id)
        except (FileNotFoundError, Exception):
            return []

        events = detail.events or []
        if not events:
            return []

        messages: list[LLMMessage] = []

        for event in events:
            kind = event.get("kind", "")
            event_type = event.get("type", "")

            # User messages
            if kind == "user":
                text = event.get("text", "").strip()
                if text:
                    messages.append(LLMMessage(role="user", content=text))
                continue

            # AgentMessage snapshots (from the new protocol)
            if kind == "message" and event_type == "say":
                say_type = event.get("say", "")
                partial = event.get("partial", False)
                if partial:
                    continue  # Skip intermediate streaming snapshots

                if say_type == "text":
                    text = event.get("text", "").strip()
                    if text:
                        messages.append(LLMMessage(role="assistant", content=text))
                elif say_type == "tool_use":
                    # Summarize tool execution as assistant context
                    tool_call = event.get("toolCall") or event.get("tool_call") or {}
                    tool_output = event.get("toolOutput") or event.get("tool_output") or ""
                    exit_code = event.get("exitCode") if event.get("exitCode") is not None else event.get("exit_code")
                    command = tool_call.get("command", "") or tool_call.get("name", "")
                    summary_parts = []
                    if command:
                        summary_parts.append(f"[Executed: {command}]")
                    if tool_output:
                        # Truncate long output to avoid token bloat
                        truncated = tool_output[:2000] + ("..." if len(tool_output) > 2000 else "")
                        summary_parts.append(f"Output:\n{truncated}")
                    if exit_code is not None:
                        summary_parts.append(f"Exit code: {exit_code}")
                    if summary_parts:
                        messages.append(LLMMessage(role="assistant", content="\n".join(summary_parts)))
                elif say_type == "error":
                    text = event.get("text", "").strip()
                    if text:
                        messages.append(LLMMessage(role="assistant", content=f"[Error: {text}]"))
                continue

            if kind == "plan":
                title = event.get("title", "Task Plan").strip() or "Task Plan"
                steps = event.get("steps") or []
                if isinstance(steps, list) and steps:
                    step_lines = []
                    for index, step in enumerate(steps, start=1):
                        if not isinstance(step, dict):
                            continue
                        step_title = str(step.get("title") or f"Step {index}").strip()
                        command = str(step.get("command") or "").strip()
                        reason = str(step.get("summary") or step.get("reason") or "").strip()
                        line = f"{index}. {step_title}"
                        if command:
                            line += f" | Command: {command}"
                        if reason:
                            line += f" | Reason: {reason}"
                        step_lines.append(line)
                    if step_lines:
                        messages.append(LLMMessage(role="assistant", content=f"{title}\n" + "\n".join(step_lines)))
                continue

            # Legacy 'final' events (from older protocol)
            if kind == "final":
                text = event.get("text", "").strip()
                if text:
                    messages.append(LLMMessage(role="assistant", content=text))
                continue

            # Legacy 'delta' events — only if they have accumulated text
            if kind == "delta":
                text = event.get("text", "").strip()
                if text:
                    messages.append(LLMMessage(role="assistant", content=text))
                continue

        # Deduplicate consecutive messages with same role (merge if needed)
        if not messages:
            return []

        # Remove the last user message — it's the current prompt, already handled by agent_loop
        # The current user event was just persisted by console.py before stream_run
        if messages and messages[-1].role == "user":
            messages = messages[:-1]

        logger.info("Built conversation history: %d messages from %d events", len(messages), len(events))
        return messages
