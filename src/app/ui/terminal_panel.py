from PySide6.QtWidgets import QLabel, QPlainTextEdit, QPushButton, QVBoxLayout, QWidget


class TerminalPanel(QWidget):
    def __init__(self):
        super().__init__()
        self._terminal_service = None
        self._asset = None
        self._terminal_session_id = None
        self._context_attached_listener = None
        self.status_label = QLabel("Disconnected")
        self.connect_button = QPushButton("Connect")
        self.disconnect_button = QPushButton("Disconnect")
        self.disconnect_button.setEnabled(False)
        self.terminal_view = QPlainTextEdit()
        self.terminal_view.setReadOnly(False)
        self.connect_button.clicked.connect(self.open_session)
        self.disconnect_button.clicked.connect(self.close_session)
        layout = QVBoxLayout(self)
        layout.addWidget(self.status_label)
        layout.addWidget(self.connect_button)
        layout.addWidget(self.disconnect_button)
        layout.addWidget(self.terminal_view)

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
        self.status_label.setText(f"Connecting: {asset_name} @ {asset_host}:{asset_port}")
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
        self.status_label.setText(f"Connected (session {self._terminal_session_id})")
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

    def close_session(self) -> None:
        if self._terminal_service is None or self._terminal_session_id is None:
            return
        if not self._terminal_service.close_session(self._terminal_session_id):
            return
        self._terminal_session_id = None
        self.status_label.setText("Disconnected")
        self.connect_button.setEnabled(True)
        self.disconnect_button.setEnabled(False)
