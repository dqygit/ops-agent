import json
import os
from datetime import UTC, datetime
from importlib import import_module
from typing import Any

from sqlmodel import Session

from app.api import app
from app.api.dependencies import get_chat_service
from app.api.terminal import get_terminal_service
from app.core.agent.planner import build_plan
from app.core.agent.runtime import AgentRuntime
from app.core.connectors.network import NetworkConnector
from app.core.connectors.server import ServerConnector
from app.core.terminal.local_pty import LocalPtyConnector
from app.db.repositories import (
    create_agent_task,
    create_approval,
    create_command_execution,
    create_model_usage,
    create_task_steps,
    create_terminal_event,
    create_terminal_session,
    get_latest_approval_by_task_id,
    get_pending_agent_task_by_session_id,
    list_task_steps_by_task_id,
    update_agent_task,
    update_command_execution,
    update_task_step,
    update_terminal_session,
)
from app.db.session import engine, init_db
from app.integrations.llm.factory import build_llm_provider
from app.services.asset_service import get_asset_credential_record, get_asset_record
from app.services.assistant_session_service import create_or_get_assistant_session, list_assistant_session_records
from app.services.auto_approval_service import AutoApprovalService
from app.services.chat_service import ChatService
from app.services.credential_service import CredentialService
from app.services.message_service import AssistantMessageService
from app.services.model_service import ModelService
from app.services.secret_key import get_ops_agent_secret_key
from app.services.terminal_service import TerminalService
from app.shared.config import APP_DIR
from app.shared.enums import AssetType, TaskStatus
from app.shared.schemas import ModelConfig


class DemoConnector:
    def __init__(self):
        self._output = ""

    def run_command(self, command: str) -> str:
        return f"demo output: {command}"

    def open_interactive(self) -> object:
        return "demo terminal connected"

    def read(self) -> str:
        output = self._output
        self._output = ""
        return output

    def write(self, data: str) -> None:
        self._output += f"demo output: {data}"

    def resize(self, cols: int, rows: int) -> None:
        return None

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
    asset_type = AssetType(asset.asset_type)
    if asset_type is AssetType.LOCAL_TERMINAL:
        return LocalPtyConnector()
    with Session(engine) as session:
        credential = get_asset_credential_record(session, asset.id)
    if credential is None:
        raise ValueError("missing credentials for asset")
    credential_service = CredentialService(secret_key=get_ops_agent_secret_key())
    secret = credential_service.decrypt_secret(credential.encrypted_blob)
    if asset_type is AssetType.LINUX:
        return ServerConnector(
            host=asset.host,
            port=asset.port,
            username=asset.username,
            password=secret,
        )
    network_device_types = {
        AssetType.NETWORK: asset.vendor or "generic",
        AssetType.CISCO: "cisco",
        AssetType.HUAWEI: "huawei",
        AssetType.JUNIPER: "juniper",
        AssetType.H3C: "h3c",
    }
    if asset_type in network_device_types:
        return NetworkConnector(
            {
                "device_type": network_device_types[asset_type],
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
            attached_terminal_context = json.dumps(_dump_terminal_context(terminal_context), ensure_ascii=False)
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
        exit_code: int | None = None,
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
                exit_code=exit_code,
                started_at=started_at,
                finished_at=finished_at,
            )

    def record_approval(self, *, task_id: int, asset_id: int, terminal_context, steps, step_ids, approved: bool):
        terminal_session_id = _get_terminal_session_id(terminal_context)
        with Session(engine) as session:
            for index, step in enumerate(steps):
                create_approval(
                    session,
                    task_id=task_id,
                    step_id=step_ids[index] if index < len(step_ids) else None,
                    asset_id=asset_id,
                    terminal_session_id=terminal_session_id,
                    command=step.command,
                    working_directory=step.working_directory,
                    risk_level=step.risk_level,
                    llm_explanation=step.reason,
                    expected_output=step.expected_output,
                    decision="approved" if approved else "rejected",
                    operator="ui",
                )

    def record_step_auto_approval(self, *, task_id: int, asset_id: int, terminal_context, step, reason: str):
        terminal_session_id = _get_terminal_session_id(terminal_context)
        with Session(engine) as session:
            create_approval(
                session,
                task_id=task_id,
                asset_id=asset_id,
                terminal_session_id=terminal_session_id,
                command=step.command,
                working_directory=step.working_directory,
                risk_level=step.risk_level,
                llm_explanation=step.reason,
                expected_output=step.expected_output,
                decision="approved",
                operator="auto",
                comment=reason,
            )

    def create_command_execution(self, *, task_id: int, step_id: int, asset_id: int, terminal_context, command: str, working_directory: str, started_at: datetime) -> int:
        terminal_session_id = _get_terminal_session_id(terminal_context) or 0
        with Session(engine) as session:
            row = create_command_execution(
                session,
                task_id=task_id,
                step_id=step_id,
                asset_id=asset_id,
                terminal_session_id=terminal_session_id,
                command=command,
                status=TaskStatus.RUNNING.value,
                working_directory=working_directory,
                started_at=started_at,
            )
            return row.id or 0

    def update_command_execution(self, *, command_execution_id: int, status: str, output: str, error_output: str, exit_code: int | None, finished_at: datetime):
        with Session(engine) as session:
            update_command_execution(
                session,
                command_execution_id,
                status=status,
                output=output,
                error_output=error_output,
                exit_code=exit_code,
                finished_at=finished_at,
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


def _dump_terminal_context(terminal_context) -> dict[str, Any]:
    if isinstance(terminal_context, dict):
        return terminal_context
    if hasattr(terminal_context, "model_dump"):
        return terminal_context.model_dump()
    return {
        "terminal_session_id": getattr(terminal_context, "terminal_session_id", 0),
        "selection_label": getattr(terminal_context, "selection_label", ""),
        "selected_text": getattr(terminal_context, "selected_text", ""),
    }


def _get_terminal_session_id(terminal_context) -> int | None:
    if isinstance(terminal_context, dict):
        value = terminal_context.get("terminal_session_id")
        return int(value) if value else None
    return getattr(terminal_context, "terminal_session_id", None) if terminal_context is not None else None


def _build_auto_approval_checker():
    def checker(*, session_id: int, asset_type: str, command: str, risk_level: str) -> dict[str, Any] | None:
        if not session_id:
            return None
        with Session(engine) as session:
            rule, reason = AutoApprovalService().match_rule(
                session,
                session_id,
                asset_type=asset_type,
                asset_tags=[],
                command=command,
                risk_level=risk_level,
            )
        if rule is None:
            return None
        return {"matched": True, "rule_id": rule.id or 0, "reason": reason}

    return checker


def _build_runtime(model_config: ModelConfig) -> AgentRuntime:
    provider = build_llm_provider(model_config)

    def execute_step(step, *, state, emit=None):
        with Session(engine) as session:
            asset = get_asset_record(session, state["asset_id"])
        connector = _build_connector(asset)
        output = _run_connector_command(connector, step.command, emit)
        return {
            "command": step.command,
            "output": output,
            "error": "",
            "status": "completed",
            "exit_code": 0,
            "title": step.title,
        }

    return AgentRuntime(
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
        auto_approval_checker=_build_auto_approval_checker(),
    )


def build_chat_service() -> ChatService:
    model_config = ModelService().load_settings()
    runtime = _build_runtime(model_config)
    return ChatService(
        runtime=runtime,
        session_store=AssistantSessionStore(),
        message_service=AssistantMessageService(lambda: Session(engine)),
        approval_store=ApprovalStore(),
    )


def build_terminal_service() -> TerminalService:
    return TerminalService(
        connector_factory=_build_connector,
        persistence=TerminalPersistence(),
    )


_chat_service: ChatService | None = None
_terminal_service: TerminalService | None = None


def configured_chat_service() -> ChatService:
    global _chat_service
    if _chat_service is None:
        _chat_service = build_chat_service()
    return _chat_service


def configured_terminal_service() -> TerminalService:
    global _terminal_service
    if _terminal_service is None:
        _terminal_service = build_terminal_service()
    return _terminal_service


def configure_api_dependencies() -> None:
    app.dependency_overrides[get_chat_service] = configured_chat_service
    app.dependency_overrides[get_terminal_service] = configured_terminal_service


def main() -> None:
    APP_DIR.mkdir(parents=True, exist_ok=True)
    configure_api_dependencies()

    host = os.environ.get("OPS_AGENT_HOST", "127.0.0.1")
    port = int(os.environ.get("OPS_AGENT_PORT", "8000"))
    import_module("uvicorn").run(app, host=host, port=port)


configure_api_dependencies()


if __name__ == "__main__":
    main()
