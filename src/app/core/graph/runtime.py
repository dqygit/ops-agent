from __future__ import annotations

from collections import deque
from dataclasses import dataclass
from datetime import UTC, datetime
import uuid

from langgraph.checkpoint.memory import InMemorySaver

from app.core.graph.build_graph import build_graph
from app.core.graph.nodes.approval_gate import apply_approval_decision
from app.core.graph.nodes.execute_command import run_execute_command
from app.core.graph.nodes.model_turn import run_model_turn


@dataclass
class GraphRuntime:
    runtime_id: str
    conversation_id: str
    asset_id: int
    terminal_id: str | None
    state: dict
    events: deque[dict]
    sequence: int
    created_at: datetime
    updated_at: datetime


class GraphRuntimeManager:
    def __init__(self, *, terminal_adapter_factory):
        self._terminal_adapter_factory = terminal_adapter_factory
        self._by_runtime: dict[str, GraphRuntime] = {}
        self._by_conversation: dict[str, dict[str, GraphRuntime]] = {}
        self._checkpointer = InMemorySaver()

    def create_runtime(self, *, conversation_id: str, asset_id: int, terminal_id: str | None, initial_state: dict) -> GraphRuntime:
        runtime_id = initial_state["runtime_id"]
        runtime = GraphRuntime(
            runtime_id=runtime_id,
            conversation_id=conversation_id,
            asset_id=asset_id,
            terminal_id=terminal_id,
            state=initial_state,
            events=deque(maxlen=2000),
            sequence=0,
            created_at=datetime.now(UTC),
            updated_at=datetime.now(UTC),
        )
        self._by_runtime[runtime_id] = runtime
        self._by_conversation.setdefault(conversation_id, {})[runtime_id] = runtime
        return runtime

    def get_runtime(self, runtime_id: str) -> GraphRuntime | None:
        return self._by_runtime.get(runtime_id)

    def list_runtimes(self, conversation_id: str) -> list[GraphRuntime]:
        return list(self._by_conversation.get(conversation_id, {}).values())

    def events_since(self, runtime_id: str, since: int) -> tuple[int, list[dict]]:
        rt = self._by_runtime.get(runtime_id)
        if rt is None:
            raise ValueError("runtime not found")
        events = [evt for evt in rt.events if int(evt.get("sequence", 0)) > since]
        return rt.sequence, events

    def get_snapshot(self, runtime_id: str) -> dict:
        rt = self._by_runtime.get(runtime_id)
        if rt is None:
            raise ValueError("runtime not found")
        state = rt.state
        pending = state.get("pending_approval")
        return {
            "runtime_id": rt.runtime_id,
            "conversation_id": rt.conversation_id,
            "asset_id": rt.asset_id,
            "terminal_id": rt.terminal_id,
            "status": state.get("status", "running"),
            "steps": [
                {
                    "step_id": s.get("id", ""),
                    "title": s.get("title", ""),
                    "command": s.get("command", ""),
                    "reason": s.get("reason", ""),
                    "risk_level": "high" if pending and pending.get("step_id") == s.get("id") else "low",
                    "working_directory": None,
                    "expected_output": None,
                    "status": s.get("status", "pending"),
                    "output": s.get("output", ""),
                    "exit_code": s.get("exit_code"),
                }
                for s in state.get("steps", [])
            ],
            "current_step_id": state.get("current_step"),
            "pending_approval_step_id": pending.get("step_id") if pending else None,
            "last_output_excerpt": state.get("last_output_excerpt", ""),
            "summary": state.get("final_text"),
            "error_message": state.get("error"),
            "created_at": rt.created_at,
            "updated_at": rt.updated_at,
            "last_sequence": rt.sequence,
        }

    def run(self, *, runtime_id: str, terminal_service) -> list[dict]:
        rt = self._by_runtime[runtime_id]
        terminal_adapter = self._terminal_adapter_factory(terminal_service)

        graph = build_graph(run_model_turn, lambda s: run_execute_command(s, terminal_adapter=terminal_adapter)).compile(checkpointer=self._checkpointer)
        config = {"configurable": {"thread_id": runtime_id}}
        out = graph.invoke(rt.state, config=config)
        rt.state = out
        return self._drain_events(rt)

    def resume(self, *, runtime_id: str, approved: bool, approval_token: str | None, terminal_service) -> list[dict]:
        rt = self._by_runtime.get(runtime_id)
        if rt is None:
            raise ValueError("runtime not found")

        rt.state = apply_approval_decision(rt.state, approved=approved, token=approval_token)
        if rt.state.get("status") == "failed":
            return self._drain_events(rt)

        terminal_adapter = self._terminal_adapter_factory(terminal_service)
        graph = build_graph(run_model_turn, lambda s: run_execute_command(s, terminal_adapter=terminal_adapter)).compile(checkpointer=self._checkpointer)
        rt.state = graph.invoke(rt.state, config={"configurable": {"thread_id": runtime_id}})
        return self._drain_events(rt)

    def _drain_events(self, rt: GraphRuntime) -> list[dict]:
        events = list(rt.state.get("events") or [])
        rt.state["events"] = []
        for event in events:
            rt.sequence = max(rt.sequence, int(event.get("sequence", 0)))
            rt.events.append(event)
        rt.updated_at = datetime.now(UTC)
        return events


def build_initial_state(*, runtime_id: str, conversation_id: str, asset_id: int, terminal_id: str | None, model_config, asset_summary: str, shell_type: str, os_type: str, user_prompt: str) -> dict:
    return {
        "runtime_id": runtime_id,
        "conversation_id": conversation_id,
        "asset_id": asset_id,
        "terminal_id": terminal_id,
        "model_config": model_config,
        "asset_summary": asset_summary,
        "shell_type": shell_type,
        "os_type": os_type,
        "user_prompt": user_prompt,
        "messages": [],
        "current_step": None,
        "steps": [],
        "pending_approval": None,
        "last_output_excerpt": "",
        "status": "running",
        "error": None,
        "final_text": None,
        "events": [],
        "sequence": 0,
    }


def new_runtime_id() -> str:
    return str(uuid.uuid4())
