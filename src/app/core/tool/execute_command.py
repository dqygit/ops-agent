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
            description="执行终端命令。系统会自动根据 settings.json 中的审批策略判断是允许、拒绝还是要求用户审批。",
            input_schema={
                "type": "object",
                "properties": {
                    "command": {"type": "string", "description": "要执行的终端命令"},
                    "asset_id": {"type": "integer", "description": "目标资产 ID，不指定则使用当前终端"},
                    "working_directory": {"type": "string", "description": "工作目录（可选）"},
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
            error = "终端未连接，无法执行。"
            if manager:
                yield from manager.update(text=f"\nError: {error}")
            return False, ""

        session_manager = self._terminal.get_session(terminal_id)
        if session_manager is None:
            error = "终端会话不存在，无法执行命令。"
            if manager:
                yield from manager.update(text=f"\nError: {error}")
            return False, ""

        if not self._terminal.acquire_terminal_slot(ctx.runtime_id, terminal_id):
            error = "当前终端已有其他任务在执行，请稍后再试。"
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
            logger.exception("命令执行异常 runtime_id=%s, command_id=%s", ctx.runtime_id, step.step_id)
            error = f"命令执行异常: {exc}"
            if manager:
                yield from manager.update(text=f"\nError: {error}")
            return False, ""
        finally:
            self._terminal.release_terminal_slot(ctx.runtime_id, terminal_id)
