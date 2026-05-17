import importlib
import json
from collections.abc import Iterator
from typing import Any

from app.core.llm.base import LLMCompletionChunk, LLMCompletionRequest, LLMCompletionResponse
from app.core.tool import LLMToolCall
from app.shared.schemas import ModelConfig


class GoogleGeminiLLMProvider:
    def __init__(self, client: Any = None, types_module: Any = None):
        self._client = client
        self._types = types_module

    def stream_complete(
        self,
        *,
        config: ModelConfig,
        request: LLMCompletionRequest,
    ) -> Iterator[LLMCompletionChunk]:
        stream = self._get_client(config).models.generate_content_stream(
            model=config.model_name,
            contents=self._serialize_contents(request),
            config=self._build_generate_config(config=config, request=request),
        )
        function_calls: dict[str, dict[str, Any]] = {}
        finish_reason: str | None = None
        thinking_parts: list[str] = []
        for chunk in stream:
            text = getattr(chunk, "text", None)
            if isinstance(text, str) and text:
                yield LLMCompletionChunk(delta=text)
            self._merge_function_calls(function_calls, chunk)
            thinking = self._extract_thinking(chunk)
            if thinking:
                thinking_parts.append(thinking)
                yield LLMCompletionChunk(thinking_delta=thinking)
            finish_reason = self._extract_finish_reason(chunk) or finish_reason
        yield LLMCompletionChunk(tool_calls=self._build_tool_calls(function_calls), finish_reason=finish_reason)

    def complete(
        self,
        *,
        config: ModelConfig,
        request: LLMCompletionRequest,
    ) -> LLMCompletionResponse:
        response = self._get_client(config).models.generate_content(
            model=config.model_name,
            contents=self._serialize_contents(request),
            config=self._build_generate_config(config=config, request=request),
        )
        function_calls: dict[str, dict[str, Any]] = {}
        self._merge_function_calls(function_calls, response)
        return LLMCompletionResponse(
            text=getattr(response, "text", "") or "",
            tool_calls=self._build_tool_calls(function_calls),
            finish_reason=self._extract_finish_reason(response),
            thinking=self._extract_thinking(response),
        )

    def _get_types(self):
        if self._types is not None:
            return self._types
        self._types = importlib.import_module("google.genai.types")
        return self._types

    def _get_client(self, config: ModelConfig):
        if self._client is not None:
            return self._client
        genai = importlib.import_module("google.genai")

        options = config.provider_options or {}
        client_kwargs: dict[str, Any] = {"api_key": config.api_key.get_secret_value()}
        if options.get("vertexai") is True:
            client_kwargs = {
                "vertexai": True,
                "project": options.get("project"),
                "location": options.get("location"),
            }
        elif config.base_url:
            client_kwargs["http_options"] = {"base_url": config.base_url}
        self._client = genai.Client(**client_kwargs)
        return self._client

    def _build_generate_config(self, *, config: ModelConfig, request: LLMCompletionRequest) -> Any:
        types = self._get_types()
        options = config.provider_options or {}
        config_kwargs: dict[str, Any] = {
            "temperature": request.temperature if request.temperature is not None else config.temperature,
            "max_output_tokens": request.max_tokens if request.max_tokens is not None else config.max_tokens,
            "automatic_function_calling": types.AutomaticFunctionCallingConfig(disable=True),
        }

        system_instruction = self._serialize_system_instruction(request)
        if system_instruction:
            config_kwargs["system_instruction"] = system_instruction

        tools = self._serialize_tools(request)
        if tools:
            config_kwargs["tools"] = tools

        tool_config = self._serialize_tool_config(request)
        if tool_config is not None:
            config_kwargs["tool_config"] = tool_config

        if request.json_schema is not None:
            config_kwargs["response_mime_type"] = "application/json"
            schema = request.json_schema.get("schema", request.json_schema)
            config_kwargs["response_schema"] = schema
        elif request.json_mode:
            config_kwargs["response_mime_type"] = "application/json"

        for key in ("thinking_config", "safety_settings", "top_p", "top_k", "candidate_count", "stop_sequences", "seed"):
            if key in options:
                config_kwargs[key] = options[key]

        extra_config = options.get("extra_config")
        if isinstance(extra_config, dict):
            config_kwargs.update(extra_config)

        return types.GenerateContentConfig(**config_kwargs)

    def _serialize_system_instruction(self, request: LLMCompletionRequest) -> str:
        return "\n\n".join(message.content for message in request.messages if message.role == "system" and message.content)

    def _serialize_contents(self, request: LLMCompletionRequest) -> list[Any]:
        types = self._get_types()
        contents: list[Any] = []
        for message in request.messages:
            if message.role == "system":
                continue
            if message.role == "tool":
                contents.append(
                    types.Content(
                        role="tool",
                        parts=[types.Part.from_function_response(name=message.name or message.tool_call_id or "tool", response={"output": message.content})],
                    )
                )
                continue
            if message.role == "assistant":
                parts: list[Any] = []
                if message.content:
                    parts.append(types.Part.from_text(text=message.content))
                for tool_call in message.tool_calls:
                    parts.append(types.Part.from_function_call(name=tool_call.name, args=tool_call.arguments))
                contents.append(types.Content(role="model", parts=parts))
                continue
            contents.append(types.Content(role="user", parts=[types.Part.from_text(text=message.content)]))
        return contents

    def _serialize_tools(self, request: LLMCompletionRequest) -> list[Any]:
        if not request.tools:
            return []
        types = self._get_types()
        declarations = [
            types.FunctionDeclaration(
                name=tool.name,
                description=tool.description,
                parameters_json_schema=tool.input_schema,
            )
            for tool in request.tools
        ]
        return [types.Tool(function_declarations=declarations)]

    def _serialize_tool_config(self, request: LLMCompletionRequest) -> Any:
        if request.tool_choice is None:
            return None
        types = self._get_types()
        mode = "AUTO"
        allowed_function_names: list[str] | None = None
        if request.tool_choice.name:
            mode = "ANY"
            allowed_function_names = [request.tool_choice.name]
        elif request.tool_choice.mode == "none":
            mode = "NONE"
        elif request.tool_choice.mode == "required":
            mode = "ANY"
        function_calling_config = types.FunctionCallingConfig(mode=mode, allowed_function_names=allowed_function_names)
        return types.ToolConfig(function_calling_config=function_calling_config)

    def _merge_function_calls(self, function_calls: dict[str, dict[str, Any]], response: Any) -> None:
        for candidate in getattr(response, "candidates", []) or []:
            content = getattr(candidate, "content", None)
            for part in getattr(content, "parts", []) or []:
                function_call = getattr(part, "function_call", None)
                if function_call is None:
                    continue
                name = getattr(function_call, "name", "") or ""
                args = getattr(function_call, "args", {})
                call_id = getattr(function_call, "id", None) or f"{name}-{len(function_calls)}"
                function_calls[str(call_id)] = {
                    "id": str(call_id),
                    "name": name,
                    "arguments": args if isinstance(args, dict) else {},
                }

    def _build_tool_calls(self, function_calls: dict[str, dict[str, Any]]) -> list[LLMToolCall]:
        tool_calls: list[LLMToolCall] = []
        for call_id, item in function_calls.items():
            arguments = item.get("arguments")
            parsed_arguments = arguments if isinstance(arguments, dict) else {}
            tool_calls.append(
                LLMToolCall(
                    id=str(item.get("id") or call_id),
                    name=str(item.get("name") or ""),
                    arguments=parsed_arguments,
                    raw_arguments=json.dumps(parsed_arguments),
                )
            )
        return tool_calls

    def _extract_finish_reason(self, response: Any) -> str | None:
        candidates = getattr(response, "candidates", []) or []
        if not candidates:
            return None
        finish_reason = getattr(candidates[0], "finish_reason", None)
        return str(finish_reason) if finish_reason is not None else None

    def _extract_thinking(self, response: Any) -> str:
        text_parts: list[str] = []
        for candidate in getattr(response, "candidates", []) or []:
            content = getattr(candidate, "content", None)
            for part in getattr(content, "parts", []) or []:
                if getattr(part, "thought", False):
                    text = getattr(part, "text", None)
                    if isinstance(text, str) and text:
                        text_parts.append(text)
        return "".join(text_parts)
