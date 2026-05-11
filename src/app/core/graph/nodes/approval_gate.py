from __future__ import annotations

from app.core.graph.events import push_event
from app.core.llm.base import LLMMessage


def apply_approval_decision(state: dict, *, approved: bool, token: str | None):
    pending = state.get("pending_approval")
    if not pending:
        return state

    expected = pending.get("token")
    if token and expected and token != expected:
        state["status"] = "failed"
        state["error"] = "approval token mismatch"
        push_event(state, kind="error", payload={"text": state["error"]})
        return state

    step_id = pending.get("step_id")
    command = pending.get("command", "")
    push_event(state, kind="approval_decision", payload={"stepId": step_id, "approved": approved, "command": command})

    if approved:
        state["status"] = "running"
        return state

    steps = list(state.get("steps") or [])
    for step in steps:
        if step.get("id") == step_id:
            step["status"] = "failed"
            break
    state["steps"] = steps

    messages = list(state.get("messages") or [])
    messages.append(
        LLMMessage(
            role="tool",
            content="Command execution rejected by user.",
            tool_call_id=pending.get("tool_call_id"),
            name=pending.get("tool_name"),
        )
    )
    state["messages"] = messages
    state["pending_approval"] = None
    return state
