import json

from sqlmodel import SQLModel, Session, create_engine, select
from PySide6.QtGui import QTextCursor

from app.main import build_main_window, main
from PySide6.QtWidgets import QApplication

from app.db.models import AgentTask, Approval, Asset, AssistantMessage, AssistantSession, TaskStep, TerminalEvent, TerminalSession
from app.services.chat_service import ChatService
from app.services.history_service import list_recent_tasks, list_session_messages, serialize_session_messages, split_active_and_completed_tasks
from app.shared.enums import AssetType
from app.shared.schemas import AssetCreate, PlanStep
from app.ui.asset_panel import AssetPanel
from app.ui.chat_panel import ChatPanel
from app.ui.main_window import MainWindow
from app.ui.settings_dialog import SettingsDialog
from app.ui.terminal_panel import TerminalPanel


def _build_isolated_main_window(monkeypatch, tmp_path, *, summary_chunks=None, settings_payload=None):
    db_path = tmp_path / "ui-flow.db"
    settings_path = tmp_path / "settings.json"
    test_engine = create_engine(f"sqlite:///{db_path}", connect_args={"check_same_thread": False})
    monkeypatch.setattr("app.shared.config.APP_DIR", tmp_path)
    monkeypatch.setattr("app.shared.config.DB_PATH", db_path)
    monkeypatch.setattr("app.shared.config.SETTINGS_PATH", settings_path)
    monkeypatch.setattr("app.db.session.APP_DIR", tmp_path)
    monkeypatch.setattr("app.db.session.DB_PATH", db_path)
    monkeypatch.setattr("app.db.session.engine", test_engine)
    monkeypatch.setattr("app.main.engine", test_engine)
    monkeypatch.setattr(
        "app.main.build_plan",
        lambda _asset_type, _user_input, terminal_context=None, recent_messages=None: [
            PlanStep(
                title="Check interface status",
                command="display interface brief",
                reason=terminal_context.selection_label if terminal_context else "no terminal context",
                risk_level="low",
            )
        ],
    )
    if settings_payload is not None:
        settings_path.write_text(json.dumps(settings_payload), encoding="utf-8")

    class FakeProvider:
        def stream_summarize(self, *, config, user_input, command_outputs, recent_messages=None):
            return iter(summary_chunks if summary_chunks is not None else ["检查完成"])

    monkeypatch.setattr("app.main.build_llm_provider", lambda _config: FakeProvider())
    return build_main_window(), test_engine, settings_path


def test_main_window_exposes_assets_terminal_and_assistant_panels():
    app = QApplication.instance() or QApplication([])
    window = MainWindow()

    assert window.windowTitle() == "Ops Agent"
    assert window.asset_panel is not None
    assert window.terminal_panel is not None
    assert window.assistant_panel is not None


def test_asset_panel_crud_updates_bound_list_widget():
    _app = QApplication.instance() or QApplication([])
    engine = create_engine("sqlite://")
    SQLModel.metadata.create_all(engine)
    panel = AssetPanel()
    panel.bind_asset_store(lambda: Session(engine))

    created = panel.create_asset(
        AssetCreate(
            name="edge-linux",
            asset_type=AssetType.LINUX,
            host="10.0.0.99",
            username="ops",
            auth_type="password",
        )
    )

    assert created is not None
    assert panel.asset_list.count() == 1
    assert panel.asset_list.item(0).text() == "edge-linux (linux) @ 10.0.0.99:22"

    panel.asset_list.setCurrentRow(0)
    updated = panel.update_selected_asset(
        AssetCreate(
            name="core-router",
            asset_type=AssetType.HUAWEI,
            host="10.0.0.10",
            port=2222,
            username="root",
            auth_type="key",
        )
    )

    assert updated is not None
    assert panel.asset_list.item(0).text() == "core-router (huawei) @ 10.0.0.10:2222"

    deleted = panel.delete_selected_asset()

    assert deleted is True
    assert panel.asset_list.count() == 0
    with Session(engine) as session:
        assert session.get(Asset, created.id) is None



def test_terminal_panel_opens_and_closes_bound_session(monkeypatch, tmp_path):
    app = QApplication.instance() or QApplication([])
    window, _engine, _settings_path = _build_isolated_main_window(monkeypatch, tmp_path)
    panel = window.terminal_panel

    assert panel.connect_button.isEnabled() is False

    window.asset_panel.create_asset(
        AssetCreate(
            name="core-router",
            asset_type=AssetType.HUAWEI,
            host="10.0.0.10",
            username="ops",
            auth_type="password",
        )
    )
    window.asset_panel.asset_list.setCurrentRow(0)
    app.processEvents()

    assert panel.status_label.text() == "Connected (session 1)"
    assert panel.terminal_view.toPlainText() == "demo terminal connected"
    assert panel.connect_button.isEnabled() is False
    assert panel.disconnect_button.isEnabled() is True

    panel.close_session()
    app.processEvents()

    assert panel.status_label.text() == "Disconnected"
    assert panel.connect_button.isEnabled() is True
    assert panel.disconnect_button.isEnabled() is False


def test_asset_panel_selection_listener_receives_selected_asset():
    _app = QApplication.instance() or QApplication([])
    engine = create_engine("sqlite://")
    SQLModel.metadata.create_all(engine)
    panel = AssetPanel()
    selected_assets = []
    panel.bind_asset_store(lambda: Session(engine))
    panel.bind_selection_listener(lambda asset: selected_assets.append(asset))

    panel.create_asset(
        AssetCreate(
            name="edge-linux",
            asset_type=AssetType.LINUX,
            host="10.0.0.99",
            username="ops",
            auth_type="password",
        )
    )
    panel.asset_list.setCurrentRow(0)

    assert selected_assets[-1] is not None
    assert selected_assets[-1].name == "edge-linux"
    assert selected_assets[-1].host == "10.0.0.99"



def test_asset_selection_syncs_terminal_and_chat_contexts():
    _app = QApplication.instance() or QApplication([])
    engine = create_engine("sqlite://")
    SQLModel.metadata.create_all(engine)
    panel = AssetPanel()
    terminal_assets = []
    chat_assets = []
    panel.bind_asset_store(lambda: Session(engine))
    panel.bind_selection_listener(lambda asset: terminal_assets.append(asset))
    panel.bind_selection_listener(lambda asset: chat_assets.append(asset))

    panel.create_asset(
        AssetCreate(
            name="core-router",
            asset_type=AssetType.HUAWEI,
            host="10.0.0.10",
            username="ops",
            auth_type="password",
        )
    )
    panel.asset_list.setCurrentRow(0)

    assert terminal_assets[-1] is not None
    assert chat_assets[-1] is not None
    assert terminal_assets[-1].id == chat_assets[-1].id
    assert terminal_assets[-1].asset_type == "huawei"


def test_chat_panel_removes_completed_tasks_from_active_area():
    app = QApplication.instance() or QApplication([])
    panel = ChatPanel()

    panel.conversation_box.setPlainText("task: pending")
    panel.conversation_box.setPlainText("summary: completed")
    app.processEvents()

    assert "summary: completed" in panel.conversation_box.toPlainText()


def test_chat_panel_renders_agent_events_for_plan_and_summary():
    app = QApplication.instance() or QApplication([])
    panel = ChatPanel()

    panel.apply_agent_event({"type": "assistant_status", "run_id": "run-1", "payload": {"value": "thinking"}})
    panel.apply_agent_event(
        {
            "type": "plan_ready",
            "run_id": "run-1",
            "payload": {
                "steps": [
                    {"title": "Check interface status", "command": "display interface brief"},
                    {"title": "Check routing table", "command": "display ip routing-table"},
                ]
            },
        }
    )
    panel.apply_agent_event({"type": "assistant_status", "run_id": "run-1", "payload": {"value": "summarizing"}})
    panel.apply_agent_event({"type": "assistant_chunk", "run_id": "run-1", "payload": {"chunk": "检查"}})
    panel.apply_agent_event({"type": "assistant_chunk", "run_id": "run-1", "payload": {"chunk": "完成"}})
    panel.apply_agent_event({"type": "assistant_final", "run_id": "run-1", "payload": {"message": "检查完成"}})
    app.processEvents()

    text = panel.conversation_box.toPlainText()
    assert "状态: thinking" in text
    assert "Plan:" in text
    assert "1. Check interface status -> display interface brief" in text
    assert "2. Check routing table -> display ip routing-table" in text
    assert "状态: summarizing" in text
    assert "检查" in text
    assert "完成" in text
    assert text.strip().endswith("检查完成")


def test_terminal_panel_renders_terminal_output_events_only():
    app = QApplication.instance() or QApplication([])
    panel = TerminalPanel()

    panel.apply_agent_event({"type": "assistant_chunk", "run_id": "run-1", "payload": {"chunk": "忽略"}})
    panel.apply_agent_event({"type": "terminal_output", "run_id": "run-1", "payload": {"chunk": "display interface brief"}})
    panel.apply_agent_event({"type": "terminal_output", "run_id": "run-1", "payload": {"chunk": "GigabitEthernet0/0/1 up"}})
    app.processEvents()

    assert panel.terminal_view.toPlainText() == "display interface brief\nGigabitEthernet0/0/1 up"


def test_build_main_window_binds_live_chat_service():
    _app = QApplication.instance() or QApplication([])

    window = build_main_window()

    assert isinstance(window, MainWindow)
    assert isinstance(window.assistant_panel._chat_service, ChatService)
    assert window.assistant_panel._model_name == "claude-opus-4-7"


def test_build_main_window_loads_model_settings_into_selector(monkeypatch, tmp_path):
    _app = QApplication.instance() or QApplication([])
    window, _engine, _settings_path = _build_isolated_main_window(
        monkeypatch,
        tmp_path,
        settings_payload={
            "provider": "anthropic",
            "model_name": "claude-sonnet-4-6",
            "base_url": "https://api.anthropic.com",
            "api_key": "test-key",
            "timeout_seconds": 30,
            "temperature": 0.2,
            "max_tokens": 256,
        },
    )

    assert window.assistant_panel.model_selector.count() == 2
    assert window.assistant_panel.model_selector.currentText() == "claude-sonnet-4-6"
    assert window.assistant_panel._model_name == "claude-sonnet-4-6"



def test_build_main_window_syncs_selected_asset_to_chat_panel(monkeypatch, tmp_path):
    app = QApplication.instance() or QApplication([])
    window, _engine, _settings_path = _build_isolated_main_window(monkeypatch, tmp_path)
    window.asset_panel.create_asset(
        AssetCreate(
            name="core-router",
            asset_type=AssetType.HUAWEI,
            host="10.0.0.10",
            username="ops",
            auth_type="password",
        )
    )

    window.asset_panel.asset_list.setCurrentRow(0)
    app.processEvents()

    assert window.assistant_panel._asset_type is AssetType.HUAWEI
    assert window.assistant_panel._asset is not None
    assert window.assistant_panel._asset.asset_type == "huawei"
    assert window.terminal_panel._asset is not None
    assert window.terminal_panel._asset.asset_type == "huawei"
    assert window.terminal_panel._terminal_session_id == 1
    assert window.terminal_panel.status_label.text() == "Connected (session 1)"



def test_build_main_window_attaches_terminal_selection_to_chat_run(monkeypatch, tmp_path):
    app = QApplication.instance() or QApplication([])
    window, _engine, _settings_path = _build_isolated_main_window(monkeypatch, tmp_path)
    window.asset_panel.create_asset(
        AssetCreate(
            name="core-router",
            asset_type=AssetType.HUAWEI,
            host="10.0.0.10",
            username="ops",
            auth_type="password",
        )
    )

    window.asset_panel.asset_list.setCurrentRow(0)
    app.processEvents()

    terminal = window.terminal_panel
    cursor = terminal.terminal_view.textCursor()
    cursor.select(QTextCursor.SelectionType.Document)
    terminal.terminal_view.setTextCursor(cursor)

    window.assistant_panel.attach_context_button.click()
    window.assistant_panel.input_box.setPlainText("检查当前终端输出")
    window.assistant_panel.run_button.click()
    app.processEvents()

    assert window.assistant_panel._chat_service is not None
    runtime = window.assistant_panel._chat_service._runtime
    terminal_context = runtime._state_cache["run-1"]["terminal_context"]

    assert terminal_context is not None
    assert terminal_context.terminal_session_id == 1
    assert terminal_context.selected_text == "demo terminal connected"


def test_build_main_window_persists_terminal_session_and_events(monkeypatch, tmp_path):
    app = QApplication.instance() or QApplication([])
    window, test_engine, _settings_path = _build_isolated_main_window(monkeypatch, tmp_path)
    window.asset_panel.create_asset(
        AssetCreate(
            name="core-router",
            asset_type=AssetType.HUAWEI,
            host="10.0.0.10",
            username="ops",
            auth_type="password",
        )
    )
    window.asset_panel.asset_list.setCurrentRow(0)
    app.processEvents()

    terminal = window.terminal_panel
    cursor = terminal.terminal_view.textCursor()
    cursor.select(QTextCursor.SelectionType.Document)
    terminal.terminal_view.setTextCursor(cursor)
    window.assistant_panel.attach_context_button.click()
    window.assistant_panel.input_box.setPlainText("检查当前终端输出")
    window.assistant_panel.run_button.click()
    app.processEvents()
    window.assistant_panel.approve_button.click()
    app.processEvents()

    with Session(test_engine) as session:
        assistant_sessions = list(session.exec(select(AssistantSession)).all())
        assistant_messages = list(session.exec(select(AssistantMessage)).all())
        agent_tasks = list(session.exec(select(AgentTask)).all())
        task_steps = list(session.exec(select(TaskStep)).all())
        approvals = list(session.exec(select(Approval)).all())
        terminal_sessions = list(session.exec(select(TerminalSession)).all())
        terminal_events = list(session.exec(select(TerminalEvent)).all())
        recent_tasks = list_recent_tasks(session)
        restored_messages = list_session_messages(session, assistant_sessions[0].id or 0)

    terminal_events.sort(key=lambda event: event.id or 0)
    assistant_messages.sort(key=lambda message: message.id or 0)
    task_steps.sort(key=lambda step: step.id or 0)

    assert len(assistant_sessions) == 1
    assert assistant_sessions[0].asset_id == 1
    assert assistant_sessions[0].title == "conversation-1"
    assert [(message.role, message.content) for message in assistant_messages] == [
        ("user", "检查当前终端输出"),
        ("assistant", "检查完成"),
    ]
    assert len(agent_tasks) == 1
    assert agent_tasks[0].session_id == assistant_sessions[0].id
    assert agent_tasks[0].status == "completed"
    assert agent_tasks[0].final_summary == "检查完成"
    assert [task.id for task in recent_tasks] == [agent_tasks[0].id]
    active_tasks, history_tasks = split_active_and_completed_tasks([
        {"task_id": task.id, "status": task.status} for task in recent_tasks
    ])
    assert active_tasks == []
    assert history_tasks == [{"task_id": agent_tasks[0].id, "status": "completed"}]
    assert serialize_session_messages(restored_messages) == [
        {"role": "user", "content": "检查当前终端输出"},
        {"role": "assistant", "content": "检查完成"},
    ]
    assert len(task_steps) == 1
    assert task_steps[0].task_id == agent_tasks[0].id
    assert task_steps[0].status == "completed"
    assert len(approvals) == 1
    assert approvals[0].task_id == agent_tasks[0].id
    assert approvals[0].decision == "approved"
    assert len(terminal_sessions) == 1
    assert terminal_sessions[0].asset_id == 1
    assert terminal_sessions[0].status == "connected"
    assert [event.event_type for event in terminal_events] == ["connected", "context_attached", "terminal_output"]
    assert "demo output: display interface brief" in terminal_events[-1].event_data


def test_build_main_window_populates_history_list_for_selected_asset(monkeypatch, tmp_path):
    app = QApplication.instance() or QApplication([])
    window, _engine, _settings_path = _build_isolated_main_window(monkeypatch, tmp_path)
    window.asset_panel.create_asset(
        AssetCreate(
            name="core-router",
            asset_type=AssetType.HUAWEI,
            host="10.0.0.10",
            username="ops",
            auth_type="password",
        )
    )
    window.asset_panel.asset_list.setCurrentRow(0)
    window.assistant_panel.input_box.setPlainText("检查当前终端输出")
    window.assistant_panel.run_button.click()
    app.processEvents()
    window.assistant_panel.approve_button.click()
    app.processEvents()

    window.asset_panel.asset_list.setCurrentRow(0)
    app.processEvents()

    assert window.asset_panel.history_list.count() == 1
    assert window.asset_panel.history_list.item(0).text() == "conversation-1"


def test_build_main_window_restores_messages_when_history_item_is_clicked(monkeypatch, tmp_path):
    app = QApplication.instance() or QApplication([])
    window, _engine, _settings_path = _build_isolated_main_window(monkeypatch, tmp_path)
    window.asset_panel.create_asset(
        AssetCreate(
            name="core-router",
            asset_type=AssetType.HUAWEI,
            host="10.0.0.10",
            username="ops",
            auth_type="password",
        )
    )
    window.asset_panel.asset_list.setCurrentRow(0)
    window.assistant_panel.input_box.setPlainText("检查当前终端输出")
    window.assistant_panel.run_button.click()
    app.processEvents()
    window.assistant_panel.approve_button.click()
    app.processEvents()

    window.assistant_panel.conversation_box.clear()
    history_item = window.asset_panel.history_list.item(0)
    window.asset_panel.history_list.itemClicked.emit(history_item)
    app.processEvents()

    text = window.assistant_panel.conversation_box.toPlainText()
    assert "user: 检查当前终端输出" in text
    assert "assistant: 检查完成" in text
    assert window.assistant_panel._session_id == 1



def test_build_main_window_uses_llm_provider_factory(monkeypatch):
    _app = QApplication.instance() or QApplication([])
    calls = []

    class FakeProvider:
        def summarize(self, *, config, user_input, command_outputs, recent_messages=None):
            return "factory summary"

    monkeypatch.setattr("app.main.build_llm_provider", lambda config: calls.append(config) or FakeProvider())

    window = build_main_window()

    assert isinstance(window, MainWindow)
    assert len(calls) == 2
    assert all(call.provider.value == "anthropic" for call in calls)


def test_settings_dialog_saves_and_applies_model_config(monkeypatch, tmp_path):
    _app = QApplication.instance() or QApplication([])
    window, _engine, settings_path = _build_isolated_main_window(monkeypatch, tmp_path)
    applied_configs = []

    def save_and_apply(config):
        applied_configs.append(config)
        window.assistant_panel.set_available_models(["gpt-5.5", "gpt-5.4"], config.model_name)
        window.assistant_panel.set_session_context(
            conversation_id=window.assistant_panel._conversation_id,
            asset_type=window.assistant_panel._asset_type,
            model_name=config.model_name,
            terminal_context=window.assistant_panel._terminal_context,
            recent_messages=window.assistant_panel._recent_messages,
        )
        settings_path.write_text(
            json.dumps(
                {
                    "provider": config.provider.value,
                    "model_name": config.model_name,
                    "base_url": config.base_url,
                    "api_key": config.api_key.get_secret_value(),
                    "timeout_seconds": config.timeout_seconds,
                    "temperature": config.temperature,
                    "max_tokens": config.max_tokens,
                }
            ),
            encoding="utf-8",
        )

    assert window.assistant_panel._chat_service is not None
    dialog = SettingsDialog(window.assistant_panel._chat_service._runtime._model_config, save_and_apply)
    dialog.provider_input.setText("openai_compatible")
    dialog.model_input.setText("gpt-5.5")
    dialog.base_url_input.setText("https://example.test/v1")
    dialog.api_key_input.setText("saved-key")
    dialog.save_button.click()

    payload = json.loads(settings_path.read_text(encoding="utf-8"))

    assert applied_configs[0].provider.value == "openai_compatible"
    assert payload["provider"] == "openai_compatible"
    assert payload["model_name"] == "gpt-5.5"
    assert payload["base_url"] == "https://example.test/v1"
    assert payload["api_key"] == "saved-key"
    assert window.assistant_panel.model_selector.currentText() == "gpt-5.5"
    assert window.assistant_panel._model_name == "gpt-5.5"



def test_main_bootstrap_initializes_database_without_starting_api_server(monkeypatch):
    calls = []

    monkeypatch.setattr("app.main.init_db", lambda: calls.append("init_db"))
    monkeypatch.setattr("app.main.QApplication", lambda args: type("FakeApp", (), {"exec": lambda self: 0})())
    monkeypatch.setattr("app.main.build_main_window", lambda: type("FakeWindow", (), {"show": lambda self: calls.append("show")})())
    monkeypatch.setattr("app.main.sys.exit", lambda code: calls.append(("exit", code)))

    main()

    assert calls[0] == "init_db"
    assert calls[1] == "show"
