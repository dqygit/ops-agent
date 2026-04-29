from collections.abc import Iterable
from datetime import UTC, datetime
from typing import Any, Protocol, TypedDict, cast

from langchain_core.runnables import RunnableConfig
from langgraph.checkpoint.memory import InMemorySaver
from langgraph.graph import END, START, StateGraph
from langgraph.types import Command, interrupt

from app.shared.enums import TaskStatus, TerminalEventType
from app.shared.schemas import ModelConfig, PlanStep


class Planner(Protocol):
    def __call__(self, asset_type: Any, user_input: str, terminal_context=None, recent_messages=None) -> list[PlanStep]: ...


class StepExecutor(Protocol):
    def __call__(self, step: PlanStep, *, state: "AgentRunState", emit=None) -> dict[str, Any]: ...


class Summarizer(Protocol):
    def __call__(self, user_input: str, execution_results: list[dict[str, Any]], recent_messages=None) -> str | Iterable[str]: ...


class AgentRunState(TypedDict):
    conversation_id: str
    run_id: str
    user_message: str
    recent_messages: list[dict[str, Any]]
    asset_type: object
    asset_id: int
    session_id: int
    task_id: int
    model_name: str
    terminal_context: object | None
    plan_steps: list[PlanStep]
    step_ids: list[int]
    current_step_index: int
    approved: bool | None
    latest_approval_step_index: int | None
    execution_results: list[dict[str, Any]]
    assistant_message: str | None
    error_message: str | None
    ui_events: list[dict[str, Any]]


class AgentRuntime:
    def __init__(
        self,
        planner: Planner,
        step_executor: StepExecutor,
        summarizer: Summarizer,
        persistence=None,
        model_config: ModelConfig | None = None,
        auto_approval_checker=None,
    ):
        self._planner = planner
        self._step_executor = step_executor
        self._summarizer = summarizer
        self._persistence = persistence
        self._model_config = model_config
        self._auto_approval_checker = auto_approval_checker
        self._state_cache: dict[str, AgentRunState] = {}
        self._graph = self._build_graph()

    def set_model_config(self, config: ModelConfig) -> None:
        self._model_config = config

    def set_active_model_name(self, model_name: str) -> None:
        if self._model_config is None:
            return
        self._model_config = self._model_config.model_copy(update={"model_name": model_name})

    def _record_terminal_output(self, state: AgentRunState, chunk: str) -> None:
        if self._persistence is None or not chunk:
            return
        terminal_context = state.get("terminal_context")
        terminal_session_id = getattr(terminal_context, "terminal_session_id", 0) if terminal_context is not None else 0
        if not terminal_session_id:
            return
        self._persistence.record_terminal_event(
            terminal_session_id=terminal_session_id,
            event_type=TerminalEventType.OUTPUT.value,
            metadata={"chunk": chunk, "run_id": state["run_id"]},
        )

    def _record_model_usage(self, state: AgentRunState) -> None:
        if self._persistence is None or self._model_config is None or not state["task_id"]:
            return
        self._persistence.record_model_usage(
            task_id=state["task_id"],
            provider=self._model_config.provider.value,
            model_name=self._model_config.model_name,
            base_url_snapshot=self._model_config.base_url,
            temperature_snapshot=self._model_config.temperature,
            max_tokens_snapshot=self._model_config.max_tokens,
        )

    def _build_graph(self):
        builder = StateGraph(AgentRunState)
        builder.add_node("plan_task", self._plan_task)
        builder.add_node("request_step_approval", self._request_step_approval)
        builder.add_node("execute_step", self._execute_step)
        builder.add_node("summarize_task", self._summarize_task)
        builder.add_edge(START, "plan_task")
        builder.add_conditional_edges(
            "plan_task",
            self._route_after_plan,
            {
                "request_step_approval": "request_step_approval",
                "execute_step": "execute_step",
                "summarize_task": "summarize_task",
            },
        )
        builder.add_conditional_edges(
            "request_step_approval",
            self._route_after_approval,
            {
                "execute_step": "execute_step",
                "summarize_task": "summarize_task",
            },
        )
        builder.add_conditional_edges(
            "execute_step",
            self._route_after_execution,
            {
                "request_step_approval": "request_step_approval",
                "execute_step": "execute_step",
                "summarize_task": "summarize_task",
            },
        )
        builder.add_edge("summarize_task", END)
        return builder.compile(checkpointer=InMemorySaver())

    def start_run(
        self,
        *,
        conversation_id: str,
        run_id: str,
        user_message: str,
        asset_type,
        asset_id: int,
        session_id: int,
        model_name: str,
        terminal_context=None,
        recent_messages=None,
    ) -> AgentRunState:
        plan_steps = self._planner(
            asset_type,
            user_message,
            terminal_context=terminal_context,
            recent_messages=recent_messages or [],
        )
        task_id = 0
        step_ids: list[int] = []
        if self._persistence is not None:
            task_id = self._persistence.create_task(
                session_id=session_id,
                run_id=run_id,
                asset_id=asset_id,
                user_input=user_message,
                terminal_context=terminal_context,
                plan_steps=plan_steps,
            )
            step_ids = self._persistence.create_steps(task_id=task_id, plan_steps=plan_steps)
        initial_state: AgentRunState = {
            "conversation_id": conversation_id,
            "run_id": run_id,
            "user_message": user_message,
            "asset_type": asset_type,
            "asset_id": asset_id,
            "session_id": session_id,
            "task_id": task_id,
            "model_name": model_name,
            "terminal_context": terminal_context,
            "recent_messages": recent_messages or [],
            "plan_steps": plan_steps,
            "step_ids": step_ids,
            "current_step_index": 0,
            "execution_results": [],
            "assistant_message": None,
            "approved": None,
            "latest_approval_step_index": None,
            "error_message": None,
            "ui_events": [],
        }
        self._state_cache[run_id] = cast(AgentRunState, dict(initial_state))
        result = cast(AgentRunState, self._graph.invoke(initial_state, config=self._config(run_id)))
        merged = self._merge_result(run_id, result)
        return {
            **merged,
            "ui_events": self._build_plan_events(run_id, plan_steps),
        }

    def resume_run(self, *, run_id: str, approved: bool) -> AgentRunState:
        result = cast(AgentRunState, self._graph.invoke(Command(resume=approved), config=self._config(run_id)))
        return self._merge_result(run_id, result)

    def _config(self, run_id: str) -> RunnableConfig:
        return {"configurable": {"thread_id": run_id}}

    def _merge_result(self, run_id: str, result: AgentRunState) -> AgentRunState:
        merged = dict(self._state_cache.get(run_id, {}))
        merged.update(result)
        final_state = cast(AgentRunState, merged)
        self._state_cache[run_id] = cast(AgentRunState, dict(final_state))
        return final_state

    def _plan_task(self, state: AgentRunState) -> AgentRunState:
        return {**state, "approved": None, "latest_approval_step_index": None}

    def _request_step_approval(self, state: AgentRunState) -> AgentRunState:
        step_index = state["current_step_index"]
        if step_index >= len(state["plan_steps"]):
            return {**state, "approved": True, "latest_approval_step_index": None}
        step = state["plan_steps"][step_index]
        approval = self._match_auto_approval(state, step)
        if approval is not None:
            if self._persistence is not None and state["task_id"]:
                self._persistence.record_step_auto_approval(
                    task_id=state["task_id"],
                    asset_id=state["asset_id"],
                    terminal_context=state["terminal_context"],
                    step=step,
                    reason=approval.get("reason", ""),
                )
            return {
                **state,
                "approved": True,
                "latest_approval_step_index": step_index,
                "ui_events": [
                    *state.get("ui_events", []),
                    {
                        "type": "auto_approved",
                        "run_id": state["run_id"],
                        "payload": {
                            "step_index": step_index,
                            "rule_id": approval.get("rule_id"),
                            "reason": approval.get("reason", ""),
                        },
                    },
                ],
            }

        approved = interrupt(
            {
                "type": "approval_request",
                "run_id": state["run_id"],
                "step_index": step_index,
                "step": {
                    "title": step.title,
                    "command": step.command,
                    "reason": step.reason,
                    "risk_level": step.risk_level,
                    "working_directory": step.working_directory,
                    "expected_output": step.expected_output,
                },
                "message": f"Approve step {step_index + 1}?",
            }
        )
        if self._persistence is not None and state["task_id"]:
            self._persistence.record_approval(
                task_id=state["task_id"],
                asset_id=state["asset_id"],
                terminal_context=state["terminal_context"],
                steps=[step],
                step_ids=[state["step_ids"][step_index]] if step_index < len(state["step_ids"]) else [],
                approved=bool(approved),
            )
            self._persistence.update_task_status(
                task_id=state["task_id"],
                status=TaskStatus.APPROVED.value if approved else TaskStatus.REJECTED.value,
            )
        return {
            **state,
            "approved": bool(approved),
            "latest_approval_step_index": step_index,
            "ui_events": [
                *state.get("ui_events", []),
                {
                    "type": "approval_requested",
                    "run_id": state["run_id"],
                    "payload": {
                        "message": f"Approve step {step_index + 1}?",
                        "step": {
                            "title": step.title,
                            "command": step.command,
                            "reason": step.reason,
                            "risk_level": step.risk_level,
                            "working_directory": step.working_directory,
                            "expected_output": step.expected_output,
                        },
                    },
                },
            ],
        }

    def _execute_step(self, state: AgentRunState) -> AgentRunState:
        events: list[dict[str, Any]] = [event for event in state.get("ui_events", []) if event.get("type") != "approval_requested"]
        if not state["approved"]:
            events.append(
                {
                    "type": "assistant_final",
                    "run_id": state["run_id"],
                    "payload": {"message": "任务已取消"},
                }
            )
            return {
                **state,
                "approved": False,
                "latest_approval_step_index": state.get("latest_approval_step_index"),
                "assistant_message": "任务已取消",
                "ui_events": events,
            }

        if state["current_step_index"] >= len(state["plan_steps"]):
            return {**state, "ui_events": [], "approved": True}

        if self._persistence is not None and state["task_id"] and not state["execution_results"]:
            self._persistence.update_task_status(task_id=state["task_id"], status=TaskStatus.RUNNING.value)
        events.append(
            {
                "type": "assistant_status",
                "run_id": state["run_id"],
                "payload": {"value": "executing"},
            }
        )
        index = state["current_step_index"]
        step = state["plan_steps"][index]
        step_id = state["step_ids"][index] if index < len(state["step_ids"]) else 0
        started_at = datetime.now(UTC)
        command_execution_id = 0
        if self._persistence is not None and step_id:
            self._persistence.update_step(
                step_id=step_id,
                status=TaskStatus.RUNNING.value,
                started_at=started_at,
            )
            command_execution_id = self._persistence.create_command_execution(
                task_id=state["task_id"],
                step_id=step_id,
                asset_id=state["asset_id"],
                terminal_context=state["terminal_context"],
                command=step.command,
                working_directory=step.working_directory,
                started_at=started_at,
            )
        events.append(
            {
                "type": "step_started",
                "run_id": state["run_id"],
                "payload": {"step_index": index, "title": step.title, "command": step.command},
            }
        )
        result = self._step_executor(
            step,
            state=state,
            emit=lambda chunk, step_index=index, title=step.title, command=step.command: (
                self._record_terminal_output(state, chunk),
                events.append(
                    {
                        "type": "terminal_output",
                        "run_id": state["run_id"],
                        "payload": {
                            "step_index": step_index,
                            "title": title,
                            "command": command,
                            "chunk": chunk,
                        },
                    }
                ),
            )[-1],
        )
        execution_results = [*state["execution_results"], result]
        finished_at = datetime.now(UTC)
        if self._persistence is not None and step_id:
            status = TaskStatus.COMPLETED.value if result.get("exit_code", 0) == 0 else TaskStatus.FAILED.value
            output = result.get("output") or result.get("stdout", "")
            error_output = result.get("error") or result.get("stderr", "")
            self._persistence.update_step(
                step_id=step_id,
                status=status,
                output=output,
                error_message=error_output,
                exit_code=result.get("exit_code"),
                finished_at=finished_at,
            )
            if command_execution_id:
                self._persistence.update_command_execution(
                    command_execution_id=command_execution_id,
                    status=status,
                    output=output,
                    error_output=error_output,
                    exit_code=result.get("exit_code"),
                    finished_at=finished_at,
                )
        events.append(
            {
                "type": "step_finished",
                "run_id": state["run_id"],
                "payload": result,
            }
        )
        return {
            **state,
            "approved": True,
            "execution_results": execution_results,
            "assistant_message": None,
            "current_step_index": index + 1,
            "ui_events": events,
        }

    def _summarize_task(self, state: AgentRunState) -> AgentRunState:
        events: list[dict[str, Any]] = [*state.get("ui_events", [])]
        if not state["approved"]:
            return state
        self._record_model_usage(state)
        summary = self._summarizer(
            state["user_message"],
            state["execution_results"],
            recent_messages=state["recent_messages"],
        )
        message = self._collect_summary(state["run_id"], events, summary)
        task_status = TaskStatus.COMPLETED.value
        if any((result.get("exit_code", 0) != 0) for result in state["execution_results"]):
            task_status = TaskStatus.FAILED.value
        if self._persistence is not None and state["task_id"]:
            self._persistence.update_task_status(
                task_id=state["task_id"],
                status=task_status,
                final_summary=message,
            )
        events.append(
            {
                "type": "assistant_final",
                "run_id": state["run_id"],
                "payload": {"message": message},
            }
        )
        return {
            **state,
            "assistant_message": message,
            "ui_events": events,
        }

    def _match_auto_approval(self, state: AgentRunState, step: PlanStep) -> dict[str, Any] | None:
        if self._auto_approval_checker is None:
            return None
        result = self._auto_approval_checker(
            session_id=state["session_id"],
            asset_type=getattr(state["asset_type"], "value", state["asset_type"]),
            command=step.command,
            risk_level=step.risk_level,
        )
        if not result or not result.get("matched"):
            return None
        return cast(dict[str, Any], result)

    def _build_plan_events(self, run_id: str, plan_steps: list[PlanStep]) -> list[dict[str, Any]]:
        events = [
            {
                "type": "assistant_status",
                "run_id": run_id,
                "payload": {"value": "thinking"},
            },
            {
                "type": "plan_ready",
                "run_id": run_id,
                "payload": {
                    "steps": [
                        {
                            "title": step.title,
                            "command": step.command,
                            "reason": step.reason,
                            "risk_level": step.risk_level,
                            "working_directory": step.working_directory,
                            "expected_output": step.expected_output,
                        }
                        for step in plan_steps
                    ]
                },
            },
        ]
        if plan_steps:
            first_step = plan_steps[0]
            events.append(
                {
                    "type": "approval_requested",
                    "run_id": run_id,
                    "payload": {
                        "message": "Approve step 1?",
                        "step": {
                            "title": first_step.title,
                            "command": first_step.command,
                            "reason": first_step.reason,
                            "risk_level": first_step.risk_level,
                            "working_directory": first_step.working_directory,
                            "expected_output": first_step.expected_output,
                        },
                    },
                }
            )
        return events

    def _route_after_plan(self, state: AgentRunState) -> str:
        if not state["plan_steps"]:
            return "summarize_task"
        first_step = state["plan_steps"][0]
        if self._match_auto_approval(state, first_step) is not None:
            return "execute_step"
        return "request_step_approval"

    def _route_after_approval(self, state: AgentRunState) -> str:
        return "execute_step"

    def _route_after_execution(self, state: AgentRunState) -> str:
        if state["current_step_index"] >= len(state["plan_steps"]):
            return "summarize_task"
        next_step = state["plan_steps"][state["current_step_index"]]
        if self._match_auto_approval(state, next_step) is not None:
            return "execute_step"
        return "request_step_approval"

    def _collect_summary(self, run_id: str, events: list[dict[str, Any]], summary: str | Iterable[str]) -> str:
        if isinstance(summary, str):
            return summary

        events.append(
            {
                "type": "assistant_status",
                "run_id": run_id,
                "payload": {"value": "summarizing"},
            }
        )
        chunks: list[str] = []
        for chunk in summary:
            if not chunk:
                continue
            chunks.append(chunk)
            events.append(
                {
                    "type": "assistant_chunk",
                    "run_id": run_id,
                    "payload": {"chunk": chunk},
                }
            )
        return "".join(chunks)
