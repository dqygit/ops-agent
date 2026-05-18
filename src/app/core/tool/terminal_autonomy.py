from __future__ import annotations

from collections.abc import Iterator
from typing import Any

from app.core.loop.loop_events import LoopEvent
from app.core.loop.loop_state import LoopState
from app.core.loop.message_manager import MessageManager
from app.core.loop.runtime_manager import LoopRuntimeManager
from app.core.tool.handler import ToolDisplayMetadata
from app.core.tool.schema import LLMToolDefinition
from app.db.repositories.assets import get_asset, list_assets
from app.db.session import Session, engine


class ListAssetsHandler:
    @property
    def definition(self) -> LLMToolDefinition:
        return LLMToolDefinition(
            name="list_assets",
            description="List visible diagnostic assets with non-secret connection summaries.",
            input_schema={"type": "object", "properties": {}, "required": []},
        )

    def needs_approval(self, args: dict[str, Any]) -> tuple[str, str]:
        _ = args
        return "allow", "Listing assets only returns non-secret summaries."

    def display_metadata(self, args: dict[str, Any]) -> ToolDisplayMetadata:
        _ = args
        return ToolDisplayMetadata(
            description="List visible diagnostic assets.",
            display_text="List assets",
            extra={"kind": "asset_list"},
        )

    def execute(self, *, state: LoopState, step_id: str, args: dict[str, Any], manager: MessageManager | None = None) -> Iterator[LoopEvent]:
        _ = state, step_id, args
        with Session(engine) as session:
            assets = list_assets(session)
            result = {
                "assets": [
                    {
                        "asset_id": asset.id,
                        "name": asset.name,
                        "asset_type": asset.asset_type,
                        "group_id": asset.group_id,
                        "connection_status": "connectable",
                        "tags": [tag.strip() for tag in asset.tags.split(",") if tag.strip()],
                        "connectable": asset.id is not None,
                    }
                    for asset in assets
                    if asset.id is not None
                ]
            }
        output = str(result)
        if manager:
            yield from manager.update(tool_output=output)
        return True, output


class RequestTerminalSessionHandler:
    def __init__(self, runtime_manager: LoopRuntimeManager) -> None:
        self._runtime_manager = runtime_manager

    @property
    def definition(self) -> LLMToolDefinition:
        return LLMToolDefinition(
            name="request_terminal_session",
            description="Request user approval to open a terminal session for a visible asset.",
            input_schema={
                "type": "object",
                "properties": {
                    "asset_id": {"type": "integer", "description": "Target asset ID."},
                    "reason": {"type": "string", "description": "Why this terminal session is needed."},
                },
                "required": ["asset_id", "reason"],
            },
        )

    def needs_approval(self, args: dict[str, Any]) -> tuple[str, str]:
        _ = args
        return "allow", "Terminal session requests require separate user confirmation."

    def display_metadata(self, args: dict[str, Any]) -> ToolDisplayMetadata:
        asset_id = args.get("asset_id")
        return ToolDisplayMetadata(
            description="Request terminal access for an asset.",
            display_text=f"Request terminal access for asset {asset_id}",
            extra={"kind": "terminal_request"},
        )

    def execute(self, *, state: LoopState, step_id: str, args: dict[str, Any], manager: MessageManager | None = None) -> Iterator[LoopEvent]:
        _ = step_id
        try:
            asset_id = int(args.get("asset_id") or -1)
        except (TypeError, ValueError):
            output = "A valid asset_id is required to request terminal access."
            if manager:
                yield from manager.update(tool_output=output)
            return False, output
        reason = str(args.get("reason") or "").strip()
        if not reason:
            output = "A reason is required to request terminal access."
            if manager:
                yield from manager.update(tool_output=output)
            return False, output
        with Session(engine) as session:
            asset = get_asset(session, asset_id)
            if asset is None or asset.id is None:
                output = "Asset is not visible or does not exist."
                if manager:
                    yield from manager.update(tool_output=output)
                return False, output
            request, _token, _event = self._runtime_manager.create_terminal_request(
                state.context.runtime_id,
                conversation_id=state.context.conversation_id,
                asset_id=asset.id,
                asset_name=asset.name,
                reason=reason,
            )
        output = str(
            {
                "request_id": request.request_id,
                "status": "pending_user_confirmation",
                "asset_id": request.asset_id,
                "asset_name": request.asset_name,
                "reason": request.reason,
            }
        )
        if manager:
            yield from manager.update(tool_output=output)
        return True, output
