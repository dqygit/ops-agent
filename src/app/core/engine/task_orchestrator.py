from collections.abc import Iterator
from dataclasses import dataclass

from sqlmodel import Session

from app.services.executor_service import ExecutorService
from app.services.model_service import ModelService
from app.services.planner_service import PlannerService
from app.services.terminal_service import TerminalService

from .task_state_machine import TaskStateMachine
from .task_use_cases_approval import TaskApprovalUseCase
from .task_use_cases_base import TaskUseCaseDependencies
from .task_use_cases_run import TaskRunUseCase


@dataclass
class OrchestratorDependencies:
    planner: PlannerService
    executor: ExecutorService
    model_service: ModelService
    terminal_service: TerminalService


class TaskOrchestrator:
    def __init__(self, deps: OrchestratorDependencies):
        use_case_deps = TaskUseCaseDependencies(
            planner=deps.planner,
            executor=deps.executor,
            model_service=deps.model_service,
            terminal_service=deps.terminal_service,
            state_machine=TaskStateMachine(),
        )
        self._run_use_case = TaskRunUseCase(use_case_deps)
        self._approval_use_case = TaskApprovalUseCase(use_case_deps)

    def stream_run(self, *, session: Session, prompt: str, asset_id: int, terminal_id: str | None = None, model_name: str | None = None, conversation_id: str = "console") -> Iterator[dict]:
        yield from self._run_use_case.execute(
            session=session,
            prompt=prompt,
            asset_id=asset_id,
            terminal_id=terminal_id,
            model_name=model_name,
            conversation_id=conversation_id,
        )

    def stream_approve(self, *, session: Session, run_id: str, approved: bool) -> Iterator[dict]:
        yield from self._approval_use_case.execute(session=session, run_id=run_id, approved=approved)
