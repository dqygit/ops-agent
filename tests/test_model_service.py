import os
from pathlib import Path

from pydantic import SecretStr

from app.shared.enums import ModelProvider
from app.shared.schemas import ModelConfig
from app.services.model_service import ModelService


class FakeProvider:
    def check_connection(self, config: ModelConfig) -> bool:
        return config.model_name == "claude-sonnet-4-6"


def test_model_service_validates_and_returns_default_model_config():
    service = ModelService(provider_client=FakeProvider())
    config = ModelConfig(
        provider=ModelProvider.ANTHROPIC,
        model_name="claude-sonnet-4-6",
        base_url="https://api.anthropic.com",
        api_key=SecretStr("test-key"),
        timeout_seconds=30,
        temperature=0.2,
        max_tokens=1024,
    )

    assert service.validate(config) is True
    assert service.get_active_model(config, None).model_name == "claude-sonnet-4-6"


def test_model_service_loads_default_settings_when_file_is_missing(tmp_path: Path):
    service = ModelService(settings_path=tmp_path / "missing-settings.json")

    config = service.load_settings()

    assert config.provider is ModelProvider.ANTHROPIC
    assert config.model_name == "claude-opus-4-7"
    assert config.base_url == os.environ.get("ANTHROPIC_BASE_URL", "https://api.anthropic.com")
    assert config.api_key.get_secret_value() == os.environ.get("ANTHROPIC_API_KEY", "demo-key")
    assert config.max_tokens == 256


def test_model_service_saves_and_loads_settings_round_trip(tmp_path: Path):
    settings_path = tmp_path / "settings.json"
    service = ModelService(settings_path=settings_path)
    config = ModelConfig(
        provider=ModelProvider.OPENAI_COMPATIBLE,
        model_name="gpt-5.5",
        base_url="https://example.test/v1",
        api_key=SecretStr("secret-value"),
        timeout_seconds=45,
        temperature=0.4,
        max_tokens=512,
    )

    service.save_settings(config)
    loaded = service.load_settings()

    assert settings_path.exists() is True
    assert loaded.provider is ModelProvider.OPENAI_COMPATIBLE
    assert loaded.model_name == "gpt-5.5"
    assert loaded.base_url == "https://example.test/v1"
    assert loaded.api_key.get_secret_value() == "secret-value"
    assert loaded.timeout_seconds == 45
    assert loaded.temperature == 0.4
    assert loaded.max_tokens == 512


def test_model_service_lists_available_models_by_provider():
    service = ModelService()

    assert service.list_available_models(ModelProvider.ANTHROPIC) == ["claude-opus-4-7", "claude-sonnet-4-6"]
    assert service.list_available_models(ModelProvider.OPENAI_COMPATIBLE) == ["gpt-5.5", "gpt-5.4"]
