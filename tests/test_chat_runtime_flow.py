from PySide6.QtWidgets import QApplication

from app.shared.enums import AssetType
from app.shared.schemas import TerminalContextAttachment
from app.ui.chat_panel import ChatPanel
from app.ui.terminal_panel import TerminalPanel


class FakeRuntime:
    def __init__(self):
        self.start_calls = []
        self.resume_calls = []

    def start_run(self, **kwargs):
        self.start_calls.append(kwargs)
        return {
            "run_id": kwargs["run_id"],
            "session_id": kwargs["session_id"],
            "ui_events": [
                {"type": "assistant_status", "run_id": kwargs["run_id"], "payload": {"value": "thinking"}},
                {
                    "type": "plan_ready",
                    "run_id": kwargs["run_id"],
                    "payload": {
                        "steps": [
                            {"title": "Check interface status", "command": "display interface brief", "reason": "selected interface"}
                        ]
                    },
                },
                {"type": "approval_requested", "run_id": kwargs["run_id"], "payload": {"message": "Approve this execution plan?"}},
            ],
            "__interrupt__": [object()],
        }

    def resume_run(self, *, run_id: str, approved: bool):
        self.resume_calls.append({"run_id": run_id, "approved": approved})
        return {
            "run_id": run_id,
            "ui_events": [
                {"type": "assistant_status", "run_id": run_id, "payload": {"value": "executing"}},
                {"type": "terminal_output", "run_id": run_id, "payload": {"chunk": "GigabitEthernet0/0/1 up"}},
                {"type": "assistant_final", "run_id": run_id, "payload": {"message": "检查完成"}},
            ],
        }


class FakeChatService:
    def __init__(self, runtime):
        self._runtime = runtime
        self.pending_approval: object | None = None
        self.pending_calls = []

    def start_agent_run(self, *, conversation_id, user_message, asset, asset_type, model_name, terminal_context=None, recent_messages=None):
        return self._runtime.start_run(
            conversation_id=conversation_id,
            run_id="run-1",
            user_message=user_message,
            asset_type=asset_type,
            asset_id=getattr(asset, "id", 0) if asset is not None else 0,
            session_id=1,
            model_name=model_name,
            terminal_context=terminal_context,
            recent_messages=recent_messages or [],
        )

    def resume_agent_run(self, *, run_id, approved):
        return self._runtime.resume_run(run_id=run_id, approved=approved)

    def resume_pending_approval(self, *, run_id, approved):
        return self.resume_agent_run(run_id=run_id, approved=approved)

    def get_pending_approval(self, *, session_id):
        self.pending_calls.append(session_id)
        return self.pending_approval


def test_chat_panel_submits_user_message_through_chat_service_and_renders_events():
    app = QApplication.instance() or QApplication([])
    runtime = FakeRuntime()
    panel = ChatPanel()
    panel.bind_chat_service(FakeChatService(runtime))
    panel.set_available_models(["claude-opus-4-7", "claude-sonnet-4-6"], "claude-sonnet-4-6")
    panel.set_session_context(
        conversation_id="conv-1",
        asset_type=AssetType.HUAWEI,
        model_name="claude-sonnet-4-6",
        terminal_context=TerminalContextAttachment(
            terminal_session_id=1,
            selection_label="selected interface",
            selected_text="GigabitEthernet0/0/1 up",
        ),
        recent_messages=[{"role": "user", "content": "上一轮"}],
    )
    panel.set_asset_context(type("Asset", (), {"id": 1, "asset_type": "huawei"})())
    panel.input_box.setPlainText("检查接口状态")

    panel.run_button.click()
    app.processEvents()

    assert runtime.start_calls[0]["conversation_id"] == "conv-1"
    assert runtime.start_calls[0]["user_message"] == "检查接口状态"
    assert runtime.start_calls[0]["asset_type"] is AssetType.HUAWEI
    assert runtime.start_calls[0]["model_name"] == "claude-sonnet-4-6"
    assert runtime.start_calls[0]["terminal_context"].selection_label == "selected interface"
    text = panel.conversation_box.toPlainText()
    assert "状态: thinking" in text
    assert "Plan:" in text
    assert panel._pending_run_id == "run-1"


def test_chat_panel_uses_current_model_selector_value_for_new_run():
    app = QApplication.instance() or QApplication([])
    runtime = FakeRuntime()
    panel = ChatPanel()
    panel.bind_chat_service(FakeChatService(runtime))
    panel.set_available_models(["claude-opus-4-7", "claude-sonnet-4-6"], "claude-opus-4-7")
    panel.set_session_context(
        conversation_id="conv-1",
        asset_type=AssetType.HUAWEI,
        model_name="claude-opus-4-7",
    )
    panel.set_asset_context(type("Asset", (), {"id": 1, "asset_type": "huawei"})())
    panel.model_selector.setCurrentText("claude-sonnet-4-6")
    panel.input_box.setPlainText("检查接口状态")

    panel.run_button.click()
    app.processEvents()

    assert runtime.start_calls[0]["model_name"] == "claude-sonnet-4-6"


def test_chat_panel_approve_button_resumes_pending_run_and_renders_final_message():
    app = QApplication.instance() or QApplication([])
    runtime = FakeRuntime()
    panel = ChatPanel()
    panel.bind_chat_service(FakeChatService(runtime))
    panel._pending_run_id = "run-1"

    panel.approve_button.click()
    app.processEvents()

    assert runtime.resume_calls == [{"run_id": "run-1", "approved": True}]
    assert panel.conversation_box.toPlainText().strip().endswith("检查完成")


def test_chat_panel_forwards_terminal_output_events_to_listener():
    app = QApplication.instance() or QApplication([])
    runtime = FakeRuntime()
    panel = ChatPanel()
    terminal_panel = TerminalPanel()
    panel.bind_chat_service(FakeChatService(runtime))
    panel.bind_agent_event_listener(terminal_panel.apply_agent_event)
    panel._pending_run_id = "run-1"

    panel.approve_button.click()
    app.processEvents()

    assert "GigabitEthernet0/0/1 up" in terminal_panel.terminal_view.toPlainText()


def test_chat_panel_reject_button_resumes_pending_run_with_rejection():
    app = QApplication.instance() or QApplication([])
    runtime = FakeRuntime()
    panel = ChatPanel()
    panel.bind_chat_service(FakeChatService(runtime))
    panel._pending_run_id = "run-1"

    panel.reject_button.click()
    app.processEvents()

    assert runtime.resume_calls == [{"run_id": "run-1", "approved": False}]


def test_chat_panel_restores_pending_approval_from_chat_service():
    app = QApplication.instance() or QApplication([])
    runtime = FakeRuntime()
    service = FakeChatService(runtime)
    service.pending_approval = type(
        "ApprovalView",
        (),
        {
            "run_id": "run-9",
            "message": "Approve this execution plan?",
            "steps": [
                type(
                    "PlanStep",
                    (),
                    {
                        "model_dump": lambda _self: {
                            "title": "Check interface status",
                            "command": "display interface brief",
                            "reason": "selected interface",
                        }
                    },
                )()
            ],
        },
    )()
    panel = ChatPanel()
    panel._session_id = 1
    panel.bind_chat_service(service)
    app.processEvents()

    assert service.pending_calls == [1]
    assert panel._pending_run_id == "run-9"
    assert "Approve this execution plan?" in panel.conversation_box.toPlainText()


def test_chat_panel_shows_error_when_no_asset_is_selected():
    app = QApplication.instance() or QApplication([])
    runtime = FakeRuntime()
    panel = ChatPanel()
    panel.bind_chat_service(FakeChatService(runtime))
    panel.input_box.setPlainText("检查接口状态")

    panel.run_button.click()
    app.processEvents()

    assert runtime.start_calls == []
    assert "请先选择要连接和对话的资产" in panel.conversation_box.toPlainText()
