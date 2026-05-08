from app.shared.enums import ModelProvider
from app.shared.schemas import ModelConfig


def build_llm_provider(config: ModelConfig):
    if config.provider is ModelProvider.ANTHROPIC:
        from app.integrations.llm.providers.anthropic import AnthropicLLMProvider

        return AnthropicLLMProvider()
    if config.provider is ModelProvider.OPENAI_COMPATIBLE:
        from app.integrations.llm.providers.openai_compatible import OpenAICompatibleLLMProvider

        return OpenAICompatibleLLMProvider()
    raise ValueError(f"Unsupported model provider: {config.provider}")
