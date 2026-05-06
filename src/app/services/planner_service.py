import json
from collections.abc import Callable, Iterator
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
        on_delta: Callable[[str], None] | None = None,
    ) -> list[PlanStep]:
        provider = self._provider or build_llm_provider(config)
        request = self._build_plan_request(user_input=user_input, asset_summary=asset_summary, recent_output=recent_output)
        text = self._stream_response_text(config=config, request=request, on_delta=on_delta)
        return self._parse_plan_steps(text)

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
        decision = str(payload.get("decision") or ("complete" if not remaining_steps else "continue")).lower()
        if decision not in {"continue", "complete"}:
            decision = "complete" if not remaining_steps else "continue"
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
        on_delta: Callable[[str], None] | None = None,
    ) -> PlannerReviewResult:
        provider = self._provider or build_llm_provider(config)
        request = self._build_review_request(
            user_input=user_input,
            current_step=current_step,
            command_output=command_output,
            remaining_steps=remaining_steps,
        )
        text = self._stream_response_text(config=config, request=request, on_delta=on_delta)
        payload = self._safe_load_json(text)
        decision = str(payload.get("decision") or ("complete" if not remaining_steps else "continue")).lower()
        if decision not in {"continue", "complete"}:
            decision = "complete" if not remaining_steps else "continue"
        summary = str(payload.get("summary") or "")
        return PlannerReviewResult(decision=decision, summary=summary)

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
                        '最后输出 JSON：{"decision":"continue|complete","summary":str}。'
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

    def _stream_response_text(self, *, config: ModelConfig, request: LLMCompletionRequest, on_delta: Callable[[str], None] | None = None) -> str:
        provider = self._provider or build_llm_provider(config)
        marker = "<FINAL_JSON>"
        text_parts: list[str] = []
        visible_buffer = ""
        marker_seen = False
        for chunk in getattr(provider, "stream_complete")(config=config, request=request):
            if not chunk.delta:
                continue
            text_parts.append(chunk.delta)
            if marker_seen:
                continue
            visible_buffer += chunk.delta
            marker_index = visible_buffer.find(marker)
            if marker_index >= 0:
                prose = visible_buffer[:marker_index]
                if prose and on_delta is not None:
                    on_delta(prose)
                visible_buffer = ""
                marker_seen = True
                continue
            safe_length = max(0, len(visible_buffer) - len(marker))
            if safe_length > 0:
                prose = visible_buffer[:safe_length]
                if prose and on_delta is not None:
                    on_delta(prose)
                visible_buffer = visible_buffer[safe_length:]
        if not marker_seen and visible_buffer and on_delta is not None:
            on_delta(visible_buffer)
        return "".join(text_parts)
