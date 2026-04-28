from app.shared.enums import AssetType
from PySide6.QtWidgets import QComboBox, QPushButton, QPlainTextEdit, QVBoxLayout, QWidget


class ChatPanel(QWidget):
    def __init__(self):
        super().__init__()
        self.model_selector = QComboBox()
        self.conversation_box = QPlainTextEdit()
        self.conversation_box.setReadOnly(True)
        self.input_box = QPlainTextEdit()
        self.attach_context_button = QPushButton("Attach Terminal Context")
        self.run_button = QPushButton("Generate Plan")
        self.approve_button = QPushButton("Approve")
        self.reject_button = QPushButton("Reject")
        self._chat_service = None
        self._conversation_id = "conversation-1"
        self._asset = None
        self._asset_type = None
        self._model_name = ""
        self._terminal_context = None
        self._recent_messages = []
        self._pending_run_id = None
        self._session_id = 0
        self._agent_event_listener = None
        layout = QVBoxLayout(self)
        layout.addWidget(self.model_selector)
        layout.addWidget(self.conversation_box)
        layout.addWidget(self.input_box)
        layout.addWidget(self.attach_context_button)
        layout.addWidget(self.run_button)
        layout.addWidget(self.approve_button)
        layout.addWidget(self.reject_button)
        self.run_button.clicked.connect(self._handle_run_clicked)
        self.approve_button.clicked.connect(lambda: self._resume_pending_run(True))
        self.reject_button.clicked.connect(lambda: self._resume_pending_run(False))

    def bind_chat_service(self, chat_service) -> None:
        self._chat_service = chat_service
        self._restore_pending_approval()

    def set_session_context(
        self,
        *,
        conversation_id: str,
        asset_type,
        model_name: str,
        terminal_context=None,
        recent_messages=None,
    ) -> None:
        self._conversation_id = conversation_id
        self._asset_type = asset_type
        self._model_name = model_name
        self._set_selected_model(model_name)
        self._terminal_context = terminal_context
        self._recent_messages = recent_messages or []
        self._restore_pending_approval()

    def set_available_models(self, models: list[str], selected_model: str) -> None:
        self.model_selector.clear()
        self.model_selector.addItems(models)
        self._set_selected_model(selected_model)

    def get_selected_model(self) -> str:
        current_model = self.model_selector.currentText().strip()
        return current_model or self._model_name

    def _set_selected_model(self, model_name: str) -> None:
        self._model_name = model_name
        if not model_name:
            return
        index = self.model_selector.findText(model_name)
        if index >= 0:
            self.model_selector.setCurrentIndex(index)
            return
        self.model_selector.addItem(model_name)
        self.model_selector.setCurrentIndex(self.model_selector.count() - 1)

    def set_asset_context(self, asset) -> None:
        self._asset = asset
        if asset is None:
            self._asset_type = None
            self._terminal_context = None
            self._session_id = 0
            self._recent_messages = []
            self.conversation_box.clear()
            return
        self._asset_type = AssetType(asset.asset_type)
        self._restore_pending_approval()

    def load_session(self, *, session_id: int, messages: list[dict[str, str]], model_name: str) -> None:
        self._session_id = session_id
        self._recent_messages = messages
        self._set_selected_model(model_name)
        lines = [f"{message['role']}: {message['content']}" for message in messages]
        self.conversation_box.setPlainText("\n".join(lines))
        self._restore_pending_approval()

    def set_terminal_context(self, terminal_context) -> None:
        self._terminal_context = terminal_context

    def bind_agent_event_listener(self, agent_event_listener) -> None:
        self._agent_event_listener = agent_event_listener

    def _restore_pending_approval(self) -> None:
        if self._chat_service is None or not self._session_id:
            return
        approval = self._chat_service.get_pending_approval(session_id=self._session_id)
        if approval is None:
            self._pending_run_id = None
            return
        self._pending_run_id = approval.run_id
        self.apply_agent_event(
            {
                "type": "approval_requested",
                "payload": {
                    "message": approval.message,
                    "steps": [step.model_dump() for step in approval.steps],
                },
            }
        )

    def _handle_run_clicked(self) -> None:
        if self._chat_service is None:
            return
        if self._asset_type is None:
            self.apply_agent_event({"type": "assistant_error", "payload": {"message": "请先选择要连接和对话的资产"}})
            return
        result = self._chat_service.start_agent_run(
            conversation_id=self._conversation_id,
            user_message=self.input_box.toPlainText(),
            asset=self._asset,
            asset_type=self._asset_type,
            model_name=self.get_selected_model(),
            terminal_context=self._terminal_context,
            recent_messages=self._recent_messages,
        )
        self._pending_run_id = result.get("run_id")
        self._session_id = result.get("session_id", self._session_id)
        for event in result.get("ui_events", []):
            self.apply_agent_event(event)
            if self._agent_event_listener is not None:
                self._agent_event_listener(event)

    def _resume_pending_run(self, approved: bool) -> None:
        if self._chat_service is None or self._pending_run_id is None:
            return
        result = self._chat_service.resume_pending_approval(run_id=self._pending_run_id, approved=approved)
        for event in result.get("ui_events", []):
            self.apply_agent_event(event)
            if self._agent_event_listener is not None:
                self._agent_event_listener(event)
        self._pending_run_id = None
        self._restore_pending_approval()

    def apply_agent_event(self, event: dict) -> None:
        event_type = event["type"]
        payload = event.get("payload", {})
        lines: list[str] = []
        if event_type == "assistant_status":
            lines.append(f"状态: {payload['value']}")
        elif event_type == "plan_ready":
            lines.append("Plan:")
            for index, step in enumerate(payload.get("steps", []), start=1):
                lines.append(f"{index}. {step['title']} -> {step['command']}")
        elif event_type == "approval_requested":
            lines.append(payload.get("message", "等待审批"))
        elif event_type == "step_started":
            lines.append(f"执行: {payload['title']} -> {payload['command']}")
        elif event_type == "step_output":
            lines.append(payload.get("chunk", ""))
        elif event_type == "step_finished":
            lines.append(f"完成: {payload['command']} (exit={payload['exit_code']})")
        elif event_type == "terminal_output":
            return
        elif event_type == "assistant_chunk":
            lines.append(payload.get("chunk", ""))
        elif event_type == "assistant_final":
            lines.append(payload["message"])
        elif event_type == "assistant_error":
            lines.append(payload["message"])
        if lines:
            current = self.conversation_box.toPlainText()
            addition = "\n".join(lines)
            self.conversation_box.setPlainText(f"{current}\n{addition}".strip())
