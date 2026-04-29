from types import SimpleNamespace

from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session

from app.api.assets import to_asset_view
from app.api.dependencies import get_chat_service
from app.api.groups import to_asset_group_view
from app.api.schemas import ConsoleApprovalRequest, ConsoleBootstrapView, ConsoleRunRequest, ConsoleSessionRecordView
from app.api.terminal import get_terminal_service
from app.db.repositories import get_default_model_config, list_model_configs
from app.db.session import get_session
from app.services.asset_service import get_asset_record, list_asset_group_records, list_asset_records
from app.services.assistant_session_service import list_assistant_session_records
from app.services.chat_service import ChatService
from app.services.model_service import ModelService
from app.services.terminal_service import TerminalService
from app.shared.enums import AssetType

router = APIRouter()


def to_event_items(ui_events: list[dict]) -> list[dict]:
    items: list[dict] = []
    for index, event in enumerate(ui_events):
        event_type = event.get("type", "")
        payload = event.get("payload", {})
        item_id = f"api-{index}"
        if event_type == "assistant_status":
            items.append({"id": item_id, "kind": "status", "text": str(payload.get("value", ""))})
        elif event_type == "plan_ready":
            steps = [{"title": step.get("title", ""), "command": step.get("command", "")} for step in payload.get("steps", [])]
            items.append({"id": item_id, "kind": "plan", "steps": steps})
        elif event_type == "approval_requested":
            items.append({"id": item_id, "kind": "approval", "text": str(payload.get("message", "Approve this execution plan?")), "runId": str(event.get("run_id", ""))})
        elif event_type == "auto_approved":
            items.append({"id": item_id, "kind": "status", "text": str(payload.get("reason", "auto approved"))})
        elif event_type == "terminal_output":
            items.append({"id": item_id, "kind": "output", "text": str(payload.get("chunk", ""))})
        elif event_type == "assistant_final":
            items.append({"id": item_id, "kind": "final", "text": str(payload.get("message", ""))})
        elif event_type == "assistant_chunk":
            items.append({"id": item_id, "kind": "final", "text": str(payload.get("chunk", ""))})
        elif event_type == "assistant_error":
            items.append({"id": item_id, "kind": "error", "text": str(payload.get("message", ""))})
    return items


@router.get("/api/console/bootstrap")
def get_console_bootstrap(
    session: Session = Depends(get_session),
    terminal_service: TerminalService = Depends(get_terminal_service),
) -> ConsoleBootstrapView:
    assets = list_asset_records(session)
    model_service = ModelService()
    default_record = get_default_model_config(session)
    default_config = model_service.from_record(default_record) if default_record is not None else model_service.load_settings()
    model_options = [record.model_name for record in list_model_configs(session)] or model_service.list_available_models(default_config.provider, session)
    local_terminal_asset = next((asset for asset in assets if asset.asset_type == AssetType.LOCAL_TERMINAL.value), None)
    if local_terminal_asset is None:
        local_terminal_asset = SimpleNamespace(
            id=0,
            asset_type=AssetType.LOCAL_TERMINAL.value,
            name="本地终端",
            host="localhost",
            port=0,
            username="",
            auth_type="",
            tags=[],
            vendor="",
            description="默认本地终端",
            group_id=None,
        )
    terminal_session_result = {"terminal_session_id": None, "channel": None, "error": ""}
    terminal_session_result = terminal_service.open_session(local_terminal_asset)
    return ConsoleBootstrapView(
        assets=[to_asset_view(asset) for asset in assets],
        groups=[to_asset_group_view(group) for group in list_asset_group_records(session)],
        historyByAsset={
            asset.id or 0: [
                ConsoleSessionRecordView(id=row.id or 0, title=row.title, model=row.active_model)
                for row in list_assistant_session_records(session, asset.id or 0)
            ]
            for asset in assets
        },
        modelOptions=model_options,
        terminalSessionId=terminal_session_result.get("terminal_session_id"),
        terminalSessionChannel=terminal_session_result.get("channel"),
        terminalSessionError=terminal_session_result.get("error", ""),
        initialPrompt="",
        terminalOutput="",
        initialEvents=[],
    )


@router.post("/api/console/run")
def run_console_agent(payload: ConsoleRunRequest, session: Session = Depends(get_session), chat_service: ChatService = Depends(get_chat_service)) -> list[dict]:
    assets = list_asset_records(session)
    asset_id = payload.asset_id or (assets[0].id if assets else None)
    if asset_id is None:
        raise HTTPException(status_code=404, detail="Asset not found")
    asset = get_asset_record(session, asset_id)
    if asset is None:
        raise HTTPException(status_code=404, detail="Asset not found")
    default_record = get_default_model_config(session)
    model_service = ModelService()
    default_model = model_service.from_record(default_record).model_name if default_record is not None else model_service.load_settings().model_name
    result = chat_service.start_agent_run(
        conversation_id=payload.conversation_id,
        user_message=payload.prompt,
        asset=asset,
        asset_type=AssetType(asset.asset_type),
        model_name=payload.model_name or default_model,
        terminal_context=payload.terminal_context,
        recent_messages=[],
    )
    return to_event_items(result.get("ui_events", []))


@router.post("/api/console/approval")
def approve_console_agent(payload: ConsoleApprovalRequest, chat_service: ChatService = Depends(get_chat_service)) -> list[dict]:
    result = chat_service.resume_pending_approval(run_id=payload.run_id, approved=payload.approved)
    return to_event_items(result.get("ui_events", []))
