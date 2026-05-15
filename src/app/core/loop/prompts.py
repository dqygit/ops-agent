from __future__ import annotations

from app.core.loop.loop_state import LoopContext, LoopRuntimeStep


def build_plan_step_system_prompt(ctx: LoopContext) -> str:
    device_context = f"\n\n设备执行规则:\n{ctx.device_context}" if ctx.device_context else ""
    return (
        f"操作系统类型: {ctx.os_type}\n"
        f"当前主机信息: {ctx.asset_summary}\n"
        f"Shell: {ctx.shell_type}\n"
        f"执行 Profile: {ctx.execution_profile}{device_context}\n\n"
        "You are an operations assistant executing a single plan step."
        "You can use the provided tools to perform actions."
        "Prioritize completing the current step, and directly provide a brief summary of the result once finished."
        "Respond in Chinese unless the user explicitly requests another language."
    )


def build_plan_step_user_prompt(ctx: LoopContext, step: LoopRuntimeStep) -> str:
    return (
        f"原始任务: {ctx.user_prompt}\n"
        f"当前步骤标题: {step.title}\n"
        f"当前步骤原因: {step.reason}\n"
        f"建议工作目录: {step.working_directory or '未指定'}\n"
        f"期望输出: {step.expected_output or '未指定'}\n"
        "请围绕当前步骤执行，必要时可以调整参数，但不要偏离该步骤目标。"
    )


def build_tool_calling_system_prompt(ctx: LoopContext) -> str:
    mode_instruction = (
        "你是一个谨慎的运维助手。你可以使用提供的工具执行操作。系统会自动根据策略判断操作是否可直接执行。"
        if ctx.mode == "plan"
        else "你是一个自主运维助手。你可以使用提供的工具执行操作。系统会自动根据策略判断操作是否可直接执行。"
    )
    device_context = f"\n设备执行规则:\n{ctx.device_context}\n" if ctx.device_context else "\n"
    return (
        f"操作系统类型: {ctx.os_type}\n"
        f"当前主机信息: {ctx.asset_summary}\n"
        f"Shell: {ctx.shell_type}\n"
        f"执行 Profile: {ctx.execution_profile}{device_context}\n"
        "Rules: " + mode_instruction + "\n"
        "When you need to check the environment or complete a task, call the corresponding tool directly."
        "Respond in Chinese unless the user explicitly requests another language."
    )
