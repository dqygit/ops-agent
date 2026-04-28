from collections.abc import Callable

from pydantic import SecretStr
from PySide6.QtWidgets import QDialog, QFormLayout, QLineEdit, QPushButton, QVBoxLayout

from app.shared.enums import ModelProvider
from app.shared.schemas import ModelConfig


class SettingsDialog(QDialog):
    def __init__(self, config: ModelConfig, on_save: Callable[[ModelConfig], None]):
        super().__init__()
        self.setWindowTitle("Settings")
        self._config = config
        self._on_save = on_save
        self.provider_input = QLineEdit(config.provider.value)
        self.model_input = QLineEdit(config.model_name)
        self.base_url_input = QLineEdit(config.base_url)
        self.api_key_input = QLineEdit(config.api_key.get_secret_value())
        self.save_button = QPushButton("Save")
        form = QFormLayout()
        form.addRow("Provider", self.provider_input)
        form.addRow("Model", self.model_input)
        form.addRow("Base URL", self.base_url_input)
        form.addRow("API Key", self.api_key_input)
        layout = QVBoxLayout(self)
        layout.addLayout(form)
        layout.addWidget(self.save_button)
        self.save_button.clicked.connect(self._handle_save_clicked)

    def _handle_save_clicked(self) -> None:
        config = ModelConfig(
            provider=ModelProvider(self.provider_input.text().strip()),
            model_name=self.model_input.text().strip(),
            base_url=self.base_url_input.text().strip(),
            api_key=SecretStr(self.api_key_input.text()),
            timeout_seconds=self._config.timeout_seconds,
            temperature=self._config.temperature,
            max_tokens=self._config.max_tokens,
        )
        self._on_save(config)
        self.accept()
