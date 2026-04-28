from pydantic import SecretStr

from app.core.agent.planner import build_plan
from app.integrations.llm.base import SupportsSummarize
from app.integrations.llm.factory import build_llm_provider
from app.integrations.llm.providers.anthropic import AnthropicLLMProvider
from app.integrations.llm.providers.openai_compatible import OpenAICompatibleLLMProvider
from app.shared.enums import AssetType, ModelProvider
from app.shared.schemas import ModelConfig, TerminalContextAttachment


class MockLLMProvider:
    def plan(self, asset_type, user_input: str, terminal_context=None, recent_messages=None):
        return build_plan(
            asset_type=asset_type,
            user_input=user_input,
            terminal_context=terminal_context,
            recent_messages=recent_messages,
        )

    def summarize(
        self,
        *,
        config,
        user_input: str,
        command_outputs: list[str],
        recent_messages=None,
    ) -> str:
        return f"Task: {user_input}\nOutput count: {len(command_outputs)}"

    def stream_summarize(
        self,
        *,
        config,
        user_input: str,
        command_outputs: list[str],
        recent_messages=None,
    ):
        yield "Task: "
        yield user_input


class FakeMessagesAPI:
    def __init__(self):
        self.calls = []
        self.stream_calls = []

    def create(self, **kwargs):
        self.calls.append(kwargs)
        return type(
            "FakeMessage",
            (),
            {"content": [type("TextBlock", (), {"text": "anthropic summary"})()]},
        )()

    def stream(self, **kwargs):
        self.stream_calls.append(kwargs)

        class FakeStream:
            text_stream = ["anthropic ", "stream"]

            def __enter__(self):
                return self

            def __exit__(self, exc_type, exc, tb):
                return False

        return FakeStream()


class FakeAnthropicClient:
    def __init__(self):
        self.messages = FakeMessagesAPI()


class FakeOpenAICompletionsAPI:
    def __init__(self):
        self.calls = []

    def create(self, **kwargs):
        self.calls.append(kwargs)
        if kwargs.get("stream"):
            return [
                type(
                    "FakeChunk",
                    (),
                    {
                        "choices": [
                            type(
                                "FakeChoiceDelta",
                                (),
                                {"delta": type("FakeDelta", (), {"content": "openai "})()},
                            )()
                        ]
                    },
                )(),
                type(
                    "FakeChunk",
                    (),
                    {
                        "choices": [
                            type(
                                "FakeChoiceDelta",
                                (),
                                {"delta": type("FakeDelta", (), {"content": "stream"})()},
                            )()
                        ]
                    },
                )(),
            ]
        message = type("FakeMessage", (), {"content": "openai summary"})()
        choice = type("FakeChoice", (), {"message": message})()
        return type("FakeResponse", (), {"choices": [choice]})()


class FakeOpenAIChatAPI:
    def __init__(self):
        self.completions = FakeOpenAICompletionsAPI()


class FakeOpenAIClient:
    def __init__(self):
        self.chat = FakeOpenAIChatAPI()



def test_mock_provider_builds_plan_and_summary_from_current_inputs():
    provider = MockLLMProvider()
    config = ModelConfig(
        provider=ModelProvider.ANTHROPIC,
        model_name="claude-opus-4-7",
        base_url="https://api.anthropic.com",
        api_key=SecretStr("test-key"),
        timeout_seconds=30,
        temperature=0.2,
        max_tokens=256,
    )

    plan = provider.plan(
        asset_type=AssetType.HUAWEI,
        user_input="检查接口状态",
        terminal_context=TerminalContextAttachment(
            terminal_session_id=1,
            selection_label="selected interface",
            selected_text="GigabitEthernet0/0/1 up",
        ),
        recent_messages=[{"role": "user", "content": "上一轮"}],
    )
    summary = provider.summarize(
        config=config,
        user_input="检查接口状态",
        command_outputs=["display interface brief: ok"],
        recent_messages=[{"role": "user", "content": "上一轮"}],
    )

    assert plan[0].title == "Check interface status"
    assert plan[0].reason == "Selected from the readonly catalog with selected interface"
    assert summary == "Task: 检查接口状态\nOutput count: 1"



def test_factory_builds_anthropic_provider_for_anthropic_model_config():
    config = ModelConfig(
        provider=ModelProvider.ANTHROPIC,
        model_name="claude-opus-4-7",
        base_url="https://api.anthropic.com",
        api_key=SecretStr("test-key"),
        timeout_seconds=30,
        temperature=0.2,
        max_tokens=256,
    )

    provider = build_llm_provider(config)

    assert isinstance(provider, AnthropicLLMProvider)



def test_factory_built_anthropic_provider_matches_shared_summarize_protocol():
    config = ModelConfig(
        provider=ModelProvider.ANTHROPIC,
        model_name="claude-opus-4-7",
        base_url="https://api.anthropic.com",
        api_key=SecretStr("test-key"),
        timeout_seconds=30,
        temperature=0.2,
        max_tokens=256,
    )

    provider = build_llm_provider(config)

    assert isinstance(provider, SupportsSummarize)



def test_factory_builds_openai_compatible_provider_for_openai_model_config():
    config = ModelConfig(
        provider=ModelProvider.OPENAI_COMPATIBLE,
        model_name="gpt-4o-mini",
        base_url="https://example-openai.test/v1",
        api_key=SecretStr("test-key"),
        timeout_seconds=30,
        temperature=0.2,
        max_tokens=256,
    )

    provider = build_llm_provider(config)

    assert isinstance(provider, OpenAICompatibleLLMProvider)



def test_factory_built_openai_provider_matches_shared_summarize_protocol():
    config = ModelConfig(
        provider=ModelProvider.OPENAI_COMPATIBLE,
        model_name="gpt-4o-mini",
        base_url="https://example-openai.test/v1",
        api_key=SecretStr("test-key"),
        timeout_seconds=30,
        temperature=0.2,
        max_tokens=256,
    )

    provider = build_llm_provider(config)

    assert isinstance(provider, SupportsSummarize)



def test_anthropic_provider_summarizes_command_outputs_with_sdk_client():
    client = FakeAnthropicClient()
    provider = AnthropicLLMProvider(client=client)
    config = ModelConfig(
        provider=ModelProvider.ANTHROPIC,
        model_name="claude-opus-4-7",
        base_url="https://api.anthropic.com",
        api_key=SecretStr("test-key"),
        timeout_seconds=30,
        temperature=0.2,
        max_tokens=256,
    )

    summary = provider.summarize(
        config=config,
        user_input="检查接口状态",
        command_outputs=["display interface brief: ok"],
        recent_messages=[{"role": "user", "content": "上一轮"}],
    )

    assert summary == "anthropic summary"
    assert client.messages.calls == [
        {
            "model": "claude-opus-4-7",
            "max_tokens": 256,
            "system": "你是一个网络运维助手。基于用户请求和命令输出，给出简洁、准确、可执行的中文总结。",
            "messages": [
                {"role": "user", "content": "上一轮"},
                {
                    "role": "user",
                    "content": "用户请求: 检查接口状态\n\n命令输出:\n1. display interface brief: ok",
                },
            ],
        }
    ]



def test_anthropic_provider_streams_summary_chunks_with_sdk_client():
    client = FakeAnthropicClient()
    provider = AnthropicLLMProvider(client=client)
    config = ModelConfig(
        provider=ModelProvider.ANTHROPIC,
        model_name="claude-opus-4-7",
        base_url="https://api.anthropic.com",
        api_key=SecretStr("test-key"),
        timeout_seconds=30,
        temperature=0.2,
        max_tokens=256,
    )

    chunks = list(
        provider.stream_summarize(
            config=config,
            user_input="检查接口状态",
            command_outputs=["display interface brief: ok"],
            recent_messages=[{"role": "user", "content": "上一轮"}],
        )
    )

    assert chunks == ["anthropic ", "stream"]
    assert client.messages.stream_calls == [
        {
            "model": "claude-opus-4-7",
            "max_tokens": 256,
            "system": "你是一个网络运维助手。基于用户请求和命令输出，给出简洁、准确、可执行的中文总结。",
            "messages": [
                {"role": "user", "content": "上一轮"},
                {
                    "role": "user",
                    "content": "用户请求: 检查接口状态\n\n命令输出:\n1. display interface brief: ok",
                },
            ],
        }
    ]



def test_openai_compatible_provider_summarizes_command_outputs_with_chat_completions_client():
    client = FakeOpenAIClient()
    provider = OpenAICompatibleLLMProvider(client=client)
    config = ModelConfig(
        provider=ModelProvider.OPENAI_COMPATIBLE,
        model_name="gpt-4o-mini",
        base_url="https://example-openai.test/v1",
        api_key=SecretStr("test-key"),
        timeout_seconds=30,
        temperature=0.2,
        max_tokens=256,
    )

    summary = provider.summarize(
        config=config,
        user_input="检查接口状态",
        command_outputs=["display interface brief: ok"],
        recent_messages=[{"role": "user", "content": "上一轮"}],
    )

    assert summary == "openai summary"
    assert client.chat.completions.calls == [
        {
            "model": "gpt-4o-mini",
            "temperature": 0.2,
            "max_tokens": 256,
            "messages": [
                {
                    "role": "system",
                    "content": "你是一个网络运维助手。基于用户请求和命令输出，给出简洁、准确、可执行的中文总结。",
                },
                {"role": "user", "content": "上一轮"},
                {
                    "role": "user",
                    "content": "用户请求: 检查接口状态\n\n命令输出:\n1. display interface brief: ok",
                },
            ],
        }
    ]



def test_openai_compatible_provider_streams_summary_chunks_with_chat_completions_client():
    client = FakeOpenAIClient()
    provider = OpenAICompatibleLLMProvider(client=client)
    config = ModelConfig(
        provider=ModelProvider.OPENAI_COMPATIBLE,
        model_name="gpt-4o-mini",
        base_url="https://example-openai.test/v1",
        api_key=SecretStr("test-key"),
        timeout_seconds=30,
        temperature=0.2,
        max_tokens=256,
    )

    chunks = list(
        provider.stream_summarize(
            config=config,
            user_input="检查接口状态",
            command_outputs=["display interface brief: ok"],
            recent_messages=[{"role": "user", "content": "上一轮"}],
        )
    )

    assert chunks == ["openai ", "stream"]
    assert client.chat.completions.calls == [
        {
            "model": "gpt-4o-mini",
            "temperature": 0.2,
            "max_tokens": 256,
            "messages": [
                {
                    "role": "system",
                    "content": "你是一个网络运维助手。基于用户请求和命令输出，给出简洁、准确、可执行的中文总结。",
                },
                {"role": "user", "content": "上一轮"},
                {
                    "role": "user",
                    "content": "用户请求: 检查接口状态\n\n命令输出:\n1. display interface brief: ok",
                },
            ],
            "stream": True,
        }
    ]
