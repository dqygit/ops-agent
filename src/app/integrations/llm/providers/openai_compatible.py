from collections.abc import Iterator
from typing import Any, cast

from app.integrations.llm.base import build_summary_conversation
from app.shared.schemas import ModelConfig


class OpenAICompatibleLLMProvider:
    def __init__(self, client: Any = None):
        self._client = client

    def summarize(self, *, config: ModelConfig, user_input: str, command_outputs: list[str], recent_messages=None) -> str:
        conversation = build_summary_conversation(user_input, command_outputs, recent_messages)
        response = self._get_client(config).chat.completions.create(
            model=config.model_name,
            temperature=config.temperature,
            max_tokens=config.max_tokens,
            messages=cast(
                Any,
                [{"role": "system", "content": conversation.system_prompt}, *conversation.messages],
            ),
        )
        return response.choices[0].message.content or ""

    def stream_summarize(
        self,
        *,
        config: ModelConfig,
        user_input: str,
        command_outputs: list[str],
        recent_messages=None,
    ) -> Iterator[str]:
        conversation = build_summary_conversation(user_input, command_outputs, recent_messages)
        response = self._get_client(config).chat.completions.create(
            model=config.model_name,
            temperature=config.temperature,
            max_tokens=config.max_tokens,
            messages=cast(
                Any,
                [{"role": "system", "content": conversation.system_prompt}, *conversation.messages],
            ),
            stream=True,
        )
        for chunk in response:
            if not chunk.choices:
                continue
            delta = getattr(chunk.choices[0], "delta", None)
            text = getattr(delta, "content", None)
            if isinstance(text, str) and text:
                yield text

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

