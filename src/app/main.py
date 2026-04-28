import json
import os
import sys
from datetime import UTC, datetime

from pydantic import SecretStr
from PySide6.QtWidgets import QApplication
from sqlmodel import Session

from app.core.agent.runtime import AgentRuntime
from app.core.agent.planner import build_plan
from app.core.connectors.network import NetworkConnector
from app.core.connectors.server import ServerConnector
from app.db.repositories import (
    create_agent_task,
    create_approval,
    create_model_usage,
    create_task_steps,
    create_terminal_event,
    create_terminal_session,
    get_latest_approval_by_task_id,
    get_pending_agent_task_by_session_id,
    list_task_steps_by_task_id,
    update_agent_task,
    update_task_step,
    update_terminal_session,
)
from app.db.session import engine, init_db
from app.integrations.llm.factory import build_llm_provider
from app.services.asset_service import get_asset_credential_record
from app.services.assistant_session_service import create_or_get_assistant_session, list_assistant_session_records
from app.services.chat_service import ChatService
from app.services.message_service import AssistantMessageService
from app.services.credential_service import CredentialService
from app.services.model_service import ModelService
from app.services.terminal_service import TerminalService
from app.shared.config import APP_DIR
from app.shared.enums import AssetType, TaskStatus
from app.shared.schemas import ModelConfig
from app.ui.main_window import MainWindow
from app.ui.settings_dialog import SettingsDialog


class DemoConnector:
    def run_command(self, command: str) -> str:
        return f"demo output: {command}"

    def open_interactive(self) -> object:
        return "demo terminal connected"

    def close(self) -> None:
        return None


def _run_connector_command(connector, command: str, emit=None) -> str:
    output = connector.run_command(command)
    if emit is not None:
        emit(output)
    return output


def _build_connector(asset):
    if asset is None:
        raise ValueError("asset is required")
    with Session(engine) as session:
        credential = get_asset_credential_record(session, asset.id)
    if credential is None:
        return DemoConnector()
    secret_key = os.environ.get("OPS_AGENT_SECRET_KEY", "dev-secret-key")
    credential_service = CredentialService(secret_key=secret_key)
    secret = credential_service.decrypt_secret(credential.encrypted_blob)
    asset_type = AssetType(asset.asset_type)
    if asset_type is AssetType.LINUX:
        return ServerConnector(
            host=asset.host,
            port=asset.port,
            username=asset.username,
            password=secret,
        )
    if asset_type is AssetType.HUAWEI:
        return NetworkConnector(
            {
                "device_type": "huawei",
                "host": asset.host,
                "port": asset.port,
                "username": asset.username,
                "password": secret,
            }
        )
    raise ValueError(f"unsupported asset type: {asset.asset_type}")


class AssistantSessionStore:
    def get_or_create(self, *, asset_id: int, conversation_id: str, model_name: str):
        with Session(engine) as session:
            return create_or_get_assistant_session(
                session,
                asset_id=asset_id,
                conversation_id=conversation_id,
                model_name=model_name,
            )

    def list_by_asset_id(self, asset_id: int):
        with Session(engine) as session:
            return list_assistant_session_records(session, asset_id)


class ApprovalStore:
    def get_pending_task_by_session_id(self, session_id: int):
        with Session(engine) as session:
            return get_pending_agent_task_by_session_id(session, session_id)

    def list_steps_by_task_id(self, task_id: int):
        with Session(engine) as session:
            return list_task_steps_by_task_id(session, task_id)

    def get_latest_approval_by_task_id(self, task_id: int):
        with Session(engine) as session:
            return get_latest_approval_by_task_id(session, task_id)


class RuntimePersistence:
    def create_task(self, *, session_id: int, run_id: str, asset_id: int, user_input: str, terminal_context, plan_steps):
        task_type = plan_steps[0].title if plan_steps else "task"
        risk_level = plan_steps[0].risk_level if plan_steps else "low"
        attached_terminal_context = ""
        if terminal_context is not None:
            attached_terminal_context = json.dumps(terminal_context.model_dump(), ensure_ascii=False)
        with Session(engine) as session:
            row = create_agent_task(
                session,
                session_id=session_id,
                run_id=run_id,
                asset_id=asset_id,
                user_input=user_input,
                attached_terminal_context=attached_terminal_context,
                task_type=task_type,
                risk_level=risk_level,
                status=TaskStatus.PENDING_APPROVAL.value,
            )
            return row.id or 0

    def create_steps(self, *, task_id: int, plan_steps):
        with Session(engine) as session:
            rows = create_task_steps(session, task_id, plan_steps)
            return [row.id or 0 for row in rows]

    def update_task_status(self, *, task_id: int, status: str, final_summary: str | None = None):
        with Session(engine) as session:
            update_agent_task(session, task_id, status=status, final_summary=final_summary)

    def update_step(
        self,
        *,
        step_id: int,
        status: str,
        output: str | None = None,
        error_message: str | None = None,
        started_at: datetime | None = None,
        finished_at: datetime | None = None,
    ):
        with Session(engine) as session:
            update_task_step(
                session,
                step_id,
                status=status,
                output=output,
                error_message=error_message,
                started_at=started_at,
                finished_at=finished_at,
            )

    def record_approval(self, *, task_id: int, approved: bool):
        with Session(engine) as session:
            create_approval(
                session,
                task_id=task_id,
                decision="approved" if approved else "rejected",
                operator="ui",
            )

    def record_terminal_event(self, *, terminal_session_id: int, event_type: str, metadata=""):
        with Session(engine) as session:
            create_terminal_event(session, terminal_session_id, event_type, metadata)

    def record_model_usage(
        self,
        *,
        task_id: int,
        provider: str,
        model_name: str,
        base_url_snapshot: str,
        temperature_snapshot: float,
        max_tokens_snapshot: int,
    ):
        with Session(engine) as session:
            create_model_usage(
                session,
                task_id=task_id,
                provider=provider,
                model_name=model_name,
                base_url_snapshot=base_url_snapshot,
                temperature_snapshot=temperature_snapshot,
                max_tokens_snapshot=max_tokens_snapshot,
            )


class TerminalPersistence:
    def create_session(self, asset_id: int) -> int:
        with Session(engine) as session:
            row = create_terminal_session(session, asset_id)
            return row.id or 0

    def update_session(self, terminal_session_id: int, *, status: str | None = None, last_error: str | None = None, ended: bool = False):
        with Session(engine) as session:
            update_terminal_session(
                session,
                terminal_session_id,
                status=status,
                last_error=last_error,
                ended_at=datetime.now(UTC) if ended else None,
            )

    def record_event(self, terminal_session_id: int, event_type: str, metadata=""):
        with Session(engine) as session:
            create_terminal_event(session, terminal_session_id, event_type, metadata)


def build_main_window() -> MainWindow:
    init_db()
    selected_asset = {"value": None}
    model_service = ModelService()
    model_config = model_service.load_settings()
    provider = build_llm_provider(model_config)

    def execute_step(step, emit=None):
        asset = selected_asset["value"]
        connector = _build_connector(asset) if asset is not None else DemoConnector()
        asset_name = getattr(asset, "name", None) if asset is not None else None
        output = _run_connector_command(connector, step.command, emit)
        if asset_name:
            output = f"[{asset_name}] {output}"
        return {
            "command": step.command,
            "output": output,
            "error": "",
            "status": "completed",
            "exit_code": 0,
            "title": step.title,
        }

    runtime = AgentRuntime(
        planner=build_plan,
        step_executor=execute_step,
        summarizer=lambda user_input, execution_results, recent_messages=None: provider.stream_summarize(
            config=model_config,
            user_input=user_input,
            command_outputs=[result.get("output") or result.get("stdout", "") for result in execution_results],
            recent_messages=recent_messages,
        ),
        persistence=RuntimePersistence(),
        model_config=model_config,
    )
    window = MainWindow()

    def apply_model_config(config):
        nonlocal model_config, provider
        model_config = config
        provider = build_llm_provider(model_config)
        runtime._model_config = model_config
        window.assistant_panel.set_available_models(
            model_service.list_available_models(model_config.provider),
            model_config.model_name,
        )
        window.assistant_panel.set_session_context(
            conversation_id=window.assistant_panel._conversation_id,
            asset_type=window.assistant_panel._asset_type,
            model_name=model_config.model_name,
            terminal_context=window.assistant_panel._terminal_context,
            recent_messages=window.assistant_panel._recent_messages,
        )

    def save_model_config(config):
        apply_model_config(model_service.save_settings(config))

    def open_settings_dialog() -> None:
        dialog = SettingsDialog(model_config, save_model_config)
        dialog.exec()
    window.settings_button.clicked.connect(open_settings_dialog)
    window.asset_panel.bind_asset_store(lambda: Session(engine))
    chat_service = ChatService(
        runtime=runtime,
        session_store=AssistantSessionStore(),
        message_service=AssistantMessageService(lambda: Session(engine)),
        approval_store=ApprovalStore(),
    )
    window.assistant_panel.bind_chat_service(chat_service)
    window.asset_panel.bind_history_loader(
        lambda asset: chat_service.list_assistant_sessions(asset_id=asset.id) if asset is not None else []
    )
    apply_model_config(model_config)
    terminal_service = TerminalService(
        connector_factory=_build_connector,
        persistence=TerminalPersistence(),
    )
    window.terminal_panel.bind_terminal_service(terminal_service)
    window.terminal_panel.bind_context_attached_listener(window.assistant_panel.set_terminal_context)

    def handle_agent_event(event) -> None:
        window.terminal_panel.apply_agent_event(event)
        if event.get("type") == "assistant_final":
            refresh_selected_asset_history()

    window.assistant_panel.bind_agent_event_listener(handle_agent_event)
    window.assistant_panel.attach_context_button.clicked.connect(window.terminal_panel.attach_selected_context)

    def refresh_selected_asset_history() -> None:
        asset = selected_asset["value"]
        window.asset_panel.refresh_history(asset)

    def handle_history_selected(session_id: int, model_name: str | None) -> None:
        messages = chat_service.list_assistant_messages(session_id=session_id)
        window.assistant_panel.load_session(
            session_id=session_id,
            messages=messages,
            model_name=model_name or model_config.model_name,
        )

    def handle_asset_selected(asset) -> None:
        selected_asset["value"] = asset
        window.terminal_panel.set_asset_context(asset)
        window.assistant_panel.set_asset_context(asset)
        if asset is None:
            return
        sessions = chat_service.list_assistant_sessions(asset_id=asset.id)
        if sessions:
            latest_session = sessions[0]
            handle_history_selected(latest_session.id or 0, latest_session.active_model)

    window.asset_panel.bind_history_selection_listener(handle_history_selected)
    window.asset_panel.bind_selection_listener(handle_asset_selected)
    if window.asset_panel.asset_list.count() > 0:
        window.asset_panel.asset_list.setCurrentRow(0)
    else:
        window.terminal_panel.set_asset_context(None)
        window.assistant_panel.set_asset_context(None)
    return window


def main() -> None:
    APP_DIR.mkdir(parents=True, exist_ok=True)
    init_db()
    app = QApplication(sys.argv)
    window = build_main_window()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
