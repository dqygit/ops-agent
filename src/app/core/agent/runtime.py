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
    def __call__(self, step: PlanStep, emit=None) -> dict[str, Any]: ...


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
    approved: bool | None
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
    ):
        self._planner = planner
        self._step_executor = step_executor
        self._summarizer = summarizer
        self._persistence = persistence
        self._model_config = model_config
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
        builder.add_node("execute_plan", self._execute_plan)
        builder.add_edge(START, "plan_task")
        builder.add_edge("plan_task", "execute_plan")
        builder.add_edge("execute_plan", END)
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
            "execution_results": [],
            "assistant_message": None,
            "approved": None,
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
        plan_steps = state["plan_steps"]
        approved = interrupt(
            {
                "type": "approval_request",
                "run_id": state["run_id"],
                "plan_steps": [
                    {"title": step.title, "command": step.command, "reason": step.reason}
                    for step in plan_steps
                ],
                "message": "Approve this execution plan?",
            }
        )
        if self._persistence is not None and state["task_id"]:
            self._persistence.record_approval(task_id=state["task_id"], approved=bool(approved))
            self._persistence.update_task_status(
                task_id=state["task_id"],
                status=TaskStatus.APPROVED.value if approved else TaskStatus.REJECTED.value,
            )
        return {**state, "plan_steps": plan_steps, "approved": approved}

    def _execute_plan(self, state: AgentRunState) -> AgentRunState:
        events: list[dict[str, Any]] = []
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
                "execution_results": [],
                "assistant_message": "任务已取消",
                "ui_events": events,
            }

        if self._persistence is not None and state["task_id"]:
            self._persistence.update_task_status(task_id=state["task_id"], status=TaskStatus.RUNNING.value)
        events.append(
            {
                "type": "assistant_status",
                "run_id": state["run_id"],
                "payload": {"value": "executing"},
            }
        )
        execution_results: list[dict[str, Any]] = []
        for index, step in enumerate(state["plan_steps"]):
            step_id = state["step_ids"][index] if index < len(state["step_ids"]) else 0
            started_at = datetime.now(UTC)
            if self._persistence is not None and step_id:
                self._persistence.update_step(
                    step_id=step_id,
                    status=TaskStatus.RUNNING.value,
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
            execution_results.append(result)
            finished_at = datetime.now(UTC)
            if self._persistence is not None and step_id:
                self._persistence.update_step(
                    step_id=step_id,
                    status=TaskStatus.COMPLETED.value if result.get("exit_code", 0) == 0 else TaskStatus.FAILED.value,
                    output=result.get("output") or result.get("stdout", ""),
                    error_message=result.get("error") or result.get("stderr", ""),
                    finished_at=finished_at,
                )
            events.append(
                {
                    "type": "step_finished",
                    "run_id": state["run_id"],
                    "payload": result,
                }
            )

        self._record_model_usage(state)
        summary = self._summarizer(
            state["user_message"],
            execution_results,
            recent_messages=state["recent_messages"],
        )
        message = self._collect_summary(state["run_id"], events, summary)
        task_status = TaskStatus.COMPLETED.value
        if any((result.get("exit_code", 0) != 0) for result in execution_results):
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
        completed_state: AgentRunState = {
            **self._state_cache.get(state["run_id"], state),
            "approved": True,
            "execution_results": execution_results,
            "assistant_message": message,
            "ui_events": [],
        }
        self._state_cache[state["run_id"]] = completed_state
        return {
            **state,
            "approved": True,
            "execution_results": execution_results,
            "assistant_message": message,
            "ui_events": events,
        }

    def _build_plan_events(self, run_id: str, plan_steps: list[PlanStep]) -> list[dict[str, Any]]:
        return [
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
                        {"title": step.title, "command": step.command, "reason": step.reason}
                        for step in plan_steps
                    ]
                },
            },
            {
                "type": "approval_requested",
                "run_id": run_id,
                "payload": {"message": "Approve this execution plan?"},
            },
        ]

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
