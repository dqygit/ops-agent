from __future__ import annotations

import uuid

from app.core.graph.events import push_event
from app.core.llm.base import LLMCompletionRequest, LLMCompletionResponse, LLMMessage
from app.core.llm.factory import build_llm_provider
from app.core.tool.schema import LLMToolDefinition
from app.services.approval_service import get_approval_service


def run_model_turn(state: dict):
    provider = build_llm_provider(state["model_config"])
    messages = list(state.get("messages") or [])

    if not messages:
        system_msg = (
            f"操作系统类型: {state.get('os_type', 'unknown')}\\n"
            f"当前主机信息: {state.get('asset_summary', '')}\\n"
            f"Shell: {state.get('shell_type', 'unknown')}\\n\\n"
            "你是一个自主运维助手。你只能通过 execute_command 工具执行操作。"
        )
        messages.append(LLMMessage(role="system", content=system_msg))
        messages.append(LLMMessage(role="user", content=state.get("user_prompt", "")))

    tools = [
        LLMToolDefinition(
            name="execute_command",
            description="执行终端命令。系统会自动根据审批策略判断是允许、拒绝还是要求用户审批。",
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

    message_id = f"msg-{uuid.uuid4().hex[:10]}"
    text_parts: list[str] = []
    tool_calls = []
    finish_reason: str | None = None
    for chunk in provider.stream_complete(
        config=state["model_config"],
        request=LLMCompletionRequest(messages=messages, tools=tools, json_mode=False),
    ):
        if chunk.delta:
            text_parts.append(chunk.delta)
            push_event(state, kind="delta", payload={"messageId": message_id, "text": chunk.delta})
        if chunk.tool_calls:
            tool_calls = chunk.tool_calls
        if chunk.finish_reason:
            finish_reason = chunk.finish_reason

    response = LLMCompletionResponse(text="".join(text_parts), tool_calls=tool_calls, finish_reason=finish_reason)
    if response.text or response.tool_calls:
        messages.append(LLMMessage(role="assistant", content=response.text, tool_calls=response.tool_calls))

    if not response.tool_calls:
        state["messages"] = messages
        state["status"] = "completed"
        state["final_text"] = response.text or "任务已执行完毕。"
        push_event(state, kind="final", payload={"text": state["final_text"]})
        return state

    tool_call = response.tool_calls[0]
    args = tool_call.arguments
    command = str(args.get("command", "")).strip()
    if not command:
        messages.append(LLMMessage(role="tool", name=tool_call.name, tool_call_id=tool_call.id, content="Missing required field: command"))
        state["messages"] = messages
        return state

    step_id = f"step-{uuid.uuid4().hex[:8]}"
    step = {
        "id": step_id,
        "title": command,
        "command": command,
        "reason": "LLM requested command execution",
        "status": "pending",
    }
    steps = list(state.get("steps") or [])
    steps.append(step)
    state["steps"] = steps
    state["current_step"] = step_id
    push_event(state, kind="plan", payload={"planId": f"runtime-{state['runtime_id']}", "title": "Task Plan", "steps": [{"id": s['id'], "title": s['title'], "status": s['status']} for s in steps], "runtimeId": state["runtime_id"]})

    action, reason = get_approval_service().check_command(command)
    if action == "deny":
        step["status"] = "failed"
        messages.append(LLMMessage(role="tool", name=tool_call.name, tool_call_id=tool_call.id, content=f"Command denied: {reason}"))
        state["messages"] = messages
        return state

    if action == "ask":
        token = uuid.uuid4().hex
        state["pending_approval"] = {
            "token": token,
            "step_id": step_id,
            "tool_call_id": tool_call.id,
            "tool_name": tool_call.name,
            "args": args,
            "command": command,
            "reason": reason,
        }
        state["status"] = "waiting_approval"
        push_event(
            state,
            kind="approval_required",
            payload={
                "stepId": step_id,
                "command": command,
                "reason": reason,
                "approvalToken": token,
            },
        )
        state["messages"] = messages
        return state

    state["messages"] = messages
    state["pending_approval"] = {
        "token": "auto",
        "step_id": step_id,
        "tool_call_id": tool_call.id,
        "tool_name": tool_call.name,
        "args": args,
        "command": command,
        "reason": "auto-allow",
    }
    return state
