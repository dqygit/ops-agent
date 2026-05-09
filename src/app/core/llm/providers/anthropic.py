from collections.abc import Iterator
from typing import Any, cast

from anthropic.types import JSONOutputFormatParam

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
        system_prompt = next((message.content for message in request.messages if message.role == "system"), "")
        with self._get_client(config).messages.stream(
            model=config.model_name,
            max_tokens=request.max_tokens if request.max_tokens is not None else config.max_tokens,
            temperature=request.temperature if request.temperature is not None else config.temperature,
            system=system_prompt,
            messages=cast(Any, self._serialize_messages(request)),
            tools=cast(Any, self._serialize_tools(request) or None),
            tool_choice=cast(Any, self._serialize_tool_choice(request)),
        ) as stream:
            for chunk in stream.text_stream:
                if isinstance(chunk, str) and chunk:
                    yield LLMCompletionChunk(delta=chunk)
            yield LLMCompletionChunk(finish_reason=getattr(stream.get_final_message(), "stop_reason", None))

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
        for message in request.messages:
            if message.role == "system":
                continue
            payload: dict[str, Any] = {"role": message.role, "content": message.content}
            if message.role == "tool":
                payload["role"] = "user"
            messages.append(payload)
        return messages

    def _serialize_tools(self, request: LLMCompletionRequest) -> list[dict[str, Any]]:
        return [
            {
                "name": tool.name,
                "description": tool.description,
                "input_schema": tool.input_schema,
            }
            for tool in request.tools
        ]

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
