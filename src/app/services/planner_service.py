import json
from collections.abc import Iterator
from dataclasses import dataclass

from app.integrations.llm.base import LLMCompletionRequest, LLMMessage, SupportsCompletion
from app.integrations.llm.factory import build_llm_provider
from app.shared.schemas import ModelConfig, PlanStep


@dataclass
class PlannerReviewResult:
    decision: str
    summary: str


class PlannerService:
    def __init__(self, provider: SupportsCompletion | None = None):
        self._provider = provider

    def build_plan(self, *, config: ModelConfig, user_input: str, asset_summary: str, recent_output: str = "") -> list[PlanStep]:
        provider = self._provider or build_llm_provider(config)
        response = provider.complete(
            config=config,
            request=self._build_plan_request(user_input=user_input, asset_summary=asset_summary, recent_output=recent_output),
        )
        return self._parse_plan_steps(response.text)

    def stream_build_plan(
        self,
        *,
        config: ModelConfig,
        user_input: str,
        asset_summary: str,
        recent_output: str = "",
    ) -> Iterator[str | list[PlanStep]]:
        request = self._build_plan_request(user_input=user_input, asset_summary=asset_summary, recent_output=recent_output)
        text_parts: list[str] = []
        for delta in self._stream_response_text(config=config, request=request):
            text_parts.append(delta)
            yield delta
        yield self._parse_plan_steps("".join(text_parts))

    def review_step_result(
        self,
        *,
        config: ModelConfig,
        user_input: str,
        current_step: PlanStep,
        command_output: str,
        remaining_steps: list[PlanStep],
    ) -> PlannerReviewResult:
        provider = self._provider or build_llm_provider(config)
        response = provider.complete(
            config=config,
            request=self._build_review_request(
                user_input=user_input,
                current_step=current_step,
                command_output=command_output,
                remaining_steps=remaining_steps,
            ),
        )
        payload = self._safe_load_json(response.text)
        decision = str(payload.get("decision") or ("complete" if not remaining_steps else "advance")).lower()
        if decision not in {"retry", "advance", "complete"}:
            decision = "complete" if not remaining_steps else "advance"
        summary = str(payload.get("summary") or "")
        return PlannerReviewResult(decision=decision, summary=summary)

    def stream_review_step_result(
        self,
        *,
        config: ModelConfig,
        user_input: str,
        current_step: PlanStep,
        command_output: str,
        remaining_steps: list[PlanStep],
    ) -> Iterator[str | PlannerReviewResult]:
        request = self._build_review_request(
            user_input=user_input,
            current_step=current_step,
            command_output=command_output,
            remaining_steps=remaining_steps,
        )
        text_parts: list[str] = []
        for delta in self._stream_response_text(config=config, request=request):
            text_parts.append(delta)
            yield delta
        payload = self._safe_load_json("".join(text_parts))
        decision = str(payload.get("decision") or ("complete" if not remaining_steps else "advance")).lower()
        if decision not in {"retry", "advance", "complete"}:
            decision = "complete" if not remaining_steps else "advance"
        summary = str(payload.get("summary") or "")
        yield PlannerReviewResult(decision=decision, summary=summary)

    def _build_plan_request(self, *, user_input: str, asset_summary: str, recent_output: str) -> LLMCompletionRequest:
        return LLMCompletionRequest(
            messages=[
                LLMMessage(
                    role="system",
                    content=(
                        "你是 Ops Planner。先用自然语言简短说明你如何拆解任务，语气像在和用户解释，不要输出 JSON。"
                        "自然语言说明结束后，单独输出标记 <FINAL_JSON>，然后输出 JSON："
                        '{"steps":[{"title":str,"reason":str,"risk_level":str,"expected_output":str}]}'
                        "。plan 阶段不要生成 command、working_directory。risk_level 只能是 low、medium、high。"
                    ),
                ),
                LLMMessage(
                    role="user",
                    content=(
                        f"资产上下文:\n{asset_summary or 'unknown'}\n\n"
                        f"最近终端输出:\n{recent_output or 'none'}\n\n"
                        f"用户任务:\n{user_input}"
                    ),
                ),
            ],
            temperature=0.1,
        )

    def _build_review_request(
        self,
        *,
        user_input: str,
        current_step: PlanStep,
        command_output: str,
        remaining_steps: list[PlanStep],
    ) -> LLMCompletionRequest:
        return LLMCompletionRequest(
            messages=[
                LLMMessage(
                    role="system",
                    content=(
                        "你是 Ops Planner。先用自然语言简短说明你如何判断当前结果，再输出标记 <FINAL_JSON>，"
                        '最后输出 JSON：{"decision":"retry|advance|complete","summary":str}。'
                        "当当前步骤执行结果有问题需要重新生成命令并再次审批时用 retry；"
                        "当前步骤通过且应继续下一个步骤时用 advance；"
                        "全部步骤完成时用 complete。"
                    ),
                ),
                LLMMessage(
                    role="user",
                    content=(
                        f"用户任务:\n{user_input}\n\n"
                        f"当前步骤:{current_step.title}\n命令:{current_step.command}\n\n"
                        f"输出:\n{command_output or 'no output'}\n\n"
                        f"剩余步骤数:{len(remaining_steps)}"
                    ),
                ),
            ],
            temperature=0.1,
        )

    def summarize_task_result(
        self,
        *,
        config: ModelConfig,
        user_input: str,
        completed_steps: list[PlanStep],
        execution_history: list[dict[str, str]],
    ) -> str:
        provider = self._provider or build_llm_provider(config)
        response = provider.complete(
            config=config,
            request=self._build_summary_request(
                user_input=user_input,
                completed_steps=completed_steps,
                execution_history=execution_history,
            ),
        )
        return response.text.strip()

    def _build_summary_request(
        self,
        *,
        user_input: str,
        completed_steps: list[PlanStep],
        execution_history: list[dict[str, str]],
    ) -> LLMCompletionRequest:
        steps_text = "\n".join(
            f"- {index + 1}. {step.title} | command={step.command} | expected={step.expected_output}"
            for index, step in enumerate(completed_steps)
        ) or "- 无"
        history_text = "\n".join(
            f"- step={item.get('step','')} | command={item.get('command','')} | output={item.get('output','')[:500]}"
            for item in execution_history
        ) or "- 无"
        return LLMCompletionRequest(
            messages=[
                LLMMessage(
                    role="system",
                    content=(
                        "你是 Ops 总结助手。请基于任务目标和执行历史，输出简洁中文总结。"
                        "必须包含：任务是否完成、关键执行动作、关键结果、风险或后续建议。"
                        "只输出自然语言，不要 JSON。"
                    ),
                ),
                LLMMessage(
                    role="user",
                    content=(
                        f"用户任务:\n{user_input}\n\n"
                        f"已完成步骤:\n{steps_text}\n\n"
                        f"执行历史:\n{history_text}"
                    ),
                ),
            ],
            temperature=0.2,
        )

    def _parse_plan_steps(self, text: str) -> list[PlanStep]:
        payload = self._safe_load_json(text)
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

    def _safe_load_json(self, text: str) -> dict:
        if not text:
            return {}
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            start = text.find("{")
            end = text.rfind("}")
            if start >= 0 and end > start:
                try:
                    return json.loads(text[start : end + 1])
                except json.JSONDecodeError:
                    return {}
            return {}

    def _stream_response_text(self, *, config: ModelConfig, request: LLMCompletionRequest) -> Iterator[str]:
        provider = self._provider or build_llm_provider(config)
        marker = "<FINAL_JSON>"
        visible_buffer = ""
        marker_seen = False
        for chunk in getattr(provider, "stream_complete")(config=config, request=request):
            if not chunk.delta:
                continue
            if marker_seen:
                yield chunk.delta
                continue
            visible_buffer += chunk.delta
            marker_index = visible_buffer.find(marker)
            if marker_index >= 0:
                prose = visible_buffer[:marker_index]
                if prose:
                    yield prose
                visible_buffer = visible_buffer[marker_index + len(marker):]
                marker_seen = True
                if visible_buffer:
                    yield visible_buffer
                    visible_buffer = ""
                continue
            safe_length = max(0, len(visible_buffer) - len(marker))
            if safe_length > 0:
                prose = visible_buffer[:safe_length]
                if prose:
                    yield prose
                visible_buffer = visible_buffer[safe_length:]
        if not marker_seen and visible_buffer:
            yield visible_buffer
