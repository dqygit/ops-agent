from __future__ import annotations

from typing import Any, Literal, TypedDict

from app.core.llm.base import LLMMessage

GraphStatus = Literal["running", "waiting_approval", "completed", "failed"]


class GraphStep(TypedDict, total=False):
    id: str
    title: str
    command: str
    reason: str
    status: Literal["pending", "running", "completed", "failed"]
    output: str
    exit_code: int | None


class PendingApproval(TypedDict, total=False):
    token: str
    step_id: str
    tool_call_id: str
    tool_name: str
    args: dict[str, Any]
    command: str
    reason: str


class GraphState(TypedDict):
    runtime_id: str
    conversation_id: str
    asset_id: int
    terminal_id: str | None
    model_config: Any
    asset_summary: str
    shell_type: str
    os_type: str
    user_prompt: str

    messages: list[LLMMessage]
    current_step: str | None
    steps: list[GraphStep]
    pending_approval: PendingApproval | None
    last_output_excerpt: str
    status: GraphStatus
    error: str | None
    final_text: str | None

    events: list[dict[str, Any]]
    sequence: int
