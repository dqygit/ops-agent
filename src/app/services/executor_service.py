import json
from collections.abc import Iterator

from app.integrations.llm.base import LLMCompletionRequest, LLMMessage, SupportsCompletion
from app.integrations.llm.factory import build_llm_provider
from app.shared.schemas import ModelConfig, PlanStep


class ExecutorService:
    def __init__(self, provider: SupportsCompletion | None = None):
        self._provider = provider

    def refine_step(
        self,
        *,
        config: ModelConfig,
        step: PlanStep,
        asset_summary: str,
        recent_output: str = "",
    ) -> PlanStep:
        provider = self._provider or build_llm_provider(config)
        response = provider.complete(
            config=config,
            request=self._build_refine_request(step=step, asset_summary=asset_summary, recent_output=recent_output),
        )
        return self._build_plan_step(step, response.text)

    def stream_refine_step(
        self,
        *,
        config: ModelConfig,
        step: PlanStep,
        asset_summary: str,
        recent_output: str = "",
    ) -> Iterator[str | PlanStep]:
        request = self._build_refine_request(step=step, asset_summary=asset_summary, recent_output=recent_output)
        text_parts: list[str] = []
        for delta in self._stream_response_text(config=config, request=request):
            text_parts.append(delta)
            yield delta
        yield self._build_plan_step(step, "".join(text_parts))

    def _build_refine_request(self, *, step: PlanStep, asset_summary: str, recent_output: str) -> LLMCompletionRequest:
        return LLMCompletionRequest(
            messages=[
                LLMMessage(
                    role="system",
                    content=(
                        "你是 Ops Executor。先用自然语言简短说明你准备如何执行当前步骤，不要输出 JSON。"
                        "说明结束后输出标记 <FINAL_JSON>，然后输出 JSON："
                        '{"title":str,"command":str,"reason":str,"risk_level":str,"working_directory":str,"expected_output":str}。'
                        "生成命令时必须默认适配非交互终端执行：不要输出需要人工翻页、按键确认、全屏界面或持续刷新的 TUI / pager / interactive 命令。"
                        "禁止生成 less、more、man、top、htop、watch、vim、vi、nano 等交互命令。"
                        "对于 systemctl、journalctl、git log 等常见会触发分页的命令，必须优先输出非交互形式，例如 systemctl --no-pager、journalctl --no-pager、git --no-pager，或配合 head、tail、grep、sed 限制输出范围。"
                    ),
                ),
                LLMMessage(
                    role="user",
                    content=(
                        f"资产上下文:\n{asset_summary or 'unknown'}\n\n"
                        f"最近终端输出:\n{recent_output or 'none'}\n\n"
                        f"当前步骤:\n标题:{step.title}\n命令:{step.command}\n原因:{step.reason}"
                    ),
                ),
            ],
            temperature=0.1,
            json_mode=False,
        )

    def _build_plan_step(self, step: PlanStep, text: str) -> PlanStep:
        payload = self._safe_load_json(text)
        command = str(payload.get("command") or step.command).strip()
        return PlanStep(
            title=str(payload.get("title") or step.title).strip() or step.title,
            command=command or step.command,
            reason=str(payload.get("reason") or step.reason).strip() or step.reason,
            risk_level=str(payload.get("risk_level") or step.risk_level or "low"),
            working_directory=str(payload.get("working_directory") or step.working_directory or ""),
            expected_output=str(payload.get("expected_output") or step.expected_output or ""),
        )

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
