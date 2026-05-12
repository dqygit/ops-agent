"""简化后的 Agent Loop。

仅保留：
- LLM tool calling (基于 ToolHandler)
- 命令审批策略检查
- 用户审批恢复执行
"""

from __future__ import annotations

import json
import logging
import uuid
from collections.abc import Iterator
from typing import Any

logger = logging.getLogger(__name__)

from app.core.llm.types import LLMCompletionRequest, LLMCompletionResponse, LLMMessage
from app.core.llm.factory import build_llm_provider
from app.core.loop.loop_events import (
    AgentMessage,
    LoopEvent,
    emit_completed,
    emit_failed,
    emit_message_update,
)
from app.core.loop.loop_state import LoopRuntimeStep, LoopState
from app.core.loop.message_manager import MessageManager
from app.core.tool.handler import ToolHandler


EventCallback = Any


class AgentLoop:
    def __init__(self, *, tools: list[ToolHandler]) -> None:
        self._tools = {t.definition.name: t for t in tools}

    def run(self, state: LoopState) -> Iterator[LoopEvent]:
        manager = MessageManager(runtime_id=state.context.runtime_id)
        if state.context.mode == "plan":
            yield from self._run_plan_mode(state, manager=manager)
            return
        yield from self._tool_calling_loop(state, manager=manager)

    def resume_with_approval(self, state: LoopState, *, approved: bool) -> Iterator[LoopEvent]:
        if state.phase != "approving":
            return

        manager = MessageManager(runtime_id=state.context.runtime_id)
        current_step = state.get_current_step()
        if current_step is None:
            return

        # Reuse the ask message's ID so the frontend replaces the card in-place
        reuse_id = state.pending_message_id

        if not approved:
            current_step.status = "failed"
            if reuse_id:
                yield from manager.resume_message(message_id=reuse_id, message_type="say", say_type="error")
            else:
                yield from manager.begin_message(message_type="say", say_type="error")
            yield from manager.finalize(text="Command execution rejected by user.")
            
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
            state.pending_message_id = None
            yield from self._tool_calling_loop(state, manager=manager)
            return

        current_step.status = "running"
        state.phase = "executing"

        tool_name = state.pending_tool_name
        args = state.pending_tool_args or {}
        handler = self._tools.get(tool_name)
        
        # Resume the existing ask message as a say/tool_use (same ID, card replaces in-place)
        if reuse_id:
            yield from manager.resume_message(message_id=reuse_id, message_type="say", say_type="tool_use")
        else:
            yield from manager.begin_message(message_type="say", say_type="tool_use")
        yield from manager.update(tool_call={"id": state.pending_tool_call_id, "name": tool_name, "args": args})

        if handler is None:
            ok, output = False, f"Unsupported tool: {tool_name}"
        else:
            ok, output = yield from handler.execute(state=state, step_id=current_step.step_id, args=args, manager=manager)

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
        state.pending_message_id = None
        yield from manager.finalize(exit_code=0 if ok else 1)
        
        if state.context.mode == "plan":
            if ok:
                yield from self._run_plan_mode(state, manager=manager, continue_existing=True)
                return
            state.phase = "failed"
            state.error_message = output
            yield emit_failed(runtime_id=state.context.runtime_id, error=output or "Failed to execute plan step.")
            return
        yield from self._tool_calling_loop(state, manager=manager)

    def _run_plan_mode(self, state: LoopState, *, manager: MessageManager, continue_existing: bool = False) -> Iterator[LoopEvent]:
        if not continue_existing and not state.steps:
            yield from self._generate_plan(state, manager=manager)
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

            paused, _, summary = yield from self._tool_calling_loop(state, manager=manager, plan_step=step, finalize_on_complete=False)
            if paused:
                return

            step.status = "completed"
            if summary:
                step.output = summary
            state.messages = []
            state.cursor += 1

        state.phase = "completed"
        state.summary = "Plan execution completed."
        yield emit_completed(runtime_id=state.context.runtime_id, summary=state.summary)

    def _generate_plan(self, state: LoopState, *, manager: MessageManager) -> Iterator[LoopEvent]:
        provider = build_llm_provider(state.context.model_config)
        ctx = state.context
        
        yield from manager.begin_message(message_type="say", say_type="text")
        yield from manager.update(text="Generating execution plan...")

        request = LLMCompletionRequest(
            messages=[
                LLMMessage(
                    role="system",
                    content=(
                        "You are an operations task planner. Please generate an executable task plan based on the user's goal."
                        "Return a JSON object in the format {\"steps\": [...]}."
                        "Each step includes title, reason, command, working_directory, expected_output, and risk_level."
                        "Command must be a single executable command. Do not output anything other than JSON."
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
                        title=str(data.get("title") or f"Step {index}"),
                        command=command,
                        reason=str(data.get("reason") or "Executing plan step"),
                        risk_level=str(data.get("risk_level") or "low"),
                        working_directory=str(data.get("working_directory") or "") or None,
                        expected_output=str(data.get("expected_output") or "") or None,
                        status="pending",
                    )
                )

            state.phase = "planning"
            yield from manager.finalize(text="\nPlan generated successfully.")
        except Exception as exc:
            error = f"Task planning failed: {exc}"
            state.phase = "failed"
            state.error_message = error
            yield from manager.finalize(text=f"\nError: {error}")
            yield emit_failed(runtime_id=ctx.runtime_id, error=error)

    def _build_step_messages(self, state: LoopState, step: LoopRuntimeStep) -> list[LLMMessage]:
        ctx = state.context
        system_msg = (
            f"操作系统类型: {ctx.os_type}\n"
            f"当前主机信息: {ctx.asset_summary}\n"
            f"Shell: {ctx.shell_type}\n\n"
            "You are an operations assistant executing a single plan step."
            "You can use the provided tools to perform actions."
            "Prioritize completing the current step, and directly provide a brief summary of the result once finished."
            "Always respond in English."
        )
        user_msg = (
            f"原始任务: {ctx.user_prompt}\n"
            f"当前步骤标题: {step.title}\n"
            f"当前步骤原因: {step.reason}\n"
            f"建议命令: {step.command or '无'}\n"
            f"建议工作目录: {step.working_directory or '未指定'}\n"
            f"期望输出: {step.expected_output or '未指定'}\n"
            "请围绕当前步骤执行，必要时可以调整参数，但不要偏离该步骤目标。"
        )
        return [LLMMessage(role="system", content=system_msg), LLMMessage(role="user", content=user_msg)]

    def _tool_calling_loop(
        self,
        state: LoopState,
        *,
        manager: MessageManager,
        plan_step: LoopRuntimeStep | None = None,
        finalize_on_complete: bool = True,
    ) -> Iterator[LoopEvent]:
        provider = build_llm_provider(state.context.model_config)
        ctx = state.context

        tools = [t.definition for t in self._tools.values()]

        if not state.messages:
            mode_instruction = (
                "你是一个谨慎的运维助手。你可以使用提供的工具执行操作。系统会自动根据策略判断操作是否可直接执行。"
                if ctx.mode == "plan"
                else "你是一个自主运维助手。你可以使用提供的工具执行操作。系统会自动根据策略判断操作是否可直接执行。"
            )
            system_msg = (
                f"操作系统类型: {ctx.os_type}\n"
                f"当前主机信息: {ctx.asset_summary}\n"
                f"Shell: {ctx.shell_type}\n\n"
                "Rules: " + mode_instruction + "\n"
                "When you need to check the environment or complete a task, call the corresponding tool directly."
                "Always respond in English."
            )
            state.messages.append(LLMMessage(role="system", content=system_msg))
            # Inject conversation history from previous turns (Roo Code style)
            if ctx.conversation_history:
                state.messages.extend(ctx.conversation_history)
            state.messages.append(LLMMessage(role="user", content=ctx.user_prompt))

        import time

        while True:
            response_text_parts: list[str] = []
            response_tool_calls = []
            finish_reason: str | None = None
            
            # Start a new assistant message for the LLM response
            yield from manager.begin_message(message_type="say", say_type="text")

            t0 = time.monotonic()
            first_chunk_logged = False
            for chunk in provider.stream_complete(
                config=ctx.model_config,
                request=LLMCompletionRequest(messages=state.messages, tools=tools, json_mode=False),
            ):
                if not first_chunk_logged:
                    ttft = time.monotonic() - t0
                    logger.warning("LLM TTFT: %.2fs (runtime_id=%s, model=%s, msg_count=%d)", ttft, ctx.runtime_id, ctx.model_config.model_name, len(state.messages))
                    first_chunk_logged = True
                if chunk.delta:
                    response_text_parts.append(chunk.delta)
                    yield from manager.update(text=chunk.delta)
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
            
            # Finalize the assistant's text message
            yield from manager.finalize()

            if not response.tool_calls:
                summary = response.text or "Task execution completed."
                if finalize_on_complete:
                    state.phase = "completed"
                    state.summary = summary
                    yield emit_completed(runtime_id=ctx.runtime_id, summary="")
                return False, True, summary

            for index, tool_call in enumerate(response.tool_calls):
                handler = self._tools.get(tool_call.name)
                if handler is None:
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

                if plan_step is None:
                    step = LoopRuntimeStep(
                        step_id=f"step-{uuid.uuid4().hex[:8]}",
                        title=command or tool_call.name,
                        command=command,
                        reason="LLM requested tool execution",
                        risk_level="low",
                        working_directory=str(working_directory) if working_directory else None,
                        status="pending",
                    )
                    state.steps.append(step)
                    state.cursor = len(state.steps) - 1
                else:
                    step = plan_step
                    if command:
                        step.command = command
                    step.working_directory = str(working_directory) if working_directory else None

                action, reason = handler.needs_approval(args)
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
                    continue

                if action == "ask":
                    step.reason = reason
                    step.risk_level = "high"
                    state.phase = "approving"
                    state.pending_tool_call_id = tool_call.id
                    state.pending_tool_name = tool_call.name
                    state.pending_tool_args = args
                    
                    # Prevent HTTP 400 error by satisfying all remaining tool calls in the response
                    for remaining_tool_call in response.tool_calls[index + 1:]:
                        state.messages.append(
                            LLMMessage(
                                role="tool",
                                content="Cancelled because a previous command in the sequence required user approval.",
                                tool_call_id=remaining_tool_call.id,
                                name=remaining_tool_call.name,
                            )
                        )
                        
                    # Emit an 'ask' message for approval
                    yield from manager.begin_message(
                        message_type="ask",
                        ask_type="command",
                    )
                    yield from manager.finalize(
                        tool_call={
                            "id": tool_call.id,
                            "name": tool_call.name,
                            "command": step.command,
                            "args": args,
                        }
                    )
                    # Save the message ID so resume_with_approval can reuse it
                    state.pending_message_id = manager.last_finalized_id
                    return True, None, ""

                step.status = "running"
                state.phase = "executing"
                
                # Emit a 'say' message for tool execution
                yield from manager.begin_message(message_type="say", say_type="tool_use")
                yield from manager.update(
                    tool_call={
                        "id": tool_call.id,
                        "name": tool_call.name,
                        "command": step.command,
                        "args": args,
                    }
                )
                
                # handler.execute should yield output deltas to the manager
                ok, output = yield from handler.execute(state=state, step_id=step.step_id, args=args, manager=manager)
                
                step.status = "completed" if ok else "failed"
                state.messages.append(
                    LLMMessage(
                        role="tool",
                        content=output if ok else f"Command Failed: {output}",
                        tool_call_id=tool_call.id,
                        name=tool_call.name,
                    )
                )
                yield from manager.finalize(exit_code=0 if ok else 1)

        return False, True, ""
