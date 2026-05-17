from dataclasses import dataclass, field
from typing import Any

from app.shared.enums import ModelProvider


@dataclass(frozen=True)
class ProviderPreset:
    provider: ModelProvider
    label: str
    default_base_url: str
    default_model: str
    openai_compatible: bool = True
    default_extra_body: dict[str, Any] = field(default_factory=dict)
    max_tokens_param: str = "max_tokens"


_PROVIDER_PRESETS: dict[ModelProvider, ProviderPreset] = {
    ModelProvider.OPENAI_COMPATIBLE: ProviderPreset(
        provider=ModelProvider.OPENAI_COMPATIBLE,
        label="OpenAI Compatible",
        default_base_url="http://localhost/v1",
        default_model="claude-sonnet-4-5-20250929",
    ),
    ModelProvider.QWEN: ProviderPreset(
        provider=ModelProvider.QWEN,
        label="Qwen / DashScope",
        default_base_url="https://dashscope.aliyuncs.com/compatible-mode/v1",
        default_model="qwen3.6-plus",
    ),
    ModelProvider.BIGMODEL: ProviderPreset(
        provider=ModelProvider.BIGMODEL,
        label="BigModel / GLM",
        default_base_url="https://open.bigmodel.cn/api/paas/v4/",
        default_model="glm-5.1",
        default_extra_body={"tool_stream": True},
    ),
    ModelProvider.KIMI: ProviderPreset(
        provider=ModelProvider.KIMI,
        label="Kimi / Moonshot",
        default_base_url="https://api.moonshot.ai/v1",
        default_model="kimi-k2.6",
        max_tokens_param="max_completion_tokens",
    ),
    ModelProvider.MINIMAX: ProviderPreset(
        provider=ModelProvider.MINIMAX,
        label="MiniMax",
        default_base_url="https://api.minimax.io/v1",
        default_model="MiniMax-M2.7",
        default_extra_body={"reasoning_split": True},
        max_tokens_param="max_completion_tokens",
    ),
    ModelProvider.DEEPSEEK: ProviderPreset(
        provider=ModelProvider.DEEPSEEK,
        label="DeepSeek",
        default_base_url="https://api.deepseek.com",
        default_model="deepseek-v4-flash",
    ),
    ModelProvider.AZURE_OPENAI: ProviderPreset(
        provider=ModelProvider.AZURE_OPENAI,
        label="Azure OpenAI",
        default_base_url="https://YOUR-RESOURCE.openai.azure.com/openai/v1/",
        default_model="gpt-4.1",
    ),
    ModelProvider.AMAZON_BEDROCK: ProviderPreset(
        provider=ModelProvider.AMAZON_BEDROCK,
        label="Amazon Bedrock",
        default_base_url="https://bedrock-mantle.us-east-1.api.aws/v1",
        default_model="openai.gpt-oss-120b",
    ),
    ModelProvider.OPENROUTER: ProviderPreset(
        provider=ModelProvider.OPENROUTER,
        label="OpenRouter",
        default_base_url="https://openrouter.ai/api/v1",
        default_model="openai/gpt-4.1",
    ),
    ModelProvider.CLOUDFLARE: ProviderPreset(
        provider=ModelProvider.CLOUDFLARE,
        label="Cloudflare Workers AI",
        default_base_url="https://api.cloudflare.com/client/v4/accounts/YOUR_ACCOUNT_ID/ai/v1",
        default_model="@cf/meta/llama-3.1-8b-instruct",
    ),
    ModelProvider.GITHUB_MODELS: ProviderPreset(
        provider=ModelProvider.GITHUB_MODELS,
        label="GitHub Models",
        default_base_url="https://models.github.ai/inference",
        default_model="openai/gpt-4.1",
    ),
    ModelProvider.SILICONFLOW: ProviderPreset(
        provider=ModelProvider.SILICONFLOW,
        label="SiliconFlow",
        default_base_url="https://api.siliconflow.com/v1",
        default_model="Qwen/Qwen3-235B-A22B-Instruct-2507",
    ),
    ModelProvider.OPENAI_RESPONSES: ProviderPreset(
        provider=ModelProvider.OPENAI_RESPONSES,
        label="OpenAI Responses",
        default_base_url="https://api.openai.com/v1",
        default_model="gpt-5",
        openai_compatible=False,
    ),
    ModelProvider.GOOGLE_GEMINI: ProviderPreset(
        provider=ModelProvider.GOOGLE_GEMINI,
        label="Google Gemini",
        default_base_url="https://generativelanguage.googleapis.com",
        default_model="gemini-2.5-pro",
        openai_compatible=False,
    ),
}


def get_provider_preset(provider: ModelProvider) -> ProviderPreset | None:
    return _PROVIDER_PRESETS.get(provider)


def is_openai_compatible_provider(provider: ModelProvider) -> bool:
    preset = get_provider_preset(provider)
    return preset.openai_compatible if preset is not None else False


def get_default_base_url(provider: ModelProvider) -> str:
    if provider is ModelProvider.ANTHROPIC:
        return "https://api.anthropic.com"
    preset = get_provider_preset(provider)
    return preset.default_base_url if preset is not None else "http://localhost/v1"


def get_default_model(provider: ModelProvider) -> str:
    if provider is ModelProvider.ANTHROPIC:
        return "claude-sonnet-4-5-20250929"
    preset = get_provider_preset(provider)
    return preset.default_model if preset is not None else "claude-sonnet-4-5-20250929"


def list_provider_presets() -> list[ProviderPreset]:
    return list(_PROVIDER_PRESETS.values())
