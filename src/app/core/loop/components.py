from __future__ import annotations

from collections.abc import Iterator
from typing import Protocol

from app.core.connectors.execution import ExecutionContext, ExecutionResult
from app.core.llm.base import SupportsCompletion
from app.core.llm.factory import build_llm_provider
from app.core.llm.stream_filter import safe_load_json, stream_prose_until_marker
from app.core.prompt import (
    build_plan_request,
    build_refine_request,
    build_review_request,
)
from app.shared.schemas import ModelConfig, PlanStep


class PlannerPort(Protocol):
    def stream_build_plan(
        self,
        *,
        config: ModelConfig,
        user_input: str,
        asset_summary: str,
        recent_output: str,
        shell_type: str,
        os_type: str,
    ) -> Iterator[str | list[PlanStep]]: ...

    def stream_review_step_result(
        self,
        *,
        config: ModelConfig,
        user_input: str,
        current_step: PlanStep,
        command_output: str,
        remaining_steps: list[PlanStep],
    ) -> Iterator[str | "PlannerReviewResult"]: ...


class RefinerPort(Protocol):
    def stream_refine_step(
        self,
        *,
        config: ModelConfig,
        step: PlanStep,
        asset_summary: str,
        recent_output: str,
        shell_type: str,
        os_type: str,
    ) -> Iterator[str | PlanStep]: ...


class ExecutorPort(Protocol):
    def execute_step(
        self,
        *,
        session_manager,
        command: str,
        working_directory: str | None = None,
    ) -> ExecutionResult: ...


from dataclasses import dataclass


@dataclass
class PlannerReviewResult:
    decision: str
    summary: str


class LLMPlanner:
    """Streaming planner + reviewer powered by an LLM provider."""

    def __init__(self, provider: SupportsCompletion | None = None) -> None:
        self._provider = provider

    def stream_build_plan(
        self,
        *,
        config: ModelConfig,
        user_input: str,
        asset_summary: str,
        recent_output: str = "",
        shell_type: str = "unknown",
        os_type: str = "unknown",
    ) -> Iterator[str | list[PlanStep]]:
        provider = self._provider or build_llm_provider(config)
        request = build_plan_request(
            user_input=user_input,
            asset_summary=asset_summary,
            recent_output=recent_output,
            shell_type=shell_type,
            os_type=os_type,
        )
        text_parts: list[str] = []
        for delta in stream_prose_until_marker(provider=provider, config=config, request=request):
            text_parts.append(delta)
            yield delta
        yield self._parse_plan_steps("".join(text_parts))

    def stream_review_step_result(
        self,
        *,
        config: ModelConfig,
        user_input: str,
        current_step: PlanStep,
        command_output: str,
        remaining_steps: list[PlanStep],
    ) -> Iterator[str | PlannerReviewResult]:
        provider = self._provider or build_llm_provider(config)
        request = build_review_request(
            user_input=user_input,
            current_step=current_step,
            command_output=command_output,
            remaining_steps=remaining_steps,
        )
        text_parts: list[str] = []
        for delta in stream_prose_until_marker(provider=provider, config=config, request=request):
            text_parts.append(delta)
            yield delta
        payload = safe_load_json("".join(text_parts))
        decision = str(payload.get("decision") or ("complete" if not remaining_steps else "advance")).lower()
        if decision not in {"retry", "advance", "complete"}:
            decision = "complete" if not remaining_steps else "advance"
        summary = str(payload.get("summary") or "")
        yield PlannerReviewResult(decision=decision, summary=summary)

    def _parse_plan_steps(self, text: str) -> list[PlanStep]:
        payload = safe_load_json(text)
        raw_steps = payload.get("steps") if isinstance(payload, dict) else None
        steps: list[PlanStep] = []
        if isinstance(raw_steps, list):
            for item in raw_steps:
                if not isinstance(item, dict):
                    continue
                title = str(item.get("title") or "").strip()
                reason = str(item.get("reason") or "").strip()
                if not title:
                    continue
                steps.append(
                    PlanStep(
                        title=title,
                        command="",
                        reason=reason or title,
                        risk_level=str(item.get("risk_level") or "low"),
                        expected_output=str(item.get("expected_output") or ""),
                    )
                )
        if steps:
            return steps
        return [
            PlanStep(
                title="执行任务诊断",
                command="pwd && whoami && uname -a",
                reason="采集基础上下文，便于后续执行",
                risk_level="low",
                expected_output="当前目录、用户和系统信息",
            )
        ]


class LLMRefiner:
    """Streaming step-refiner powered by an LLM provider."""

    def __init__(self, provider: SupportsCompletion | None = None) -> None:
        self._provider = provider

    def stream_refine_step(
        self,
        *,
        config: ModelConfig,
        step: PlanStep,
        asset_summary: str,
        recent_output: str = "",
        shell_type: str = "unknown",
        os_type: str = "unknown",
    ) -> Iterator[str | PlanStep]:
        provider = self._provider or build_llm_provider(config)
        request = build_refine_request(
            step=step,
            asset_summary=asset_summary,
            recent_output=recent_output,
            shell_type=shell_type,
            os_type=os_type,
        )
        text_parts: list[str] = []
        for delta in stream_prose_until_marker(provider=provider, config=config, request=request):
            text_parts.append(delta)
            yield delta
        yield self._build_plan_step(step, "".join(text_parts))

    def _build_plan_step(self, step: PlanStep, text: str) -> PlanStep:
        payload = safe_load_json(text)
        command = str(payload.get("command") or step.command).strip()
        return PlanStep(
            title=str(payload.get("title") or step.title).strip() or step.title,
            command=command or step.command,
            reason=str(payload.get("reason") or step.reason).strip() or step.reason,
            risk_level=str(payload.get("risk_level") or step.risk_level or "low"),
            working_directory=str(payload.get("working_directory") or step.working_directory or ""),
            expected_output=str(payload.get("expected_output") or step.expected_output or ""),
        )


class TerminalExecutor:
    """Executes a refined step against a terminal session manager."""

    def execute_step(
        self,
        *,
        session_manager,
        command: str,
        working_directory: str | None = None,
    ) -> ExecutionResult:
        execution_id = session_manager.start_execution(
            command,
            ExecutionContext(working_directory=working_directory),
        )
        return session_manager.get_execution_result(execution_id)
