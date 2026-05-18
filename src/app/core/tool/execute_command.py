from __future__ import annotations

import logging
from collections.abc import Iterator
from typing import Any, Protocol

logger = logging.getLogger(__name__)

from app.core.loop.loop_events import (
    LoopEvent,
    emit_failed,
)
from app.core.loop.loop_state import LoopState
from app.core.loop.message_manager import MessageManager
from app.core.tool.handler import ToolDisplayMetadata
from app.core.tool.schema import LLMToolDefinition
from app.core.approval import ApprovalContext
from app.core.connectors.execution import ExecutionContext
from app.services.approval_service import get_approval_service


class TerminalSessionResolver(Protocol):
    def get_session(self, terminal_id: str) -> Any | None: ...

    def acquire_terminal_slot(self, runtime_id: str, terminal_id: str) -> bool: ...

    def release_terminal_slot(self, runtime_id: str, terminal_id: str) -> None: ...


class ExecuteCommandHandler:
    def __init__(self, terminal: TerminalSessionResolver) -> None:
        self._terminal = terminal

    @property
    def definition(self) -> LLMToolDefinition:
        return LLMToolDefinition(
            name="execute_command",
            description="Execute terminal command. The system will automatically determine whether to allow, reject, or require user approval based on the approval policy in settings.json.",
            input_schema={
                "type": "object",
                "properties": {
                    "command": {"type": "string", "description": "The command to execute, must be specified."},
                    "asset_id": {"type": "integer", "description": "Target asset ID, if not specified, the current terminal will be used"},
                    "working_directory": {"type": "string", "description": "Working directory (optional)"},
                },
                "required": ["command"],
            },
        )

    def needs_approval(self, args: dict[str, Any]) -> tuple[str, str]:
        command = str(args.get("command", "")).strip()
        context = ApprovalContext(
            asset_type=str(args.get("asset_type", "") or ""),
            shell_type=str(args.get("shell_type", "") or ""),
            profile=str(args.get("execution_profile", "posix-shell") or "posix-shell"),
            vendor=str(args.get("device_vendor", "") or "") or None,
        )
        action, reason = get_approval_service().check_command(command, context)
        return action, reason

    def display_metadata(self, args: dict[str, Any]) -> ToolDisplayMetadata:
        command = str(args.get("command", "")).strip()
        return ToolDisplayMetadata(
            description="Execute terminal command.",
            display_text=command or "Execute terminal command",
            extra={"kind": "command"},
        )

    def execute(self, *, state: LoopState, step_id: str, args: dict[str, Any], manager: MessageManager | None = None) -> Iterator[LoopEvent]:
        ctx = state.context
        terminal_id = ctx.terminal_id
        
        step = state.get_step(step_id)
        if step is None:
            return False, "Step not found"

        if terminal_id is None:
            error = "Terminal not connected, cannot execute."
            if manager:
                yield from manager.update(text=f"\nError: {error}")
            return False, ""

        session_manager = self._terminal.get_session(terminal_id)
        if session_manager is None:
            error = "Terminal session does not exist, cannot execute command."
            if manager:
                yield from manager.update(text=f"\nError: {error}")
            return False, ""

        if not self._terminal.acquire_terminal_slot(ctx.runtime_id, terminal_id):
            error = "currently executing command, please wait for it to finish"
            if manager:
                yield from manager.update(text=f"\nError: {error}")
            return False, ""

        try:
            command = str(args.get("command", "")).strip()
            execution_id = session_manager.start_execution(
                command,
                ExecutionContext(working_directory=step.working_directory),
            )
            execution = session_manager.get_execution_result(execution_id)
            
            step.output = execution.output
            step.exit_code = execution.exit_code
            state.last_output_excerpt = execution.output[-4000:] if execution.output else ""

            if execution.output and manager:
                yield from manager.update(tool_output=execution.output)

            success = execution.success and not execution.needs_attention
            return success, execution.output
        except Exception as exc:
            logger.exception("Command execution exception runtime_id=%s, command_id=%s", ctx.runtime_id, step.step_id)
            error = f"Command execution exception: {exc}"
            if manager:
                yield from manager.update(text=f"\nError: {error}")
            return False, ""
        finally:
            self._terminal.release_terminal_slot(ctx.runtime_id, terminal_id)
