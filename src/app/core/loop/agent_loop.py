"""Agent Loop 主编排器。

职责：
- 接受 LoopContext + 4 个 Port + TerminalSessionResolver
- 驱动 Plan → Refine → (Approval) → Execute → Review → Decision 循环
- yield LoopEvent；服务层负责把 LoopEvent 翻译为 SSE 字典 + 同步到 runtime_manager
- 暂停于审批；调用 resume_with_approval(state, approved) 继续
- 同时支持 agent / plan 两种模式
"""

from __future__ import annotations

import uuid
from collections.abc import Iterator
from typing import Any, Protocol

from app.core.loop.components import (
    ExecutorPort,
    PlannerPort,
    PlannerReviewResult,
    RefinerPort,
)
from app.core.loop.loop_events import (
    LoopEvent,
    emit_approval_granted,
    emit_approval_rejected,
    emit_approval_required,
    emit_completed,
    emit_decision_made,
    emit_delta,
    emit_execution_completed,
    emit_execution_output,
    emit_execution_started,
    emit_failed,
    emit_plan_updated,
    emit_planning_completed,
    emit_planning_failed,
    emit_planning_started,
    emit_replan_pending_approval,
)
from app.core.loop.loop_policy import MAX_STEP_RETRIES, needs_approval
from app.core.loop.loop_state import (
    LoopContext,
    LoopRuntimeStep,
    LoopState,
)
from app.shared.schemas import PlanStep


class TerminalSessionResolver(Protocol):
    """服务层提供的终端会话适配器：loop 不直接持有 TerminalService。"""

    def get_session(self, terminal_id: str) -> Any | None: ...

    def acquire_terminal_slot(self, runtime_id: str, terminal_id: str) -> bool: ...

    def release_terminal_slot(self, runtime_id: str, terminal_id: str) -> None: ...


# 兼容老导入；不再使用 callback 形式。
EventCallback = Any


class AgentLoop:
    """LLM 驱动的任务编排循环。

    使用方式：

        loop = AgentLoop(planner=..., refiner=..., executor=..., terminal=...)
        state = LoopState(phase="planning", context=context)
        for event in loop.run(state):
            ...  # 服务层翻译 event 为 SSE / 同步 runtime_manager

    审批暂停时 generator 自然结束。服务层稍后通过：

        for event in loop.resume_with_approval(state, approved=True):
            ...
    """

    def __init__(
        self,
        *,
        planner: PlannerPort,
        refiner: RefinerPort,
        executor: ExecutorPort,
        terminal: TerminalSessionResolver,
    ) -> None:
        self._planner = planner
        self._refiner = refiner
        self._executor = executor
        self._terminal = terminal

    # ------------------------------------------------------------------
    # Entry points
    # ------------------------------------------------------------------

    def run(self, state: LoopState) -> Iterator[LoopEvent]:
        if state.context.mode == "plan":
            yield from self._run_plan_mode(state)
        else:
            yield from self._run_agent_mode(state)

    def resume_with_approval(self, state: LoopState, *, approved: bool) -> Iterator[LoopEvent]:
        if state.phase not in {"approving", "replan_pending_approval"}:
            return
        current_step = state.get_current_step()
        if current_step is None:
            return

        if not approved:
            current_step.status = "pending"
            yield emit_approval_rejected(runtime_id=state.context.runtime_id, step_id=current_step.step_id)
            return

        yield emit_approval_granted(runtime_id=state.context.runtime_id, step_id=current_step.step_id)

        if state.phase == "replan_pending_approval" and state.pending_patch:
            patch = state.pending_patch
            current_step.command = str(patch.get("proposed_command") or current_step.command)
            state.pending_patch = None

        if state.context.mode == "plan":
            yield from self._continue_plan_mode_after_approval(state, current_step)
        else:
            yield from self._continue_agent_mode_after_approval(state, current_step)

    # ------------------------------------------------------------------
    # Agent mode
    # ------------------------------------------------------------------

    def _run_agent_mode(self, state: LoopState) -> Iterator[LoopEvent]:
        plan_steps, plan_events = self._collect_build_plan(state, message_stage="initial")
        yield from plan_events
        if plan_steps is None:
            return
        state.steps = self._materialize_steps(state, plan_steps)
        state.cursor = 0
        state.plan_version = 1
        yield emit_plan_updated(runtime_id=state.context.runtime_id, plan_payload=self._snapshot_plan(state))

        yield from self._agent_step_pump(state)

    def _continue_agent_mode_after_approval(
        self,
        state: LoopState,
        current_step: LoopRuntimeStep,
    ) -> Iterator[LoopEvent]:
        current_step.status = "running"
        state.phase = "executing"
        ok, _output = yield from self._execute_step(state, current_step)
        if not ok:
            current_step.status = "failed"
            return
        review = yield from self._review_step(state, current_step)
        yield from self._apply_agent_review(state, current_step, review)
        if state.is_terminal():
            return
        yield from self._agent_step_pump(state)

    def _agent_step_pump(self, state: LoopState) -> Iterator[LoopEvent]:
        while True:
            current_index = self._next_pending_index(state)
            if current_index is None:
                summary = "任务完成。"
                state.phase = "completed"
                state.summary = summary
                yield emit_completed(runtime_id=state.context.runtime_id, summary=summary)
                return

            state.cursor = current_index
            step = state.steps[current_index]
            refined, events = self._collect_refine_step(state, step)
            yield from events
            if refined is None:
                return
            self._apply_refined(step, refined)
            yield emit_plan_updated(runtime_id=state.context.runtime_id, plan_payload=self._snapshot_plan(state))

            if needs_approval(step.risk_level):
                step.status = "pending"
                state.phase = "approving"
                state.pending_approval_step_id = step.step_id
                yield emit_approval_required(
                    runtime_id=state.context.runtime_id,
                    step_id=step.step_id,
                    step_index=current_index,
                    command=step.command,
                    title=step.title,
                    reason=step.reason,
                    risk_level=step.risk_level,
                    working_directory=step.working_directory,
                    expected_output=step.expected_output,
                )
                return

            step.status = "running"
            state.phase = "executing"
            ok, _output = yield from self._execute_step(state, step)
            if not ok:
                step.status = "failed"
                return
            review = yield from self._review_step(state, step)
            yield from self._apply_agent_review(state, step, review)
            if state.is_terminal():
                return

    def _apply_agent_review(
        self,
        state: LoopState,
        step: LoopRuntimeStep,
        review: PlannerReviewResult,
    ) -> Iterator[LoopEvent]:
        yield emit_decision_made(
            runtime_id=state.context.runtime_id,
            step_id=step.step_id,
            decision=review.decision,
            summary=review.summary,
        )
        if review.decision == "complete":
            summary = review.summary or f"任务完成，最后执行步骤：{step.title}"
            state.phase = "completed"
            state.summary = summary
            yield emit_completed(runtime_id=state.context.runtime_id, summary=summary)
            return

        if review.decision == "retry":
            retry_count = state.retry_counts.get(step.step_id, 0) + 1
            state.retry_counts[step.step_id] = retry_count
            if retry_count >= MAX_STEP_RETRIES:
                step.status = "failed"
                error = f"步骤重试超过上限({MAX_STEP_RETRIES})：{step.title}"
                state.phase = "failed"
                state.error_message = error
                yield emit_failed(runtime_id=state.context.runtime_id, error=error)
                return
            step.status = "pending"
            return

        step.status = "completed"
        state.retry_counts.pop(step.step_id, None)
        state.cursor += 1
        if state.cursor >= len(state.steps):
            summary = review.summary or "任务完成。"
            state.phase = "completed"
            state.summary = summary
            yield emit_completed(runtime_id=state.context.runtime_id, summary=summary)

    # ------------------------------------------------------------------
    # Plan mode
    # ------------------------------------------------------------------

    def _run_plan_mode(self, state: LoopState) -> Iterator[LoopEvent]:
        plan_steps, plan_events = self._collect_build_plan(state, message_stage="plan-initial")
        yield from plan_events
        if plan_steps is None:
            return

        locked: list[LoopRuntimeStep] = []
        for index, plan_step in enumerate(plan_steps):
            step_id = f"{state.context.runtime_id}-step-{index + 1}"
            tmp_runtime_step = LoopRuntimeStep.from_plan_step(step_id=step_id, step=plan_step, status="pending")
            refined, events = self._collect_refine_step(state, tmp_runtime_step)
            yield from events
            if refined is None:
                return
            self._apply_refined(tmp_runtime_step, refined)
            locked.append(tmp_runtime_step)

        state.steps = locked
        state.cursor = 0
        state.plan_version = 1
        state.locked_plan = True
        yield emit_plan_updated(runtime_id=state.context.runtime_id, plan_payload=self._snapshot_plan(state))

        yield from self._plan_step_pump(state)

    def _continue_plan_mode_after_approval(
        self,
        state: LoopState,
        current_step: LoopRuntimeStep,
    ) -> Iterator[LoopEvent]:
        current_step.status = "running"
        state.phase = "executing"
        ok, _output = yield from self._execute_step(state, current_step)
        if not ok:
            current_step.status = "failed"
            return
        current_step.status = "completed"
        state.cursor += 1
        yield emit_plan_updated(runtime_id=state.context.runtime_id, plan_payload=self._snapshot_plan(state))
        yield from self._plan_step_pump(state)

    def _plan_step_pump(self, state: LoopState) -> Iterator[LoopEvent]:
        while state.cursor < len(state.steps):
            current = state.steps[state.cursor]
            refined, events = self._collect_refine_step(state, current)
            yield from events
            if refined is None:
                return

            if needs_approval(refined.risk_level):
                self._apply_refined(current, refined)
                current.status = "pending"
                state.phase = "approving"
                state.pending_approval_step_id = current.step_id
                yield emit_approval_required(
                    runtime_id=state.context.runtime_id,
                    step_id=current.step_id,
                    step_index=state.cursor,
                    command=current.command,
                    title=current.title,
                    reason=current.reason,
                    risk_level=current.risk_level,
                    working_directory=current.working_directory,
                    expected_output=current.expected_output,
                )
                return

            if self._plan_requires_replan(current, refined):
                state.phase = "replan_pending_approval"
                state.pending_approval_step_id = current.step_id
                state.pending_patch = {
                    "step_id": current.step_id,
                    "locked_command": current.command,
                    "proposed_command": refined.command,
                }
                yield emit_replan_pending_approval(
                    runtime_id=state.context.runtime_id,
                    step_id=current.step_id,
                    step_index=state.cursor,
                    locked_command=current.command,
                    proposed_command=refined.command,
                    title=refined.title,
                    risk_level=refined.risk_level,
                )
                return

            current.status = "running"
            state.phase = "executing"
            ok, _output = yield from self._execute_step(state, current)
            if not ok:
                current.status = "failed"
                return
            current.status = "completed"
            state.cursor += 1
            yield emit_plan_updated(runtime_id=state.context.runtime_id, plan_payload=self._snapshot_plan(state))

        summary = "任务完成。"
        state.phase = "completed"
        state.summary = summary
        yield emit_completed(runtime_id=state.context.runtime_id, summary=summary)

    def _plan_requires_replan(self, locked: LoopRuntimeStep, proposed: PlanStep) -> bool:
        if (proposed.command or "").strip() != (locked.command or "").strip():
            return True
        if (proposed.working_directory or "").strip() != (locked.working_directory or "").strip():
            return True
        if (proposed.risk_level or "low").strip() != (locked.risk_level or "low").strip():
            return True
        return False

    # ------------------------------------------------------------------
    # LLM helpers — collect deltas + final value
    # ------------------------------------------------------------------

    def _collect_build_plan(
        self,
        state: LoopState,
        *,
        message_stage: str,
    ) -> tuple[list[PlanStep] | None, list[LoopEvent]]:
        ctx = state.context
        events: list[LoopEvent] = [emit_planning_started(runtime_id=ctx.runtime_id)]
        message_id = f"message-plan-{message_stage}-{uuid.uuid4()}"
        steps: list[PlanStep] | None = None
        try:
            for chunk in self._planner.stream_build_plan(
                config=ctx.model_config,
                user_input=ctx.user_prompt,
                asset_summary=ctx.asset_summary,
                recent_output=ctx.recent_output,
                shell_type=ctx.shell_type,
                os_type=ctx.os_type,
            ):
                if isinstance(chunk, str):
                    events.append(
                        emit_delta(
                            runtime_id=ctx.runtime_id,
                            message_id=message_id,
                            stage="planner",
                            text=chunk,
                        )
                    )
                    continue
                steps = list(chunk)
        except Exception as exc:
            error = f"规划失败: {exc}"
            state.phase = "failed"
            state.error_message = error
            events.append(emit_planning_failed(runtime_id=ctx.runtime_id, error=error))
            events.append(emit_failed(runtime_id=ctx.runtime_id, error=error))
            return None, events

        if not steps:
            error = "未生成可执行计划，请补充更明确的任务目标。"
            state.phase = "failed"
            state.error_message = error
            events.append(emit_planning_failed(runtime_id=ctx.runtime_id, error=error))
            events.append(emit_failed(runtime_id=ctx.runtime_id, error=error))
            return None, events

        events.append(emit_planning_completed(runtime_id=ctx.runtime_id, steps_count=len(steps)))
        return steps, events

    def _collect_refine_step(
        self,
        state: LoopState,
        step: LoopRuntimeStep,
    ) -> tuple[PlanStep | None, list[LoopEvent]]:
        ctx = state.context
        events: list[LoopEvent] = []
        message_id = f"message-executor-{ctx.runtime_id}-{step.step_id}"
        refined: PlanStep | None = None
        try:
            for chunk in self._refiner.stream_refine_step(
                config=ctx.model_config,
                step=step.to_plan_step(),
                asset_summary=ctx.asset_summary,
                recent_output=state.last_output_excerpt or ctx.recent_output,
                shell_type=ctx.shell_type,
                os_type=ctx.os_type,
            ):
                if isinstance(chunk, str):
                    events.append(
                        emit_delta(
                            runtime_id=ctx.runtime_id,
                            message_id=message_id,
                            stage="executor",
                            text=chunk,
                        )
                    )
                    continue
                refined = chunk
        except Exception as exc:
            error = f"步骤精炼失败: {exc}"
            state.phase = "failed"
            state.error_message = error
            events.append(emit_failed(runtime_id=ctx.runtime_id, error=error))
            return None, events
        if refined is None:
            error = "执行器未返回精炼后的命令。"
            state.phase = "failed"
            state.error_message = error
            events.append(emit_failed(runtime_id=ctx.runtime_id, error=error))
            return None, events
        return refined, events

    def _review_step(
        self,
        state: LoopState,
        step: LoopRuntimeStep,
    ) -> Iterator[LoopEvent]:
        ctx = state.context
        message_id = f"message-review-{ctx.runtime_id}-{uuid.uuid4()}"
        review: PlannerReviewResult | None = None
        try:
            for chunk in self._planner.stream_review_step_result(
                config=ctx.model_config,
                user_input=ctx.user_prompt,
                current_step=step.to_plan_step(),
                command_output=step.output,
                remaining_steps=state.get_remaining_plan_steps(),
            ):
                if isinstance(chunk, str):
                    yield emit_delta(
                        runtime_id=ctx.runtime_id,
                        message_id=message_id,
                        stage="review",
                        text=chunk,
                    )
                    continue
                review = chunk  # type: ignore[assignment]
        except Exception:
            review = None
        if review is None:
            review = PlannerReviewResult(decision="advance", summary="")
        return review

    # ------------------------------------------------------------------
    # Execution
    # ------------------------------------------------------------------

    def _execute_step(
        self,
        state: LoopState,
        step: LoopRuntimeStep,
    ) -> Iterator[LoopEvent]:
        ctx = state.context
        terminal_id = ctx.terminal_id
        if terminal_id is None:
            error = "终端未连接，无法执行。"
            state.phase = "failed"
            state.error_message = error
            yield emit_failed(runtime_id=ctx.runtime_id, error=error)
            return False, ""
        if self._terminal.get_session(terminal_id) is None:
            error = "终端会话不存在，无法执行命令。"
            state.phase = "failed"
            state.error_message = error
            yield emit_failed(runtime_id=ctx.runtime_id, error=error)
            return False, ""
        if not self._terminal.acquire_terminal_slot(ctx.runtime_id, terminal_id):
            error = "当前终端已有其他任务在执行，请稍后再试。"
            state.phase = "failed"
            state.error_message = error
            yield emit_failed(runtime_id=ctx.runtime_id, error=error)
            return False, ""

        try:
            session_manager = self._terminal.get_session(terminal_id)
            try:
                execution = self._executor.execute_step(
                    session_manager=session_manager,
                    command=step.command,
                    working_directory=step.working_directory,
                )
            except Exception as exc:
                error = f"命令执行异常: {exc}"
                state.phase = "failed"
                state.error_message = error
                yield emit_failed(runtime_id=ctx.runtime_id, error=error)
                return False, ""

            command_id = execution.execution_id or step.step_id
            yield emit_execution_started(
                runtime_id=ctx.runtime_id,
                step_id=step.step_id,
                step_index=state.cursor,
                command_id=command_id,
                terminal_id=terminal_id,
                command=step.command,
                title=step.title,
            )

            step.output = execution.output
            step.exit_code = execution.exit_code
            state.last_output_excerpt = execution.output[-4000:] if execution.output else ""

            if execution.output:
                yield emit_execution_output(
                    runtime_id=ctx.runtime_id,
                    step_id=step.step_id,
                    command_id=command_id,
                    terminal_id=terminal_id,
                    text=execution.output,
                    stream="stdout",
                )

            success = execution.completed and execution.exit_code in {None, 0}
            yield emit_execution_completed(
                runtime_id=ctx.runtime_id,
                step_id=step.step_id,
                step_index=state.cursor,
                command_id=command_id,
                terminal_id=terminal_id,
                exit_code=execution.exit_code,
                completed=execution.completed,
                success=success,
            )
            return success, execution.output
        finally:
            self._terminal.release_terminal_slot(ctx.runtime_id, terminal_id)

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _materialize_steps(self, state: LoopState, plan_steps: list[PlanStep]) -> list[LoopRuntimeStep]:
        return [
            LoopRuntimeStep.from_plan_step(
                step_id=f"{state.context.runtime_id}-step-{index + 1}",
                step=step,
                status="pending",
            )
            for index, step in enumerate(plan_steps)
        ]

    def _apply_refined(self, step: LoopRuntimeStep, refined: PlanStep) -> None:
        step.title = refined.title
        step.command = refined.command
        step.reason = refined.reason
        step.risk_level = refined.risk_level
        step.working_directory = refined.working_directory or None
        step.expected_output = refined.expected_output or None

    def _next_pending_index(self, state: LoopState) -> int | None:
        for index, step in enumerate(state.steps):
            if step.status in {"pending", "running"}:
                return index
        return None

    def _snapshot_plan(self, state: LoopState) -> dict[str, Any]:
        rendered: list[dict[str, Any]] = []
        for index, step in enumerate(state.steps):
            status = step.status
            if state.cursor == index and step.status == "pending" and state.phase == "executing":
                status = "running"
            rendered.append(
                {
                    "id": step.step_id,
                    "title": step.title,
                    "summary": step.reason,
                    "status": status,
                }
            )
        return {
            "id": f"plan-{state.context.runtime_id}-v{state.plan_version}",
            "kind": "plan",
            "planId": f"runtime-{state.context.runtime_id}",
            "title": "Task Plan",
            "loading": False,
            "version": state.plan_version,
            "isLatest": True,
            "updated": state.plan_version > 1,
            "steps": rendered,
            "runtimeId": state.context.runtime_id,
            "mode": state.context.mode,
            "lockedPlan": state.locked_plan,
        }
