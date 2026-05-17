from __future__ import annotations

import uuid
from collections import deque
from collections.abc import Iterator
from dataclasses import dataclass
from datetime import UTC, datetime

from app.core.loop.agent_loop import AgentLoop
from app.core.loop.loop_events import LoopEvent
from app.core.loop.loop_state import LoopContext, LoopRuntimeStep, LoopState


@dataclass
class RuntimeState:
    runtime_id: str
    conversation_id: str
    asset_id: int
    terminal_id: str | None
    state: LoopState
    events: deque[dict]
    sequence: int
    created_at: datetime
    updated_at: datetime


class LoopRuntimeManager:
    def __init__(self, *, tools_factory, usage_callback=None):
        self._tools_factory = tools_factory
        self._usage_callback = usage_callback
        self._by_runtime: dict[str, RuntimeState] = {}
        self._by_conversation: dict[str, dict[str, RuntimeState]] = {}
        self._terminal_slots: dict[str, str] = {}

    def acquire_terminal_slot(self, runtime_id: str, terminal_id: str) -> bool:
        if terminal_id in self._terminal_slots and self._terminal_slots[terminal_id] != runtime_id:
            return False
        self._terminal_slots[terminal_id] = runtime_id
        return True

    def release_terminal_slot(self, runtime_id: str, terminal_id: str) -> None:
        if self._terminal_slots.get(terminal_id) == runtime_id:
            self._terminal_slots.pop(terminal_id, None)

    def create_runtime(self, *, conversation_id: str, asset_id: int, terminal_id: str | None, context: LoopContext) -> LoopState:
        runtime_id = context.runtime_id
        state = LoopState(phase="executing", context=context)
        runtime = RuntimeState(
            runtime_id=runtime_id,
            conversation_id=conversation_id,
            asset_id=asset_id,
            terminal_id=terminal_id,
            state=state,
            events=deque(maxlen=2000),
            sequence=0,
            created_at=datetime.now(UTC),
            updated_at=datetime.now(UTC),
        )
        self._by_runtime[runtime_id] = runtime
        self._by_conversation.setdefault(conversation_id, {})[runtime_id] = runtime
        return state

    def get_runtime(self, runtime_id: str) -> RuntimeState | None:
        return self._by_runtime.get(runtime_id)

    def list_runtimes(self, conversation_id: str) -> list[RuntimeState]:
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
        current_step = state.get_current_step()
        return {
            "runtime_id": rt.runtime_id,
            "conversation_id": rt.conversation_id,
            "asset_id": rt.asset_id,
            "terminal_id": rt.terminal_id,
            "status": state.phase,
            "loaded_skill_name": state.context.loaded_skill_name,
            "mode": state.context.mode,
            "plan_version": state.plan_version,
            "locked_plan": state.locked_plan,
            "steps": [
                {
                    "step_id": s.step_id,
                    "title": s.title,
                    "command": "",
                    "reason": s.reason,
                    "risk_level": s.risk_level,
                    "working_directory": s.working_directory,
                    "expected_output": s.expected_output,
                    "status": s.status,
                    "output": s.output,
                    "exit_code": s.exit_code,
                }
                for s in state.steps
            ],
            "current_step_id": current_step.step_id if current_step else None,
            "pending_approval_step_id": state.pending_approval_step_id,
            "last_output_excerpt": state.last_output_excerpt,
            "summary": state.summary,
            "error_message": state.error_message,
            "created_at": rt.created_at,
            "updated_at": rt.updated_at,
            "last_sequence": rt.sequence,
        }

    def run(self, *, runtime_id: str, terminal_service) -> Iterator[dict]:
        rt = self._by_runtime.get(runtime_id)
        if rt is None:
            raise ValueError("runtime not found")

        loop = AgentLoop(tools=self._tools_factory(terminal_service), usage_callback=self._usage_callback)
        for event in loop.run(rt.state):
            yield self._to_ws_event(event, rt)
            usage_event = self._build_usage_event(rt)
            if usage_event is not None:
                yield usage_event

    def update_plan(self, *, runtime_id: str, steps: list[dict]) -> dict:
        rt = self._by_runtime.get(runtime_id)
        if rt is None:
            raise ValueError("runtime not found")
        state = rt.state
        if state.context.mode != "plan":
            raise ValueError("runtime is not in plan mode")
        if state.phase != "waiting_plan_approval" or state.locked_plan:
            raise ValueError("plan can only be edited before approval")
        if not steps:
            raise ValueError("plan must include at least one step")

        state.steps = [
            LoopRuntimeStep(
                step_id=str(item.get("id") or item.get("step_id") or f"step-{uuid.uuid4().hex[:8]}"),
                title=str(item.get("title") or "").strip() or f"Step {index}",
                reason=str(item.get("reason") or "Executing plan step"),
                risk_level=str(item.get("riskLevel") or item.get("risk_level") or "low"),
                working_directory=str(item.get("workingDirectory") or item.get("working_directory") or "") or None,
                expected_output=str(item.get("expectedOutput") or item.get("expected_output") or "") or None,
                status="pending",
            )
            for index, item in enumerate(steps, start=1)
        ]
        state.cursor = 0
        state.plan_version += 1
        rt.updated_at = datetime.now(UTC)
        return self._append_plan_event(rt)

    def approve_plan(self, *, runtime_id: str, terminal_service) -> Iterator[dict]:
        rt = self._by_runtime.get(runtime_id)
        if rt is None:
            raise ValueError("runtime not found")
        state = rt.state
        if state.context.mode != "plan":
            raise ValueError("runtime is not in plan mode")
        if state.phase != "waiting_plan_approval":
            raise ValueError("plan is not waiting for approval")
        if not state.steps:
            raise ValueError("plan has no steps")

        state.locked_plan = True
        state.cursor = 0
        state.phase = "executing"
        yield self._append_plan_event(rt)
        loop = AgentLoop(tools=self._tools_factory(terminal_service), usage_callback=self._usage_callback)
        for event in loop.run(rt.state):
            yield self._to_ws_event(event, rt)
            usage_event = self._build_usage_event(rt)
            if usage_event is not None:
                yield usage_event

    def _append_plan_event(self, rt: RuntimeState) -> dict:
        state = rt.state
        event = LoopEvent(
            event_type="plan",
            runtime_id=rt.runtime_id,
            phase=state.phase,
            payload={
                "planId": rt.runtime_id,
                "title": "Task Plan",
                "mode": state.context.mode,
                "version": state.plan_version,
                "lockedPlan": state.locked_plan,
                "status": state.phase,
                "steps": [
                    {
                        "id": step.step_id,
                        "title": step.title,
                        "command": "",
                        "reason": step.reason,
                        "riskLevel": step.risk_level,
                        "workingDirectory": step.working_directory,
                        "expectedOutput": step.expected_output,
                        "status": step.status,
                    }
                    for step in state.steps
                ],
            },
        )
        return self._to_ws_event(event, rt)

    def resume(self, *, runtime_id: str, approved: bool, approval_token: str | None, terminal_service) -> Iterator[dict]:
        rt = self._by_runtime.get(runtime_id)
        if rt is None:
            raise ValueError("runtime not found")

        # In a real implementation we would verify approval_token here
        loop = AgentLoop(tools=self._tools_factory(terminal_service), usage_callback=self._usage_callback)
        for event in loop.resume_with_approval(rt.state, approved=approved):
            yield self._to_ws_event(event, rt)
            usage_event = self._build_usage_event(rt)
            if usage_event is not None:
                yield usage_event

    def _build_usage_event(self, rt: RuntimeState) -> dict | None:
        state = rt.state
        if self._usage_callback is None:
            return None
        usage = getattr(state, "latest_usage", None)
        if usage is None:
            return None
        state.latest_usage = None
        rt.sequence += 1
        rt.updated_at = datetime.now(UTC)
        event = {
            "id": f"evt-context-{uuid.uuid4().hex[:12]}",
            "kind": "context_status",
            "runtimeId": rt.runtime_id,
            "sequence": rt.sequence,
            "ts": datetime.now(UTC).isoformat(),
            "tokenUsage": usage,
        }
        rt.events.append(event)
        return event

    def _to_ws_event(self, event: LoopEvent, rt: RuntimeState) -> dict:
        rt.sequence += 1
        rt.updated_at = datetime.now(UTC)
        kind = event.event_type.replace("loop_", "")
        
        if kind == "message_update":
            # For message_update events, use the message's own id and spread
            # all message fields at the top level for the frontend to consume.
            ws_event = {
                **event.payload,           # id, ts, type, text, partial, toolCall, etc.
                "kind": kind,              # Override kind to "message_update" for transport
                "runtimeId": event.runtime_id,
                "sequence": rt.sequence,
            }
        else:
            ws_event = {
                "id": f"evt-{uuid.uuid4().hex[:12]}",
                "kind": kind,
                "runtimeId": event.runtime_id,
                "sequence": rt.sequence,
                "ts": datetime.now(UTC).isoformat(),
                **event.payload,
            }
        
        if event.message_id:
            ws_event["messageId"] = event.message_id
        if event.stage:
            ws_event["stage"] = event.stage
        if event.step_id:
            ws_event["stepId"] = event.step_id
            
        rt.events.append(ws_event)
        return ws_event

def new_runtime_id() -> str:
    return str(uuid.uuid4())
