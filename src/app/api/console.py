from types import SimpleNamespace
import json

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import StreamingResponse
from sqlmodel import Session

from app.api.assets import to_asset_view
from app.api.groups import to_asset_group_view
from app.api.ssh_keys import to_ssh_key_view
from app.api.schemas import ConsoleApprovalRequest, ConsoleBootstrapView, ConsoleRunRequest, ConsoleSessionRecordView
from app.core.engine.task_orchestrator import OrchestratorDependencies, TaskOrchestrator
from app.services.ssh_key_service import list_ssh_key_records
from app.api.terminal import get_terminal_service
from app.db.repositories.models import get_default_model_config, list_model_configs
from app.db.session import get_session
from app.services.asset_service import get_asset_record, list_asset_group_records, list_asset_records
from app.services.executor_service import ExecutorService
from app.services.model_service import ModelService
from app.services.planner_service import PlannerService
from app.services.terminal_service import TerminalService
from app.shared.enums import AssetType

router = APIRouter()


def _sse_event(payload: dict) -> str:
    return f"event: {payload.get('kind', 'message')}\ndata: {json.dumps(payload, ensure_ascii=False)}\n\n"


async def _parse_request_model(request: Request, model_type):
    payload = await request.json()
    if isinstance(payload, str):
        payload = json.loads(payload)
    return model_type.model_validate(payload)


def get_task_orchestrator(terminal_service: TerminalService = Depends(get_terminal_service)) -> TaskOrchestrator:
    return TaskOrchestrator(
        OrchestratorDependencies(
            planner=PlannerService(),
            executor=ExecutorService(),
            model_service=ModelService(),
            terminal_service=terminal_service,
        )
    )


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
            ssh_key_id=None,
        )
    terminal_session_result = {"terminal_session_id": None, "channel": None, "error": ""}
    terminal_session_result = terminal_service.open_session(local_terminal_asset)
    return ConsoleBootstrapView(
        assets=[to_asset_view(asset) for asset in assets],
        groups=[to_asset_group_view(group) for group in list_asset_group_records(session)],
        historyByAsset={},
        modelOptions=model_options,
        terminalSessionId=terminal_session_result.get("terminal_session_id"),
        terminalSessionChannel=terminal_session_result.get("channel"),
        terminalSessionError=terminal_session_result.get("error", ""),
        initialPrompt="",
        terminalOutput="",
        initialEvents=[],
        sshKeys=[to_ssh_key_view(record) for record in list_ssh_key_records(session)],
    )


@router.post("/api/console/run")
async def run_console_agent(
    request: Request,
    session: Session = Depends(get_session),
    orchestrator: TaskOrchestrator = Depends(get_task_orchestrator),
):
    payload = await _parse_request_model(request, ConsoleRunRequest)
    asset_id = payload.asset_id
    if asset_id is None:
        local_terminal_asset = next((asset for asset in list_asset_records(session) if asset.asset_type == AssetType.LOCAL_TERMINAL.value), None)
        asset_id = local_terminal_asset.id if local_terminal_asset is not None and local_terminal_asset.id is not None else 0
    if asset_id is None:
        raise HTTPException(status_code=400, detail="Asset id is required")
    try:
        stream = orchestrator.stream_run(session=session, prompt=payload.prompt, asset_id=asset_id, model_name=payload.model_name)
        return StreamingResponse((_sse_event(event) for event in stream), media_type="text/event-stream")
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/api/console/approval")
async def approve_console_agent(
    request: Request,
    session: Session = Depends(get_session),
    orchestrator: TaskOrchestrator = Depends(get_task_orchestrator),
):
    payload = await _parse_request_model(request, ConsoleApprovalRequest)
    try:
        stream = orchestrator.stream_approve(session=session, run_id=payload.run_id, approved=payload.approved)
        return StreamingResponse((_sse_event(event) for event in stream), media_type="text/event-stream")
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
