from __future__ import annotations

import logging
from collections.abc import Iterator
from types import SimpleNamespace
from typing import Any, cast

from sqlmodel import Session

from app.core.connectors.device_profiles import (
    NETWORK_CLI_PROFILE,
    select_device_profile,
    select_execution_profile,
)
from app.core.loop.loop_state import LoopContext, LoopMode
from app.core.loop.runtime_manager import LoopRuntimeManager, new_runtime_id
from app.core.tool.execute_command import ExecuteCommandHandler
from app.core.tool.load_skill import LoadSkillHandler
from app.db.repositories.assets import get_asset
from app.db.repositories.models import get_default_model_config
from app.services.approval_service import get_approval_service
from app.services.context_manager import ContextManager, JsonObject
from app.services.mcp_service import McpService
from app.services.model_service import ModelService
from app.services.skill_service import SkillService
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
        selected_skill_name: str | None = None,
        conversation_id: str = "console",
        mode: LoopMode = "agent",
    ) -> Iterator[dict]:
        return self._app_service.stream_run(
            session=session,
            prompt=prompt,
            asset_id=asset_id,
            terminal_id=terminal_id,
            model_name=model_name,
            selected_skill_name=selected_skill_name,
            conversation_id=conversation_id,
            mode=mode,
            terminal_service=self._terminal_service,
        )

    def stream_approve(self, *, session: Session, runtime_id: str, approved: bool, approval_token: str | None = None, allow_prefix: str | None = None) -> Iterator[dict]:
        return self._app_service.stream_approve(
            session=session,
            runtime_id=runtime_id,
            approved=approved,
            approval_token=approval_token,
            allow_prefix=allow_prefix,
            terminal_service=self._terminal_service,
        )

    def stream_plan_approval(self, *, runtime_id: str) -> Iterator[dict]:
        return self._app_service.stream_plan_approval(
            runtime_id=runtime_id,
            terminal_service=self._terminal_service,
        )

class ConsoleAppService:
    def __init__(
        self,
        *,
        model_service: ModelService | None = None,
        skill_service: SkillService | None = None,
        mcp_service: McpService | None = None,
    ) -> None:
        self._model_service = model_service or ModelService()
        self._skill_service = skill_service or SkillService()
        self._mcp_service = mcp_service or McpService()
        self.runtime_manager = LoopRuntimeManager(
            tools_factory=self._build_tool_handlers,
        )

    def _build_tool_handlers(self, ts: TerminalService) -> list[Any]:
        return [
            LoadSkillHandler(self._skill_service),
            ExecuteCommandHandler(_TerminalSessionAdapter(ts, self.runtime_manager)),
            *self._mcp_service.build_tool_handlers(),
        ]

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
        selected_skill_name: str | None = None,
        conversation_id: str = "console",
        mode: LoopMode = "agent",
        terminal_service: TerminalService,
    ) -> Iterator[dict]:
        asset = self._resolve_asset(session, asset_id)
        model_config = self._resolve_model_config(session, model_name)
        if terminal_id and not terminal_service.session_belongs_to_asset(terminal_id, asset_id):
            logger.warning(
                "Ignoring terminal_id that does not belong to asset: asset_id=%s terminal_id=%s",
                asset_id,
                terminal_id,
            )
            terminal_id = None
        asset_summary = (
            f"asset={getattr(asset, 'name', '')}, type={getattr(asset, 'asset_type', '')}, "
            f"host={getattr(asset, 'host', '')}, user={getattr(asset, 'username', '')}"
        )
        asset_type = str(getattr(asset, "asset_type", "") or "")
        shell_type = self._resolve_shell_type(terminal_service, terminal_id)
        execution_profile = select_execution_profile(asset_type, shell_type)
        device_profile = select_device_profile(asset_type, shell_type)
        os_type = self._infer_os_type(shell_type, execution_profile=execution_profile)
        device_context = self._build_device_context(execution_profile, device_profile)

        context_result = self._prepare_conversation_context(conversation_id, model_config)
        conversation_history = context_result.prepared_messages

        runtime_id = new_runtime_id()
        skill_packages = self._skill_service.list_skills()
        available_skills = [
            {"name": skill.name, "description": skill.description}
            for skill in skill_packages
            if skill.valid
        ]
        loaded_skill_name: str | None = None
        manual_skill_name: str | None = None
        manual_skill_content = ""
        if selected_skill_name:
            manual_skill_name = selected_skill_name.strip() or None
            if manual_skill_name:
                try:
                    loaded_skill = self._skill_service.load_skill(manual_skill_name)
                except ValueError as exc:
                    yield {
                        "id": f"evt-error-{runtime_id}",
                        "kind": "error",
                        "runtimeId": runtime_id,
                        "sequence": -1,
                        "ts": "",
                        "text": str(exc),
                        "recoverable": True,
                    }
                    return
                loaded_skill_name = loaded_skill.name
                manual_skill_name = loaded_skill.name
                manual_skill_content = loaded_skill.body

        context = LoopContext(
            runtime_id=runtime_id,
            conversation_id=conversation_id,
            asset_id=asset_id,
            asset_type=asset_type,
            terminal_id=terminal_id,
            asset_summary=asset_summary,
            shell_type=shell_type,
            os_type=os_type,
            execution_profile=execution_profile,
            device_vendor=device_profile.vendor if device_profile else None,
            device_context=device_context,
            user_prompt=prompt,
            model_config=model_config,
            mode=mode,
            conversation_history=conversation_history,
            available_skills=available_skills,
            loaded_skill_name=loaded_skill_name,
            manual_skill_name=manual_skill_name,
            manual_skill_content=manual_skill_content,
        )

        self.runtime_manager.create_runtime(
            conversation_id=conversation_id,
            asset_id=asset_id,
            terminal_id=terminal_id,
            context=context,
        )

        yield {
            "id": f"evt-context-{runtime_id}",
            "kind": "context_status",
            "runtimeId": runtime_id,
            "contextPercent": context_result.context_percent,
            "contextStatus": context_result.context_status,
            "compactionApplied": context_result.compaction_applied,
            "fitStatus": context_result.fit_status,
            "summaryRevision": context_result.summary_revision,
            "sourceConversationRevision": context_result.source_conversation_revision,
        }

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
        allow_prefix: str | None,
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
            if approved and allow_prefix:
                get_approval_service().add_allow_prefix(allow_prefix)
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

    def update_plan(self, *, runtime_id: str, steps: list[dict]) -> dict:
        return self.runtime_manager.update_plan(runtime_id=runtime_id, steps=steps)

    def stream_plan_approval(self, *, runtime_id: str, terminal_service: TerminalService) -> Iterator[dict]:
        try:
            events = self.runtime_manager.approve_plan(runtime_id=runtime_id, terminal_service=terminal_service)
            for event in events:
                yield event
        except Exception as exc:
            logger.exception("stream_plan_approval failed runtime_id=%s", runtime_id)
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

    def _infer_os_type(self, shell_type: str, *, execution_profile: str = "posix-shell") -> str:
        if execution_profile == NETWORK_CLI_PROFILE:
            if shell_type == "serial":
                return "serial-console"
            return "network-device"
        if shell_type in {"powershell", "cmd"}:
            return "Windows"
        if shell_type == "posix":
            return "Darwin/Linux"
        return "unknown"

    def _build_device_context(self, execution_profile: str, device_profile) -> str:
        if execution_profile != NETWORK_CLI_PROFILE or device_profile is None:
            return ""

        base_rules = [
            "You are operating a network device CLI, not a Linux shell.",
            "Do not use Linux commands.",
            f"Use the current device vendor syntax: {device_profile.vendor}.",
            "Prefer read-only inspection commands before changes.",
            "Treat prompts, pagination, configuration modes, and confirmations as protocol state.",
            "Never save configuration unless the user explicitly approves a save action.",
            "If command output contains an error pattern or an unexpected confirmation prompt, stop and explain.",
        ]
        if device_profile.vendor == "generic":
            base_rules.append(
                "This is a generic network device profile. First use '?' to inspect available commands, then choose vendor-specific read-only commands from that output before entering configuration mode."
            )
        else:
            base_rules.append(
                f"Read-only prefixes: {', '.join(device_profile.read_prefixes)}. Save commands requiring separate approval: {', '.join(device_profile.save_commands)}."
            )
        return "\n".join(base_rules)

    def _prepare_conversation_context(self, conversation_id: str, model_config):
        context_manager = self._context_manager()
        if not conversation_id or conversation_id == "console":
            return context_manager.prepare_context(conversation_id or "console", [], model_config)

        from app.api.conversations import get_conversation_service
        service = get_conversation_service()
        try:
            detail = service.get_conversation(conversation_id)
        except FileNotFoundError:
            logger.warning("Conversation not found while preparing context conversation_id=%s", conversation_id)
            return context_manager.prepare_context(conversation_id, [], model_config)

        events = cast(list[JsonObject], detail.events or [])
        result = context_manager.prepare_context(conversation_id, events, model_config)
        logger.info(
            "Prepared conversation context: %d messages from %d events, %d%%, fit=%s",
            len(result.prepared_messages),
            len(events),
            result.context_percent,
            result.fit_status,
        )
        return result

    def _context_manager(self) -> ContextManager:
        from app.api.conversations import get_conversation_service
        service = get_conversation_service()
        return ContextManager(service.base_dir / "context")
