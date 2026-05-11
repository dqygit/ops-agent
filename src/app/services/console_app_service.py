from __future__ import annotations

import logging
from collections.abc import Iterator
from types import SimpleNamespace
from typing import Any

from sqlmodel import Session

from app.core.loop.loop_state import LoopContext
from app.core.loop.runtime_manager import LoopRuntimeManager, new_runtime_id
from app.core.tool.execute_command import ExecuteCommandHandler
from app.db.repositories.assets import get_asset
from app.db.repositories.models import get_default_model_config
from app.services.model_service import ModelService
from app.services.terminal_service import TerminalService


logger = logging.getLogger(__name__)


class _TerminalSessionAdapter:
    def __init__(self, terminal_service: TerminalService, runtime_manager: LoopRuntimeManager) -> None:
        self._terminal_service = terminal_service
        self._runtime_manager = runtime_manager

    def get_session(self, terminal_id: str) -> Any | None:
        return self._terminal_service.get_session(terminal_id)

    def acquire_terminal_slot(self, runtime_id: str, terminal_id: str) -> bool:
        return self._runtime_manager.acquire_terminal_slot(runtime_id, terminal_id)

    def release_terminal_slot(self, runtime_id: str, terminal_id: str) -> None:
        self._runtime_manager.release_terminal_slot(runtime_id, terminal_id)


class TaskOrchestrator:
    def __init__(self, app_service: "ConsoleAppService", terminal_service: TerminalService) -> None:
        self._app_service = app_service
        self._terminal_service = terminal_service

    def stream_run(
        self,
        *,
        session: Session,
        prompt: str,
        asset_id: int,
        terminal_id: str | None = None,
        model_name: str | None = None,
        conversation_id: str = "console",
        mode: str = "agent",
    ) -> Iterator[dict]:
        return self._app_service.stream_run(
            session=session,
            prompt=prompt,
            asset_id=asset_id,
            terminal_id=terminal_id,
            model_name=model_name,
            conversation_id=conversation_id,
            mode=mode,
            terminal_service=self._terminal_service,
        )

    def stream_approve(self, *, session: Session, runtime_id: str, approved: bool, approval_token: str | None = None) -> Iterator[dict]:
        return self._app_service.stream_approve(
            session=session,
            runtime_id=runtime_id,
            approved=approved,
            approval_token=approval_token,
            terminal_service=self._terminal_service,
        )


class ConsoleAppService:
    def __init__(
        self,
        *,
        model_service: ModelService | None = None,
    ) -> None:
        self._model_service = model_service or ModelService()
        self.runtime_manager = LoopRuntimeManager(
            tools_factory=lambda ts: [ExecuteCommandHandler(_TerminalSessionAdapter(ts, self.runtime_manager))]
        )

    def build_orchestrator(self, terminal_service: TerminalService) -> TaskOrchestrator:
        return TaskOrchestrator(self, terminal_service)

    def stream_run(
        self,
        *,
        session: Session,
        prompt: str,
        asset_id: int,
        terminal_id: str | None = None,
        model_name: str | None = None,
        conversation_id: str = "console",
        mode: str = "agent",
        terminal_service: TerminalService,
    ) -> Iterator[dict]:
        asset = self._resolve_asset(session, asset_id)
        model_config = self._resolve_model_config(session, model_name)
        asset_summary = (
            f"asset={getattr(asset, 'name', '')}, type={getattr(asset, 'asset_type', '')}, "
            f"host={getattr(asset, 'host', '')}, user={getattr(asset, 'username', '')}"
        )
        shell_type = self._resolve_shell_type(terminal_service, terminal_id)
        os_type = self._infer_os_type(shell_type)

        runtime_id = new_runtime_id()
        context = LoopContext(
            runtime_id=runtime_id,
            conversation_id=conversation_id,
            asset_id=asset_id,
            terminal_id=terminal_id,
            asset_summary=asset_summary,
            shell_type=shell_type,
            os_type=os_type,
            user_prompt=prompt,
            model_config=model_config,
            mode=mode, # type: ignore
        )
        
        self.runtime_manager.create_runtime(
            conversation_id=conversation_id,
            asset_id=asset_id,
            terminal_id=terminal_id,
            context=context,
        )

        try:
            events = self.runtime_manager.run(runtime_id=runtime_id, terminal_service=terminal_service)
            for event in events:
                yield event
        except Exception as exc:
            logger.exception("stream_run failed conversation_id=%s runtime_id=%s", conversation_id, runtime_id)
            yield {
                "id": f"evt-error-{runtime_id}",
                "kind": "error",
                "runtimeId": runtime_id,
                "sequence": -1,
                "ts": "",
                "text": str(exc),
                "recoverable": True,
            }

    def stream_approve(
        self,
        *,
        session: Session,
        runtime_id: str,
        approved: bool,
        approval_token: str | None,
        terminal_service: TerminalService,
    ) -> Iterator[dict]:
        _ = session
        runtime = self.runtime_manager.get_runtime(runtime_id)
        if runtime is None:
            yield {
                "id": f"evt-error-{runtime_id}",
                "kind": "error",
                "runtimeId": runtime_id,
                "sequence": -1,
                "ts": "",
                "text": "Runtime not found.",
                "recoverable": False,
            }
            return

        try:
            events = self.runtime_manager.resume(
                runtime_id=runtime_id,
                approved=approved,
                approval_token=approval_token,
                terminal_service=terminal_service,
            )
            for event in events:
                yield event
        except Exception as exc:
            logger.exception("stream_approve failed runtime_id=%s", runtime_id)
            yield {
                "id": f"evt-error-{runtime_id}",
                "kind": "error",
                "runtimeId": runtime_id,
                "sequence": -1,
                "ts": "",
                "text": str(exc),
                "recoverable": True,
            }

    def _resolve_asset(self, session: Session, asset_id: int):
        asset = get_asset(session, asset_id)
        if asset is None and asset_id == 0:
            asset = SimpleNamespace(
                id=0,
                name="本地终端",
                asset_type="local_terminal",
                host="localhost",
                username="",
            )
        return asset

    def _resolve_model_config(self, session: Session, model_name: str | None):
        default_record = get_default_model_config(session)
        default_config = (
            self._model_service.from_record(default_record)
            if default_record is not None
            else self._model_service.load_settings()
        )
        if model_name and model_name != default_config.model_name:
            default_config = default_config.model_copy(update={"model_name": model_name})
        return default_config

    def _resolve_shell_type(self, terminal_service: TerminalService, terminal_id: str | None) -> str:
        shell_type = "unknown"
        if terminal_id:
            try:
                shell_type = terminal_service.get_shell_kind(terminal_id)
            except ValueError:
                shell_type = "unknown"
        return shell_type

    def _infer_os_type(self, shell_type: str) -> str:
        if shell_type in {"powershell", "cmd"}:
            return "Windows"
        if shell_type in {"posix", "network", "serial"}:
            return "Darwin/Linux"
        return "unknown"
