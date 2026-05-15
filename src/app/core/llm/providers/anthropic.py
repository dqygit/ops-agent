from collections.abc import Iterator
from typing import Any, cast

from anthropic.types import JSONOutputFormatParam, TextBlockParam

from app.core.llm.base import LLMCompletionChunk, LLMCompletionRequest, LLMCompletionResponse
from app.core.tool import LLMToolCall
from app.shared.schemas import ModelConfig


class AnthropicLLMProvider:
    def __init__(self, client: Any = None):
        self._client = client


    def stream_complete(
        self,
        *,
        config: ModelConfig,
        request: LLMCompletionRequest,
    ) -> Iterator[LLMCompletionChunk]:
        with self._get_client(config).messages.stream(
            model=config.model_name,
            max_tokens=request.max_tokens if request.max_tokens is not None else config.max_tokens,
            temperature=request.temperature if request.temperature is not None else config.temperature,
            system=self._serialize_system_prompt(request),
            messages=cast(Any, self._serialize_messages(request)),
            tools=cast(Any, self._serialize_tools(request) or None),
            tool_choice=cast(Any, self._serialize_tool_choice(request)),
        ) as stream:
            for chunk in stream.text_stream:
                if isinstance(chunk, str) and chunk:
                    yield LLMCompletionChunk(delta=chunk)
            final_message = stream.get_final_message()
            yield LLMCompletionChunk(
                tool_calls=self._extract_tool_calls(getattr(final_message, "content", []) or []),
                finish_reason=getattr(final_message, "stop_reason", None),
            )

    def complete(
        self,
        *,
        config: ModelConfig,
        request: LLMCompletionRequest,
    ) -> LLMCompletionResponse:
        response = self._get_client(config).messages.create(
            model=config.model_name,
            max_tokens=request.max_tokens if request.max_tokens is not None else config.max_tokens,
            temperature=request.temperature if request.temperature is not None else config.temperature,
            system=self._serialize_system_prompt(request),
            messages=cast(Any, self._serialize_messages(request)),
            tools=cast(Any, self._serialize_tools(request) or None),
            tool_choice=cast(Any, self._serialize_tool_choice(request)),
        )
        text_parts: list[str] = []
        tool_calls: list[LLMToolCall] = []
        for block in getattr(response, "content", []) or []:
            block_type = getattr(block, "type", None)
            if block_type == "text":
                text = getattr(block, "text", None)
                if isinstance(text, str) and text:
                    text_parts.append(text)
            if block_type == "tool_use":
                tool_calls.append(
                    LLMToolCall(
                        id=getattr(block, "id", ""),
                        name=getattr(block, "name", ""),
                        arguments=getattr(block, "input", {}) if isinstance(getattr(block, "input", {}), dict) else {},
                    )
                )
        return LLMCompletionResponse(
            text="".join(text_parts),
            tool_calls=tool_calls,
            finish_reason=getattr(response, "stop_reason", None),
        )

    def _get_client(self, config: ModelConfig):
        if self._client is not None:
            return self._client
        from anthropic import Anthropic

        self._client = Anthropic(
            api_key=config.api_key.get_secret_value(),
            base_url=config.base_url,
            timeout=config.timeout_seconds,
        )
        return self._client

    def _serialize_messages(self, request: LLMCompletionRequest) -> list[dict[str, Any]]:
        messages: list[dict[str, Any]] = []
        breakpoint_index = self._find_cache_breakpoint(request)
        for index, message in enumerate(request.messages):
            if message.role == "system":
                continue
            if message.role == "user":
                messages.append({"role": "user", "content": self._serialize_text_content(message.content, request, cacheable=index == breakpoint_index)})
                continue
            if message.role == "assistant":
                if not message.tool_calls:
                    messages.append({"role": "assistant", "content": self._serialize_text_content(message.content, request, cacheable=index == breakpoint_index)})
                    continue
                content_blocks: list[dict[str, Any]] = []
                if message.content:
                    text_block: dict[str, Any] = {"type": "text", "text": message.content}
                    if index == breakpoint_index:
                        text_block["cache_control"] = self._build_cache_control(request)
                    content_blocks.append(text_block)
                for tool_call in message.tool_calls:
                    content_blocks.append(
                        {
                            "type": "tool_use",
                            "id": tool_call.id,
                            "name": tool_call.name,
                            "input": tool_call.arguments,
                        }
                    )
                messages.append({"role": "assistant", "content": content_blocks})
                continue
            if message.role == "tool":
                messages.append(
                    {
                        "role": "user",
                        "content": [
                            {
                                "type": "tool_result",
                                "tool_use_id": message.tool_call_id or "",
                                "content": message.content,
                            }
                        ],
                    }
                )
        return messages

    def _serialize_system_prompt(self, request: LLMCompletionRequest) -> list[TextBlockParam] | str:
        system_entries = [(index, message.content) for index, message in enumerate(request.messages) if message.role == "system" and message.content]
        if not system_entries:
            return ""
        breakpoint_index = self._find_cache_breakpoint(request)
        blocks: list[TextBlockParam] = []
        for index, content in system_entries:
            block: dict[str, Any] = {"type": "text", "text": content}
            if index == breakpoint_index:
                block["cache_control"] = self._build_cache_control(request)
            blocks.append(cast(TextBlockParam, block))
        if len(blocks) == 1 and breakpoint_index != system_entries[0][0]:
            return system_entries[0][1]
        return blocks

    def _serialize_tools(self, request: LLMCompletionRequest) -> list[dict[str, Any]]:
        return [
            {
                "name": tool.name,
                "description": tool.description,
                "input_schema": tool.input_schema,
            }
            for tool in sorted(request.tools, key=lambda item: item.name)
        ]

    def _find_cache_breakpoint(self, request: LLMCompletionRequest) -> int | None:
        if request.cache_policy is None or not request.cache_policy.enabled:
            return None
        for index in range(len(request.messages) - 1, -1, -1):
            message = request.messages[index]
            if self._message_supports_cache_marker(message):
                return index
        return None

    def _message_supports_cache_marker(self, message) -> bool:
        if self._resolve_cache_status(message) != "cacheable":
            return False
        if message.role == "system":
            return bool(message.content)
        if message.role == "user":
            return bool(message.content)
        if message.role == "assistant":
            return bool(message.content)
        return False

    def _resolve_cache_status(self, message) -> str:
        if message.cache_status != "inherit":
            return message.cache_status
        defaults = {
            "system": "cacheable",
            "history": "cacheable",
            "summary": "cacheable",
            "current_user": "volatile",
            "runtime_context": "volatile",
            "assistant_response": "volatile",
            "tool_result": "volatile",
        }
        return defaults.get(message.cache_segment, "volatile")

    def _build_cache_control(self, request: LLMCompletionRequest) -> dict[str, Any]:
        ttl = request.cache_policy.ttl if request.cache_policy is not None else "ephemeral"
        if ttl == "one_hour":
            return {"type": "ephemeral", "ttl": "1h"}
        return {"type": "ephemeral"}

    def _serialize_text_content(self, content: str, request: LLMCompletionRequest, *, cacheable: bool) -> Any:
        if not cacheable:
            return content
        return [{"type": "text", "text": content, "cache_control": self._build_cache_control(request)}]

    def _serialize_tool_choice(self, request: LLMCompletionRequest) -> Any:
        if request.tool_choice is None:
            return None
        if request.tool_choice.name:
            return {"type": "tool", "name": request.tool_choice.name}
        if request.tool_choice.mode == "required":
            return {"type": "any"}
        if request.tool_choice.mode == "none":
            return None
        return {"type": "auto"}

    def _extract_tool_calls(self, blocks: list[Any]) -> list[LLMToolCall]:
        tool_calls: list[LLMToolCall] = []
        for block in blocks:
            if getattr(block, "type", None) != "tool_use":
                continue
            raw_input = getattr(block, "input", {})
            tool_calls.append(
                LLMToolCall(
                    id=getattr(block, "id", ""),
                    name=getattr(block, "name", ""),
                    arguments=raw_input if isinstance(raw_input, dict) else {},
                )
            )
        return tool_calls
