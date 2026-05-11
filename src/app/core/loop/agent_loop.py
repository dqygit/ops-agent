"""简化后的 Agent Loop。

仅保留：
- LLM tool calling
- execute_command 工具调用
- 命令审批策略检查
- 用户审批恢复执行
- 终端执行事件输出
"""

from __future__ import annotations

import json
import uuid
from collections.abc import Iterator
from typing import Any, Protocol

from app.core.llm.base import LLMCompletionRequest, LLMCompletionResponse, LLMMessage
from app.core.llm.factory import build_llm_provider
from app.core.loop.loop_events import (
    LoopEvent,
    emit_approval_granted,
    emit_approval_rejected,
    emit_approval_required,
    emit_completed,
    emit_delta,
    emit_execution_completed,
    emit_execution_output,
    emit_execution_started,
    emit_failed,
    emit_plan_updated,
)
from app.core.loop.loop_state import LoopRuntimeStep, LoopState
from app.core.tool.schema import LLMToolDefinition
from app.services.approval_service import get_approval_service


class TerminalSessionResolver(Protocol):
    def get_session(self, terminal_id: str) -> Any | None: ...

    def acquire_terminal_slot(self, runtime_id: str, terminal_id: str) -> bool: ...

    def release_terminal_slot(self, runtime_id: str, terminal_id: str) -> None: ...


EventCallback = Any


class AgentLoop:
    def __init__(self, *, terminal: TerminalSessionResolver) -> None:
        self._terminal = terminal

    def run(self, state: LoopState) -> Iterator[LoopEvent]:
        if state.context.mode == "plan":
            yield from self._run_plan_mode(state)
            return
        yield from self._tool_calling_loop(state)

    def resume_with_approval(self, state: LoopState, *, approved: bool) -> Iterator[LoopEvent]:
        if state.phase != "approving":
            return

        current_step = state.get_current_step()
        if current_step is None:
            return

        if not approved:
            current_step.status = "failed"
            yield emit_approval_rejected(runtime_id=state.context.runtime_id, step_id=current_step.step_id)
            state.messages.append(
                LLMMessage(
                    role="tool",
                    content="Command execution rejected by user.",
                    tool_call_id=state.pending_tool_call_id,
                    name=state.pending_tool_name,
                )
            )
            state.pending_tool_call_id = None
            state.pending_tool_name = None
            state.pending_tool_args = None
            yield emit_plan_updated(runtime_id=state.context.runtime_id, plan_payload=self._snapshot_plan(state))
            yield from self._tool_calling_loop(state)
            return

        yield emit_approval_granted(runtime_id=state.context.runtime_id, step_id=current_step.step_id)
        current_step.status = "running"
        state.phase = "executing"
        yield emit_plan_updated(runtime_id=state.context.runtime_id, plan_payload=self._snapshot_plan(state))

        ok, output = yield from self._execute_step(state, current_step)
        current_step.status = "completed" if ok else "failed"
        state.messages.append(
            LLMMessage(
                role="tool",
                content=output if ok else f"Command Failed: {output}",
                tool_call_id=state.pending_tool_call_id,
                name=state.pending_tool_name,
            )
        )
        state.pending_tool_call_id = None
        state.pending_tool_name = None
        state.pending_tool_args = None
        yield emit_plan_updated(runtime_id=state.context.runtime_id, plan_payload=self._snapshot_plan(state))
        if state.context.mode == "plan":
            if ok:
                yield from self._run_plan_mode(state, continue_existing=True)
                return
            state.phase = "failed"
            state.error_message = output
            yield emit_failed(runtime_id=state.context.runtime_id, error=output or "计划步骤执行失败。")
            return
        yield from self._tool_calling_loop(state)

    def _run_plan_mode(self, state: LoopState, *, continue_existing: bool = False) -> Iterator[LoopEvent]:
        if not continue_existing and not state.steps:
            yield from self._generate_plan(state)
            if state.phase == "failed":
                return

        while state.cursor < len(state.steps):
            step = state.get_current_step()
            if step is None:
                break

            if step.status == "completed":
                state.cursor += 1
                continue

            step.status = "running"
            state.phase = "executing"
            state.messages = self._build_step_messages(state, step)
            yield emit_plan_updated(runtime_id=state.context.runtime_id, plan_payload=self._snapshot_plan(state))

            paused, _, summary = yield from self._tool_calling_loop(state, plan_step=step, finalize_on_complete=False)
            if paused:
                return

            step.status = "completed"
            if summary:
                step.output = summary
            state.messages = []
            yield emit_plan_updated(runtime_id=state.context.runtime_id, plan_payload=self._snapshot_plan(state))
            state.cursor += 1

        state.phase = "completed"
        state.summary = "计划任务已执行完毕。"
        yield emit_completed(runtime_id=state.context.runtime_id, summary=state.summary)

    def _generate_plan(self, state: LoopState) -> Iterator[LoopEvent]:
        provider = build_llm_provider(state.context.model_config)
        ctx = state.context
        request = LLMCompletionRequest(
            messages=[
                LLMMessage(
                    role="system",
                    content=(
                        "你是一个运维任务规划器。请根据用户目标生成可执行的任务计划。"
                        "返回 JSON 对象，格式为 {\"steps\": [...]}。"
                        "每个 step 包含 title、reason、command、working_directory、expected_output、risk_level。"
                        "command 必须是单步可执行命令。不要输出 JSON 以外的内容。"
                    ),
                ),
                LLMMessage(
                    role="user",
                    content=(
                        f"操作系统类型: {ctx.os_type}\n"
                        f"当前主机信息: {ctx.asset_summary}\n"
                        f"Shell: {ctx.shell_type}\n"
                        f"用户任务: {ctx.user_prompt}"
                    ),
                ),
            ],
            json_mode=True,
        )
        try:
            response = provider.complete(config=ctx.model_config, request=request)
            payload = json.loads(response.text or "{}")
            raw_steps = payload.get("steps") or []
            if not isinstance(raw_steps, list) or not raw_steps:
                raise ValueError("planner returned empty steps")

            state.steps = []
            state.cursor = 0
            for index, item in enumerate(raw_steps, start=1):
                data = item if isinstance(item, dict) else {}
                command = str(data.get("command", "")).strip()
                state.steps.append(
                    LoopRuntimeStep(
                        step_id=f"step-{uuid.uuid4().hex[:8]}",
                        title=str(data.get("title") or f"步骤 {index}"),
                        command=command,
                        reason=str(data.get("reason") or "执行计划步骤"),
                        risk_level=str(data.get("risk_level") or "low"),
                        working_directory=str(data.get("working_directory") or "") or None,
                        expected_output=str(data.get("expected_output") or "") or None,
                        status="pending",
                    )
                )

            state.phase = "planning"
            yield emit_plan_updated(runtime_id=ctx.runtime_id, plan_payload=self._snapshot_plan(state))
        except Exception as exc:
            error = f"任务规划失败: {exc}"
            state.phase = "failed"
            state.error_message = error
            yield emit_failed(runtime_id=ctx.runtime_id, error=error)

    def _build_step_messages(self, state: LoopState, step: LoopRuntimeStep) -> list[LLMMessage]:
        ctx = state.context
        system_msg = (
            f"操作系统类型: {ctx.os_type}\n"
            f"当前主机信息: {ctx.asset_summary}\n"
            f"Shell: {ctx.shell_type}\n\n"
            "你是一个执行单个计划步骤的运维助手。"
            "你只能通过 execute_command 工具执行操作。"
            "优先完成当前步骤，完成后直接给出简短结果总结。"
        )
        user_msg = (
            f"原始任务: {ctx.user_prompt}\n"
            f"当前步骤标题: {step.title}\n"
            f"当前步骤原因: {step.reason}\n"
            f"建议命令: {step.command or '无'}\n"
            f"建议工作目录: {step.working_directory or '未指定'}\n"
            f"期望输出: {step.expected_output or '未指定'}\n"
            "请围绕当前步骤执行，必要时可以调整命令，但不要偏离该步骤目标。"
        )
        return [LLMMessage(role="system", content=system_msg), LLMMessage(role="user", content=user_msg)]

    def _tool_calling_loop(
        self,
        state: LoopState,
        *,
        plan_step: LoopRuntimeStep | None = None,
        finalize_on_complete: bool = True,
    ) -> Iterator[LoopEvent]:
        provider = build_llm_provider(state.context.model_config)
        ctx = state.context

        tools = [
            LLMToolDefinition(
                name="execute_command",
                description="执行终端命令。系统会自动根据 settings.json 中的审批策略判断是允许、拒绝还是要求用户审批。",
                input_schema={
                    "type": "object",
                    "properties": {
                        "command": {"type": "string", "description": "要执行的终端命令"},
                        "working_directory": {"type": "string", "description": "工作目录（可选）"},
                    },
                    "required": ["command"],
                },
            )
        ]

        if not state.messages:
            mode_instruction = (
                "你是一个谨慎的运维助手。你只能通过 execute_command 工具执行操作。系统会自动根据审批策略判断命令是否可直接执行。"
                if ctx.mode == "plan"
                else "你是一个自主运维助手。你只能通过 execute_command 工具执行操作。系统会自动根据审批策略判断命令是否可直接执行。"
            )
            system_msg = (
                f"操作系统类型: {ctx.os_type}\n"
                f"当前主机信息: {ctx.asset_summary}\n"
                f"Shell: {ctx.shell_type}\n\n"
                f"规则: {mode_instruction}\n"
                "当需要检查环境或完成任务时，直接调用 execute_command。"
            )
            state.messages.append(LLMMessage(role="system", content=system_msg))
            state.messages.append(LLMMessage(role="user", content=ctx.user_prompt))

        while True:
            response_text_parts: list[str] = []
            response_tool_calls = []
            finish_reason: str | None = None
            message_id = f"msg-{uuid.uuid4()}"

            for chunk in provider.stream_complete(
                config=ctx.model_config,
                request=LLMCompletionRequest(messages=state.messages, tools=tools, json_mode=False),
            ):
                if chunk.delta:
                    response_text_parts.append(chunk.delta)
                    yield emit_delta(
                        runtime_id=ctx.runtime_id,
                        message_id=message_id,
                        stage="assistant",
                        text=chunk.delta,
                    )
                if chunk.tool_arguments_delta:
                    # Do not emit raw json to the UI text stream
                    pass
                if chunk.tool_calls:
                    response_tool_calls = chunk.tool_calls
                if chunk.finish_reason:
                    finish_reason = chunk.finish_reason

            response = LLMCompletionResponse(
                text="".join(response_text_parts),
                tool_calls=response_tool_calls,
                finish_reason=finish_reason,
            )

            if response.text or response.tool_calls:
                state.messages.append(
                    LLMMessage(
                        role="assistant",
                        content=response.text,
                        tool_calls=response.tool_calls,
                    )
                )

            if not response.tool_calls:
                summary = response.text or "任务已执行完毕。"
                if finalize_on_complete:
                    state.phase = "completed"
                    state.summary = summary
                    yield emit_completed(runtime_id=ctx.runtime_id, summary=summary)
                return False, True, summary

            for tool_call in response.tool_calls:
                if tool_call.name != "execute_command":
                    state.messages.append(
                        LLMMessage(
                            role="tool",
                            content=f"Unsupported tool: {tool_call.name}",
                            tool_call_id=tool_call.id,
                            name=tool_call.name,
                        )
                    )
                    continue

                args = tool_call.arguments
                command = str(args.get("command", "")).strip()
                working_directory = args.get("working_directory")
                if not command:
                    state.messages.append(
                        LLMMessage(
                            role="tool",
                            content="Missing required field: command",
                            tool_call_id=tool_call.id,
                            name=tool_call.name,
                        )
                    )
                    continue

                if plan_step is None:
                    step = LoopRuntimeStep(
                        step_id=f"step-{uuid.uuid4().hex[:8]}",
                        title=command,
                        command=command,
                        reason="LLM requested command execution",
                        risk_level="low",
                        working_directory=str(working_directory) if working_directory else None,
                        status="pending",
                    )
                    state.steps.append(step)
                    state.cursor = len(state.steps) - 1
                    yield emit_plan_updated(runtime_id=ctx.runtime_id, plan_payload=self._snapshot_plan(state))
                else:
                    step = plan_step
                    step.command = command
                    step.working_directory = str(working_directory) if working_directory else None
                    yield emit_plan_updated(runtime_id=ctx.runtime_id, plan_payload=self._snapshot_plan(state))

                action, reason = get_approval_service().check_command(command)
                if action == "deny":
                    step.status = "failed"
                    state.messages.append(
                        LLMMessage(
                            role="tool",
                            content=f"Command denied: {reason}",
                            tool_call_id=tool_call.id,
                            name=tool_call.name,
                        )
                    )
                    yield emit_plan_updated(runtime_id=ctx.runtime_id, plan_payload=self._snapshot_plan(state))
                    continue

                if action == "ask":
                    step.reason = reason
                    step.risk_level = "high"
                    state.phase = "approving"
                    state.pending_tool_call_id = tool_call.id
                    state.pending_tool_name = tool_call.name
                    state.pending_tool_args = args
                    yield emit_plan_updated(runtime_id=ctx.runtime_id, plan_payload=self._snapshot_plan(state))
                    yield emit_approval_required(
                        runtime_id=ctx.runtime_id,
                        step_id=step.step_id,
                        step_index=state.cursor,
                        command=step.command,
                        title="命令需要审批",
                        reason=reason,
                        risk_level="high",
                        working_directory=step.working_directory,
                        expected_output=None,
                    )
                    return True, None, ""

                step.status = "running"
                state.phase = "executing"
                yield emit_plan_updated(runtime_id=ctx.runtime_id, plan_payload=self._snapshot_plan(state))
                ok, output = yield from self._execute_step(state, step)
                step.status = "completed" if ok else "failed"
                state.messages.append(
                    LLMMessage(
                        role="tool",
                        content=output if ok else f"Command Failed: {output}",
                        tool_call_id=tool_call.id,
                        name=tool_call.name,
                    )
                )
                yield emit_plan_updated(runtime_id=ctx.runtime_id, plan_payload=self._snapshot_plan(state))

        return False, True, ""

    def _execute_step(self, state: LoopState, step: LoopRuntimeStep) -> Iterator[LoopEvent]:
        ctx = state.context
        terminal_id = ctx.terminal_id
        if terminal_id is None:
            error = "终端未连接，无法执行。"
            state.phase = "failed"
            state.error_message = error
            yield emit_failed(runtime_id=ctx.runtime_id, error=error)
            return False, ""

        session_manager = self._terminal.get_session(terminal_id)
        if session_manager is None:
            error = "终端会话不存在，无法执行命令。"
            state.phase = "failed"
            state.error_message = error
            yield emit_failed(runtime_id=ctx.runtime_id, error=error)
            return False, ""

        if not self._terminal.acquire_terminal_slot(ctx.runtime_id, terminal_id):
            error = "当前终端已有其他任务在执行，请稍后再试。"
            state.phase = "failed"
            state.error_message = error
            yield emit_failed(runtime_id=ctx.runtime_id, error=error)
            return False, ""

        try:
            execution_id = session_manager.start_execution(
                step.command,
                type("ExecutionContext", (), {"working_directory": step.working_directory})(),
            )
            execution = session_manager.get_execution_result(execution_id)
            command_id = execution.execution_id or step.step_id

            yield emit_execution_started(
                runtime_id=ctx.runtime_id,
                step_id=step.step_id,
                step_index=state.cursor,
                command_id=command_id,
                terminal_id=terminal_id,
                command=step.command,
                title=step.title,
            )

            step.output = execution.output
            step.exit_code = execution.exit_code
            state.last_output_excerpt = execution.output[-4000:] if execution.output else ""

            if execution.output:
                yield emit_execution_output(
                    runtime_id=ctx.runtime_id,
                    step_id=step.step_id,
                    command_id=command_id,
                    terminal_id=terminal_id,
                    text=execution.output,
                    stream="stdout",
                )

            success = execution.completed and execution.exit_code in {None, 0}
            yield emit_execution_completed(
                runtime_id=ctx.runtime_id,
                step_id=step.step_id,
                step_index=state.cursor,
                command_id=command_id,
                terminal_id=terminal_id,
                exit_code=execution.exit_code,
                completed=execution.completed,
                success=success,
            )
            return success, execution.output
        except Exception as exc:
            error = f"命令执行异常: {exc}"
            state.phase = "failed"
            state.error_message = error
            yield emit_failed(runtime_id=ctx.runtime_id, error=error)
            return False, ""
        finally:
            self._terminal.release_terminal_slot(ctx.runtime_id, terminal_id)

    def _snapshot_plan(self, state: LoopState) -> dict[str, Any]:
        return {
            "id": f"plan-{state.context.runtime_id}-v{len(state.steps)}",
            "kind": "plan",
            "planId": f"runtime-{state.context.runtime_id}",
            "title": "Task Plan",
            "loading": False,
            "version": len(state.steps),
            "isLatest": True,
            "updated": bool(state.steps),
            "steps": [
                {
                    "id": step.step_id,
                    "title": step.title,
                    "summary": step.reason,
                    "status": step.status,
                }
                for step in state.steps
            ],
            "runtimeId": state.context.runtime_id,
            "mode": state.context.mode,
            "lockedPlan": False,
        }
