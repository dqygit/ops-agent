from __future__ import annotations

from dataclasses import replace

from app.core.llm.types import LLMCompletionRequest, LLMMessage, LLMPromptCachePolicy
from app.core.loop.loop_state import LoopContext, LoopRuntimeStep, LoopState
from app.core.loop.prompts import (
    build_manual_skill_system_prompt,
    build_plan_step_system_prompt,
    build_plan_step_user_prompt,
    build_planner_skill_index_prompt,
    build_tool_calling_system_prompt,
)
from app.core.tool.schema import LLMToolDefinition


class AgentLLMRequestBuilder:
    def build_plan_summary_request(self, *, state: LoopState, step_lines: list[str]) -> LLMCompletionRequest:
        ctx = state.context
        messages = [
            self._make_system_message(
                "You are an operations assistant. Summarize the completed plan for the user. "
                "Be concise, mention what was done, important results, and any recommended next action. "
                "Respond in Chinese unless the user explicitly requests another language."
            ),
            LLMMessage(
                role="user",
                content=(
                    f"Original task: {ctx.user_prompt}\n\n"
                    "Completed plan steps:\n"
                    + ("\n".join(step_lines) if step_lines else "No step details were recorded.")
                ),
                cache_segment="current_user",
                cache_status="volatile",
            ),
        ]
        return LLMCompletionRequest(messages=messages, json_mode=False, cache_policy=self._cache_policy(ctx))

    def build_plan_generation_request(self, *, state: LoopState) -> LLMCompletionRequest:
        ctx = state.context
        device_rules = ""
        if ctx.device_context:
            device_rules = "设备执行规则:\n" + ctx.device_context + "\n"
        messages = [
            self._make_system_message(
                "You are an operations task planner. Please generate a task plan based on the user's goal."
                'Return a JSON object in the format {"steps": [...]}. '
                "The steps array must contain at least one step."
                "Each step includes title, reason, working_directory, expected_output, and risk_level."
                "Do not include commands in the plan. Output only raw JSON. Do not wrap it in markdown code fences or add any explanation."
            )
        ]
        planner_skill_prompt = build_planner_skill_index_prompt(ctx)
        if planner_skill_prompt:
            messages.append(self._make_system_message(planner_skill_prompt))
        manual_skill_prompt = build_manual_skill_system_prompt(ctx)
        if manual_skill_prompt:
            messages.append(self._make_system_message(manual_skill_prompt))
        messages.extend(self._annotate_history_messages(ctx.conversation_history))
        messages.append(
            LLMMessage(
                role="user",
                content=(
                    f"Operating System Type: {ctx.os_type}\n"
                    f"Current Host Information: {ctx.asset_summary}\n"
                    f"Shell: {ctx.shell_type}\n"
                    f"Execution Profile: {ctx.execution_profile}\n"
                    f"{device_rules}"
                    f"User Task: {ctx.user_prompt}"
                ),
                cache_segment="current_user",
                cache_status="volatile",
            )
        )
        return LLMCompletionRequest(messages=messages, json_mode=True, cache_policy=self._cache_policy(ctx))

    def build_plan_step_messages(self, *, state: LoopState, step: LoopRuntimeStep) -> list[LLMMessage]:
        ctx = state.context
        messages = [self._make_system_message(build_plan_step_system_prompt(ctx))]
        manual_skill_prompt = build_manual_skill_system_prompt(ctx)
        if manual_skill_prompt:
            messages.append(self._make_system_message(manual_skill_prompt))
        messages.extend(self._annotate_history_messages(ctx.conversation_history))
        messages.append(
            LLMMessage(
                role="user",
                content=build_plan_step_user_prompt(ctx, step),
                cache_segment="current_user",
                cache_status="volatile",
            )
        )
        return messages

    def build_tool_calling_request(self, *, state: LoopState, tools: list[LLMToolDefinition]) -> LLMCompletionRequest:
        messages = self._annotate_state_messages(state)
        sorted_tools = sorted(tools, key=lambda tool: tool.name)
        return LLMCompletionRequest(
            messages=messages,
            tools=sorted_tools,
            json_mode=False,
            cache_policy=self._cache_policy(state.context),
        )

    def build_initial_tool_calling_messages(self, *, state: LoopState) -> list[LLMMessage]:
        ctx = state.context
        messages = [self._make_system_message(build_tool_calling_system_prompt(ctx))]
        manual_skill_prompt = build_manual_skill_system_prompt(ctx)
        if manual_skill_prompt:
            messages.append(self._make_system_message(manual_skill_prompt))
        messages.extend(self._annotate_history_messages(ctx.conversation_history))
        messages.append(
            LLMMessage(
                role="user",
                content=ctx.user_prompt,
                cache_segment="current_user",
                cache_status="volatile",
            )
        )
        return messages

    def _annotate_state_messages(self, state: LoopState) -> list[LLMMessage]:
        messages: list[LLMMessage] = []
        last_user_index = max((index for index, message in enumerate(state.messages) if message.role == "user"), default=-1)
        for index, message in enumerate(state.messages):
            if message.role == "system":
                messages.append(self._apply_cache_metadata(message, segment="system", status="cacheable"))
                continue
            if index == last_user_index and not self._has_followup_content(state.messages, index):
                messages.append(self._apply_cache_metadata(message, segment="current_user", status="volatile"))
                continue
            messages.append(self._apply_cache_metadata(message, segment="history", status="cacheable"))
        return messages

    def _annotate_history_messages(self, messages: list[LLMMessage]) -> list[LLMMessage]:
        return [self._apply_cache_metadata(message, segment="history", status="cacheable") for message in messages]

    def _has_followup_content(self, messages: list[LLMMessage], user_index: int) -> bool:
        return any(message.role in {"assistant", "tool"} for message in messages[user_index + 1 :])

    def _make_system_message(self, content: str) -> LLMMessage:
        return LLMMessage(role="system", content=content, cache_segment="system", cache_status="cacheable")

    def _cache_policy(self, ctx: LoopContext) -> LLMPromptCachePolicy:
        return LLMPromptCachePolicy(
            enabled=ctx.model_config.prompt_cache_enabled,
            ttl=ctx.model_config.prompt_cache_ttl,
        )

    def _apply_cache_metadata(self, message: LLMMessage, *, segment: str, status: str) -> LLMMessage:
        return replace(message, cache_segment=segment, cache_status=status)
