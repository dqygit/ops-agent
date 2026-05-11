from __future__ import annotations

from types import SimpleNamespace

from app.core.graph.events import push_event
from app.core.llm.base import LLMMessage


def run_execute_command(state: dict, *, terminal_adapter):
    pending = state.get("pending_approval")
    if not pending:
        return state

    step_id = pending.get("step_id", "")
    command = str((pending.get("args") or {}).get("command", "")).strip()
    working_directory = (pending.get("args") or {}).get("working_directory")
    runtime_id = state.get("runtime_id", "")
    terminal_id = state.get("terminal_id")

    if not terminal_id:
        state["status"] = "failed"
        state["error"] = "终端未连接，无法执行。"
        push_event(state, kind="error", payload={"text": state["error"]})
        return state

    session_manager = terminal_adapter.get_session(terminal_id)
    if session_manager is None:
        state["status"] = "failed"
        state["error"] = "终端会话不存在，无法执行命令。"
        push_event(state, kind="error", payload={"text": state["error"]})
        return state

    if not terminal_adapter.acquire_terminal_slot(runtime_id, terminal_id):
        state["status"] = "failed"
        state["error"] = "当前终端已有其他任务在执行，请稍后再试。"
        push_event(state, kind="error", payload={"text": state["error"]})
        return state

    try:
        execution_id = session_manager.start_execution(
            command,
            SimpleNamespace(working_directory=str(working_directory) if working_directory else None),
        )
        execution = session_manager.get_execution_result(execution_id)
        command_id = execution.execution_id or step_id

        push_event(state, kind="command_start", payload={"commandId": command_id, "stepId": step_id, "terminalId": terminal_id, "command": command, "title": command})
        if execution.output:
            push_event(state, kind="command_chunk", payload={"commandId": command_id, "stepId": step_id, "terminalId": terminal_id, "stream": "stdout", "text": execution.output})
        success = bool(execution.completed and execution.exit_code in {None, 0})
        push_event(state, kind="command_end", payload={"commandId": command_id, "stepId": step_id, "terminalId": terminal_id, "exitCode": execution.exit_code, "summary": "completed" if success else "failed"})

        state["last_output_excerpt"] = (execution.output or "")[-4000:]
        steps = list(state.get("steps") or [])
        for step in steps:
            if step.get("id") == step_id:
                step["status"] = "completed" if success else "failed"
                step["output"] = execution.output or ""
                step["exit_code"] = execution.exit_code
                break
        state["steps"] = steps

        messages = list(state.get("messages") or [])
        messages.append(
            LLMMessage(
                role="tool",
                content=(execution.output or "") if success else f"Command Failed: {execution.output or ''}",
                tool_call_id=pending.get("tool_call_id"),
                name=pending.get("tool_name"),
            )
        )
        state["messages"] = messages
        state["pending_approval"] = None
        if not success:
            state["status"] = "failed"
            state["error"] = execution.output or "命令执行失败"
            push_event(state, kind="error", payload={"text": state["error"]})
    except Exception as exc:
        state["status"] = "failed"
        state["error"] = f"命令执行异常: {exc}"
        push_event(state, kind="error", payload={"text": state["error"]})
    finally:
        terminal_adapter.release_terminal_slot(runtime_id, terminal_id)

    return state
