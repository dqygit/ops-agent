from app.core.llm.provider_presets import is_openai_compatible_provider
from app.shared.enums import ModelProvider
from app.shared.schemas import ModelConfig


def build_llm_provider(config: ModelConfig):
    if config.provider is ModelProvider.ANTHROPIC:
        from app.core.llm.providers.anthropic import AnthropicLLMProvider

        return AnthropicLLMProvider()
    if config.provider is ModelProvider.OPENAI_RESPONSES:
        from app.core.llm.providers.openai_responses import OpenAIResponsesLLMProvider

        return OpenAIResponsesLLMProvider()
    if config.provider is ModelProvider.GOOGLE_GEMINI:
        from app.core.llm.providers.google_gemini import GoogleGeminiLLMProvider

        return GoogleGeminiLLMProvider()
    if is_openai_compatible_provider(config.provider):
        from app.core.llm.providers.openai_compatible import OpenAICompatibleLLMProvider

        return OpenAICompatibleLLMProvider()
    raise ValueError(f"Unsupported model provider: {config.provider}")
