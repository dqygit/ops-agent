from __future__ import annotations

from app.core.llm.base import LLMCompletionRequest, LLMMessage
from app.shared.schemas import PlanStep


def build_plan_request(
    *,
    user_input: str,
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
                    "作为运维任务规划助手，请先用自然语言简短说明如何拆解任务，然后输出标记 <FINAL_JSON>，最后输出 JSON 格式的执行计划。"
                    "\n\nJSON 格式："
                    '\n{"steps":[{"title":"步骤标题","reason":"执行原因","risk_level":"风险等级","expected_output":"预期输出"}]}'
                    "\n\n要求："
                    "\n- risk_level 只能是 low、medium、high"
                    "\n- 规划阶段不生成 command 和 working_directory"
                    "\n- 所有步骤适配非交互式终端"
                    "\n- 避免交互命令（less、more、man、top、htop、watch、vim、vi、nano）"
                    "\n- 对于可能分页的命令使用非交互形式（--no-pager、tail、head、sed、grep）"
                ),
            ),
            LLMMessage(
                role="user",
                content=(
                    f"资产上下文:\n{asset_summary or 'unknown'}\n\n"
                    f"执行环境:\nshell_type={shell_type or 'unknown'}\nos_type={os_type or 'unknown'}\n\n"
                    f"最近终端输出:\n{recent_output or 'none'}\n\n"
                    f"用户任务:\n{user_input}"
                ),
            ),
        ],
        temperature=0.1,
        json_mode=False,
    )


def build_review_request(
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
                    "作为运维任务评估助手，请先用自然语言简短说明如何判断当前结果，再输出标记 <FINAL_JSON>，"
                    '最后输出 JSON：{"decision":"retry|advance|complete","summary":"总结"}。'
                    "\n\n决策说明："
                    "\n- retry: 当前步骤有问题，需要重新生成命令"
                    "\n- advance: 当前步骤通过，继续下一步"
                    "\n- complete: 全部步骤完成"
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
        json_mode=False,
    )


def build_summary_request(
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
                    "作为运维任务总结助手，请基于任务目标和执行历史输出简洁的中文总结。"
                    "\n\n总结应包含："
                    "\n- 任务是否完成"
                    "\n- 关键执行动作"
                    "\n- 关键结果"
                    "\n- 风险或后续建议"
                    "\n\n只输出自然语言，不要 JSON 格式。"
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
        json_mode=False,
    )
