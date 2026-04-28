import json
import os
from pathlib import Path

from pydantic import SecretStr

from app.shared import config as shared_config
from app.shared.enums import ModelProvider
from app.shared.schemas import ModelConfig


class ModelService:
    def __init__(self, provider_client=None, settings_path: Path | None = None):
        self._provider_client = provider_client
        self._settings_path = settings_path or shared_config.SETTINGS_PATH

    def validate(self, config: ModelConfig) -> bool:
        if self._provider_client is None:
            return True
        return self._provider_client.check_connection(config)

    def get_active_model(self, default_config: ModelConfig, session_override: ModelConfig | None) -> ModelConfig:
        return session_override or default_config

    def build_default_config(self) -> ModelConfig:
        return ModelConfig(
            provider=ModelProvider.ANTHROPIC,
            model_name="claude-opus-4-7",
            base_url=os.environ.get("ANTHROPIC_BASE_URL", "https://api.anthropic.com"),
            api_key=SecretStr(os.environ.get("ANTHROPIC_API_KEY", "demo-key")),
            timeout_seconds=30,
            temperature=0.2,
            max_tokens=256,
        )

    def load_settings(self) -> ModelConfig:
        default_config = self.build_default_config()
        if not self._settings_path.exists():
            return default_config
        payload = json.loads(self._settings_path.read_text(encoding="utf-8"))
        return ModelConfig(
            provider=ModelProvider(payload.get("provider", default_config.provider.value)),
            model_name=payload.get("model_name", default_config.model_name),
            base_url=payload.get("base_url", default_config.base_url),
            api_key=SecretStr(payload.get("api_key", default_config.api_key.get_secret_value())),
            timeout_seconds=payload.get("timeout_seconds", default_config.timeout_seconds),
            temperature=payload.get("temperature", default_config.temperature),
            max_tokens=payload.get("max_tokens", default_config.max_tokens),
        )

    def save_settings(self, config: ModelConfig) -> ModelConfig:
        self._settings_path.parent.mkdir(parents=True, exist_ok=True)
        self._settings_path.write_text(
            json.dumps(
                {
                    "provider": config.provider.value,
                    "model_name": config.model_name,
                    "base_url": config.base_url,
                    "api_key": config.api_key.get_secret_value(),
                    "timeout_seconds": config.timeout_seconds,
                    "temperature": config.temperature,
                    "max_tokens": config.max_tokens,
                },
                ensure_ascii=False,
                indent=2,
            ),
            encoding="utf-8",
        )
        return config

    def list_available_models(self, provider: ModelProvider) -> list[str]:
        if provider is ModelProvider.OPENAI_COMPATIBLE:
            return ["gpt-5.5", "gpt-5.4"]
        return ["claude-opus-4-7", "claude-sonnet-4-6"]
