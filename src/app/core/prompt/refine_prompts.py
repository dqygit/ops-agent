from __future__ import annotations

from app.core.llm.base import LLMCompletionRequest, LLMMessage
from app.shared.schemas import PlanStep


def build_refine_request(
    *,
    step: PlanStep,
    asset_summary: str,
    recent_output: str,
    shell_type: str,
    os_type: str,
) -> LLMCompletionRequest:
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
                    f"执行环境:\nshell_type={shell_type or 'unknown'}\nos_type={os_type or 'unknown'}\n\n"
                    f"最近终端输出:\n{recent_output or 'none'}\n\n"
                    f"当前步骤:\n标题:{step.title}\n命令:{step.command}\n原因:{step.reason}"
                ),
            ),
        ],
        temperature=0.1,
        json_mode=False,
    )
