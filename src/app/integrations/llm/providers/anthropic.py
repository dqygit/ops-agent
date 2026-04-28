from collections.abc import Iterator
from typing import Any, cast

from app.integrations.llm.base import build_summary_conversation
from app.shared.schemas import ModelConfig


class AnthropicLLMProvider:
    def __init__(self, client: Any = None):
        self._client = client

    def summarize(self, *, config: ModelConfig, user_input: str, command_outputs: list[str], recent_messages=None) -> str:
        conversation = build_summary_conversation(user_input, command_outputs, recent_messages)
        response = self._get_client(config).messages.create(
            model=config.model_name,
            max_tokens=config.max_tokens,
            system=conversation.system_prompt,
            messages=cast(Any, conversation.messages),
        )
        chunks: list[str] = []
        for block in response.content:
            text = getattr(block, "text", None)
            if isinstance(text, str):
                chunks.append(text)
        return "".join(chunks)

    def stream_summarize(
        self,
        *,
        config: ModelConfig,
        user_input: str,
        command_outputs: list[str],
        recent_messages=None,
    ) -> Iterator[str]:
        conversation = build_summary_conversation(user_input, command_outputs, recent_messages)
        with self._get_client(config).messages.stream(
            model=config.model_name,
            max_tokens=config.max_tokens,
            system=conversation.system_prompt,
            messages=cast(Any, conversation.messages),
        ) as stream:
            for chunk in stream.text_stream:
                if isinstance(chunk, str) and chunk:
                    yield chunk

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

