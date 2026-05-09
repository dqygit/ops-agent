import json
from collections.abc import Iterator
from typing import Any, cast

from app.core.llm.base import LLMCompletionChunk, LLMCompletionRequest, LLMCompletionResponse
from app.core.tool import LLMToolCall
from app.shared.schemas import ModelConfig


class OpenAICompatibleLLMProvider:
    def __init__(self, client: Any = None):
        self._client = client

  
    def stream_complete(
        self,
        *,
        config: ModelConfig,
        request: LLMCompletionRequest,
    ) -> Iterator[LLMCompletionChunk]:
        response = self._get_client(config).chat.completions.create(
            **self._build_completion_params(config=config, request=request, stream=True)
        )
        finish_reason: str | None = None
        for chunk in response:
            if not chunk.choices:
                continue
            choice = chunk.choices[0]
            finish_reason = getattr(choice, "finish_reason", finish_reason)
            delta = getattr(choice, "delta", None)
            text = getattr(delta, "content", None)
            if isinstance(text, str) and text:
                yield LLMCompletionChunk(delta=text)
        yield LLMCompletionChunk(finish_reason=finish_reason)

    def complete(
        self,
        *,
        config: ModelConfig,
        request: LLMCompletionRequest,
    ) -> LLMCompletionResponse:
        response = self._get_client(config).chat.completions.create(
            **self._build_completion_params(config=config, request=request, stream=False)
        )
        choice = response.choices[0] if getattr(response, "choices", None) else None
        message = getattr(choice, "message", None)
        text = getattr(message, "content", "") or ""
        tool_calls = self._parse_tool_calls(getattr(message, "tool_calls", None))
        finish_reason = getattr(choice, "finish_reason", None)
        return LLMCompletionResponse(text=text, tool_calls=tool_calls, finish_reason=finish_reason)

    def _build_completion_params(self, *, config: ModelConfig, request: LLMCompletionRequest, stream: bool) -> dict[str, Any]:
        params: dict[str, Any] = {
            "model": config.model_name,
            "temperature": request.temperature if request.temperature is not None else config.temperature,
            "max_tokens": request.max_tokens if request.max_tokens is not None else config.max_tokens,
            "messages": cast(Any, [self._serialize_message(message) for message in request.messages]),
            "tools": cast(Any, self._serialize_tools(request) or None),
            "tool_choice": cast(Any, self._serialize_tool_choice(request)),
            "stream": stream,
        }
        if request.json_mode:
            params["response_format"] = {"type": "json_object"}
        return params

    def _get_client(self, config: ModelConfig):
        if self._client is not None:
            return self._client
        from openai import OpenAI

        self._client = OpenAI(
            api_key=config.api_key.get_secret_value(),
            base_url=config.base_url,
            timeout=config.timeout_seconds,
        )
        return self._client

    def _serialize_message(self, message):
        payload = {"role": message.role, "content": message.content}
        if message.tool_call_id:
            payload["tool_call_id"] = message.tool_call_id
        if message.name:
            payload["name"] = message.name
        return payload

    def _serialize_tools(self, request: LLMCompletionRequest) -> list[dict[str, Any]]:
        return [
            {
                "type": "function",
                "function": {
                    "name": tool.name,
                    "description": tool.description,
                    "parameters": tool.input_schema,
                },
            }
            for tool in request.tools
        ]

    def _serialize_tool_choice(self, request: LLMCompletionRequest) -> Any:
        if request.tool_choice is None:
            return None
        if request.tool_choice.name:
            return {"type": "function", "function": {"name": request.tool_choice.name}}
        return request.tool_choice.mode

    def _parse_tool_calls(self, tool_calls: Any) -> list[LLMToolCall]:
        parsed: list[LLMToolCall] = []
        for tool_call in tool_calls or []:
            function = getattr(tool_call, "function", None)
            raw_arguments = getattr(function, "arguments", None)
            arguments = self._safe_load_arguments(raw_arguments)
            parsed.append(
                LLMToolCall(
                    id=getattr(tool_call, "id", ""),
                    name=getattr(function, "name", ""),
                    arguments=arguments,
                    raw_arguments=raw_arguments if isinstance(raw_arguments, str) else None,
                )
            )
        return parsed

    def _safe_load_arguments(self, raw_arguments: Any) -> dict[str, Any]:
        if not isinstance(raw_arguments, str) or not raw_arguments:
            return {}
        try:
            value = json.loads(raw_arguments)
        except json.JSONDecodeError:
            return {}
        return value if isinstance(value, dict) else {}
