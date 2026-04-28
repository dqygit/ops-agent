from PySide6.QtWidgets import QFrame, QHBoxLayout, QLabel, QPlainTextEdit, QPushButton, QVBoxLayout, QWidget


class TerminalPanel(QWidget):
    def __init__(self):
        super().__init__()
        self._terminal_service = None
        self._asset = None
        self._terminal_session_id = None
        self._context_attached_listener = None

        self.status_label = QLabel("Disconnected")
        self.status_label.setObjectName("sectionMeta")
        self.connect_button = QPushButton("Connect")
        self.connect_button.setObjectName("primaryButton")
        self.disconnect_button = QPushButton("Disconnect")
        self.disconnect_button.setEnabled(False)
        self.terminal_view = QPlainTextEdit()
        self.terminal_view.setReadOnly(False)
        self.terminal_view.setPlaceholderText("Terminal output and selected context will appear here")

        root_layout = QVBoxLayout(self)
        root_layout.setContentsMargins(0, 0, 0, 0)

        card = QFrame()
        card.setObjectName("panelCard")
        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(14, 14, 14, 14)
        card_layout.setSpacing(12)

        title = QLabel("Terminal Session")
        title.setObjectName("sectionTitle")
        meta = QLabel("Live connection view for the selected asset")
        meta.setObjectName("sectionMeta")
        title_box = QVBoxLayout()
        title_box.setContentsMargins(0, 0, 0, 0)
        title_box.setSpacing(2)
        title_box.addWidget(title)
        title_box.addWidget(meta)
        card_layout.addLayout(title_box)
        card_layout.addWidget(self.status_label)

        actions = QHBoxLayout()
        actions.setSpacing(8)
        actions.addWidget(self.connect_button)
        actions.addWidget(self.disconnect_button)
        actions.addStretch(1)
        card_layout.addLayout(actions)
        card_layout.addWidget(self.terminal_view, 1)

        root_layout.addWidget(card)

        self.connect_button.clicked.connect(self.open_session)
        self.disconnect_button.clicked.connect(self.close_session)

    def bind_terminal_service(self, terminal_service) -> None:
        self._terminal_service = terminal_service

    def bind_context_attached_listener(self, context_attached_listener) -> None:
        self._context_attached_listener = context_attached_listener

    def set_asset_context(self, asset) -> None:
        if self._terminal_session_id is not None:
            self.close_session()
        self._asset = asset
        if asset is None:
            self.status_label.setText("Disconnected")
            self.connect_button.setEnabled(False)
            self.disconnect_button.setEnabled(False)
            self.terminal_view.clear()
            return
        if isinstance(asset, dict):
            asset_name = asset["name"]
            asset_host = asset["host"]
            asset_port = asset["port"]
        else:
            asset_name = asset.name
            asset_host = asset.host
            asset_port = asset.port
        self.status_label.setText(f"Target: {asset_name} @ {asset_host}:{asset_port}")
        self.connect_button.setEnabled(True)
        self.disconnect_button.setEnabled(False)
        self.terminal_view.clear()
        self.open_session()

    def open_session(self) -> None:
        if self._terminal_service is None or self._asset is None or self._terminal_session_id is not None:
            return
        session = self._terminal_service.open_session(self._asset)
        if session.get("error"):
            self.status_label.setText("Connection failed")
            self.terminal_view.setPlainText(session["error"])
            self.connect_button.setEnabled(True)
            self.disconnect_button.setEnabled(False)
            return
        self._terminal_session_id = session["terminal_session_id"]
        self.status_label.setText(f"Connected · session {self._terminal_session_id}")
        self.terminal_view.setPlainText(str(session["channel"]))
        self.connect_button.setEnabled(False)
        self.disconnect_button.setEnabled(True)

    def attach_selected_context(self, selection_label: str | bool = "terminal selection"):
        if self._terminal_service is None or self._terminal_session_id is None:
            return None
        if isinstance(selection_label, bool):
            selection_label = "terminal selection"
        cursor = self.terminal_view.textCursor()
        selected_text = cursor.selectedText()
        if not selected_text:
            return None
        attachment = self._terminal_service.attach_context(
            self._terminal_session_id,
            selection_label,
            selected_text,
        )
        if self._context_attached_listener is not None:
            self._context_attached_listener(attachment)
        return attachment

    def apply_agent_event(self, event: dict) -> None:
        if event.get("type") != "terminal_output":
            return
        chunk = event.get("payload", {}).get("chunk", "")
        if not chunk:
            return
        current = self.terminal_view.toPlainText()
        self.terminal_view.setPlainText(f"{current}\n{chunk}".strip())
        self.terminal_view.verticalScrollBar().setValue(self.terminal_view.verticalScrollBar().maximum())

    def close_session(self) -> None:
        if self._terminal_service is None or self._terminal_session_id is None:
            return
        if not self._terminal_service.close_session(self._terminal_session_id):
            return
        self._terminal_session_id = None
        self.status_label.setText("Disconnected")
        self.connect_button.setEnabled(True)
        self.disconnect_button.setEnabled(False)
