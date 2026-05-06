import json
import os
from pathlib import Path

from pydantic import SecretStr
from sqlmodel import Session

from app.db.models import ModelConfigRecord
from app.db.repositories.models import list_model_names_by_provider
from app.services.credential_service import CredentialService
from app.services.secret_key import get_ops_agent_secret_key
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
        provider = os.environ.get("OPS_AGENT_MODEL_PROVIDER", ModelProvider.ANTHROPIC.value)
        return ModelConfig(
            provider=ModelProvider(provider),
            model_name=os.environ.get("OPS_AGENT_MODEL_NAME", "claude-opus-4-7"),
            base_url=os.environ.get("ANTHROPIC_BASE_URL", "https://api.anthropic.com"),
            api_key=SecretStr(os.environ.get("ANTHROPIC_API_KEY", "demo-key")),
            timeout_seconds=int(os.environ.get("OPS_AGENT_MODEL_TIMEOUT_SECONDS", "30")),
            temperature=float(os.environ.get("OPS_AGENT_MODEL_TEMPERATURE", "0.2")),
            max_tokens=int(os.environ.get("OPS_AGENT_MODEL_MAX_TOKENS", "2560")),
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

    def list_available_models(self, provider: ModelProvider, session: Session | None = None) -> list[str]:
        if session is None:
            return []
        return list_model_names_by_provider(session, provider.value)

    def encrypt_api_key(self, api_key: SecretStr) -> tuple[str, str]:
        credential_service = self._credential_service()
        return CredentialService.encryption_version, credential_service.encrypt_secret(api_key.get_secret_value())

    def decrypt_api_key(self, record: ModelConfigRecord) -> SecretStr:
        return SecretStr(self._credential_service().decrypt_secret(record.encrypted_api_key))

    def mask_api_key(self, api_key: str) -> str:
        if not api_key:
            return ""
        if len(api_key) <= 4:
            return "****"
        if len(api_key) <= 8:
            return f"****{api_key[-4:]}"
        return f"{api_key[:3]}****{api_key[-4:]}"

    def from_record(self, record: ModelConfigRecord) -> ModelConfig:
        return ModelConfig(
            provider=ModelProvider(record.provider),
            model_name=record.model_name,
            base_url=record.base_url,
            api_key=self.decrypt_api_key(record),
            name=record.name,
            is_default=record.is_default,
            description=record.description,
            timeout_seconds=record.timeout_seconds,
            temperature=record.temperature,
            max_tokens=record.max_tokens,
        )

    def to_record_payload(self, config: ModelConfig) -> dict:
        encryption_version, encrypted_api_key = self.encrypt_api_key(config.api_key)
        return {
            "name": config.name,
            "provider": config.provider.value,
            "base_url": config.base_url,
            "api_key_encryption_version": encryption_version,
            "encrypted_api_key": encrypted_api_key,
            "model_name": config.model_name,
            "is_default": config.is_default,
            "timeout_seconds": config.timeout_seconds,
            "temperature": config.temperature,
            "max_tokens": config.max_tokens,
            "description": config.description,
        }

    def _credential_service(self) -> CredentialService:
        return CredentialService(secret_key=get_ops_agent_secret_key())
