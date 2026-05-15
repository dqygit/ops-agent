from types import SimpleNamespace
import json
import logging

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import StreamingResponse
from sqlmodel import Session

from app.api.assets import to_asset_view
from app.api.conversations import get_conversation_service
from app.api.groups import to_asset_group_view
from app.api.ssh_keys import to_ssh_key_view
from app.api.schemas import ConsoleApprovalRequest, ConsoleBootstrapView, ConsolePlanUpdateRequest, ConsoleRunRequest, RuntimeEventsResponse, RuntimeSnapshotView, RuntimeSummaryView
from app.services.ssh_key_service import list_ssh_key_records
from app.api.terminal import get_terminal_service
from app.db.repositories.models import get_default_model_config, list_model_configs
from app.db.session import get_session
from app.services.asset_service import list_asset_group_records, list_asset_records

from app.services.model_service import ModelService
from app.services.terminal_service import TerminalService
from app.services.console_app_service import ConsoleAppService, TaskOrchestrator
from app.shared.enums import AssetType

router = APIRouter()
_console_app_service = ConsoleAppService()
logger = logging.getLogger(__name__)


def _sse_event(payload: dict) -> str:
    return f"event: {payload.get('kind', 'message')}\ndata: {json.dumps(payload, ensure_ascii=False)}\n\n"


async def _parse_request_model(request: Request, model_type):
    payload = await request.json()
    if isinstance(payload, str):
        payload = json.loads(payload)
    return model_type.model_validate(payload)


def get_task_orchestrator(terminal_service: TerminalService = Depends(get_terminal_service)) -> TaskOrchestrator:
    return _console_app_service.build_orchestrator(terminal_service)


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
    if default_config.model_name and default_config.model_name not in model_options:
        model_options = [default_config.model_name, *model_options]
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
    terminal_session_result = terminal_service.open_session(local_terminal_asset, reuse_existing=True)
    terminal_session_id = terminal_session_result.get("terminal_id")
    terminal_output = ""
    if terminal_session_id:
        terminal_output = terminal_service.read_buffered_output(terminal_session_id)

    return ConsoleBootstrapView(
        assets=[to_asset_view(asset) for asset in assets],
        groups=[to_asset_group_view(group) for group in list_asset_group_records(session)],
        historyByAsset={},
        modelOptions=model_options,
        terminalSessionId=terminal_session_id,
        terminalSessionChannel=terminal_session_result.get("channel"),
        terminalSessionError=terminal_session_result.get("error", ""),
        initialPrompt="",
        terminalOutput=terminal_output,
        initialEvents=[],
        sshKeys=[to_ssh_key_view(record) for record in list_ssh_key_records(session)],
    )


@router.post("/api/console/run")
async def run_console_agent(
    request: Request,
    session: Session = Depends(get_session),
    orchestrator: TaskOrchestrator = Depends(get_task_orchestrator),
):
    import time as _time
    t_start = _time.monotonic()
    payload = await _parse_request_model(request, ConsoleRunRequest)
    t_parse = _time.monotonic()
    if payload.conversation_id and payload.conversation_id != "console":
        conversation_service = get_conversation_service()
        user_event = {
            "id": f"user-{payload.conversation_id}-{abs(hash(payload.prompt))}",
            "kind": "user",
            "text": payload.prompt,
        }
        try:
            conversation_service.append_events(payload.conversation_id, [user_event])
        except FileNotFoundError as exc:
            raise HTTPException(status_code=404, detail="Conversation not found") from exc
    t_persist = _time.monotonic()
    asset_id = payload.asset_id
    if asset_id is None:
        local_terminal_asset = next((asset for asset in list_asset_records(session) if asset.asset_type == AssetType.LOCAL_TERMINAL.value), None)
        asset_id = local_terminal_asset.id if local_terminal_asset is not None and local_terminal_asset.id is not None else 0
    if asset_id is None:
        raise HTTPException(status_code=400, detail="Asset id is required")
    
    stream = orchestrator.stream_run(
        session=session,
        prompt=payload.prompt,
        asset_id=asset_id,
        terminal_id=payload.terminal_id,
        model_name=payload.model_name,
        selected_skill_name=payload.selected_skill_name,
        conversation_id=payload.conversation_id,
        mode=payload.mode,
    )

    def event_stream():
        t_first_event = None
        try:
            for event in stream:
                if t_first_event is None:
                    t_first_event = _time.monotonic()
                yield _sse_event(event)
        except Exception as exc:
            logger.exception("console.run stream failed conversation_id=%s", payload.conversation_id)
            yield _sse_event({"id": "error-run", "kind": "error", "text": str(exc), "recoverable": True})

    return StreamingResponse(event_stream(), media_type="text/event-stream")


@router.get("/api/console/conversations/{conversation_id}/runtimes")
def list_conversation_runtimes(conversation_id: str) -> list[RuntimeSummaryView]:
    runtimes = _console_app_service.runtime_manager.list_runtimes(conversation_id)
    summaries: list[RuntimeSummaryView] = []
    for runtime in runtimes:
        current_step = runtime.state.get_current_step()
        summaries.append(
            RuntimeSummaryView(
                runtime_id=runtime.runtime_id,
                conversation_id=runtime.conversation_id,
                asset_id=runtime.asset_id,
                terminal_id=runtime.terminal_id,
                status=runtime.state.phase,
                loaded_skill_name=runtime.state.context.loaded_skill_name,
                mode=runtime.state.context.mode,
                plan_version=runtime.state.plan_version,
                locked_plan=runtime.state.locked_plan,
                current_step_id=current_step.step_id if current_step else None,
                pending_approval_step_id=runtime.state.pending_approval_step_id,
                updated_at=runtime.updated_at,
            )
        )
    return summaries


@router.get("/api/console/runtimes/{runtime_id}/snapshot")
def get_runtime_snapshot(runtime_id: str) -> RuntimeSnapshotView:
    snapshot = _console_app_service.runtime_manager.get_snapshot(runtime_id)
    return RuntimeSnapshotView.model_validate(snapshot, from_attributes=True)


@router.get("/api/console/runtimes/{runtime_id}/events")
def get_runtime_events(runtime_id: str, since: int = 0) -> RuntimeEventsResponse:
    latest_sequence, events = _console_app_service.runtime_manager.events_since(runtime_id, since)
    return RuntimeEventsResponse(latest_sequence=latest_sequence, events=[dict(event) for event in events])


@router.put("/api/console/runtimes/{runtime_id}/plan")
async def update_runtime_plan(runtime_id: str, request: Request):
    payload = await _parse_request_model(request, ConsolePlanUpdateRequest)
    try:
        return _console_app_service.update_plan(
            runtime_id=runtime_id,
            steps=[step.model_dump() for step in payload.steps],
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/api/console/runtimes/{runtime_id}/plan/approve")
def approve_runtime_plan(
    runtime_id: str,
    orchestrator: TaskOrchestrator = Depends(get_task_orchestrator),
):
    stream = orchestrator.stream_plan_approval(runtime_id=runtime_id)

    def event_stream():
        try:
            for event in stream:
                yield _sse_event(event)
        except Exception as exc:
            yield _sse_event({"id": "error-plan-approve", "kind": "error", "text": str(exc), "recoverable": True})

    return StreamingResponse(event_stream(), media_type="text/event-stream")


@router.post("/api/console/approval")
async def approve_console_agent(
    request: Request,
    session: Session = Depends(get_session),
    orchestrator: TaskOrchestrator = Depends(get_task_orchestrator),
):
    payload = await _parse_request_model(request, ConsoleApprovalRequest)
    stream = orchestrator.stream_approve(
        session=session,
        runtime_id=payload.runtime_id,
        approved=payload.approved,
        approval_token=payload.approval_token,
        allow_prefix=payload.allow_prefix,
    )

    def event_stream():
        try:
            for event in stream:
                yield _sse_event(event)
        except Exception as exc:
            yield _sse_event({"id": "error-approve", "kind": "error", "text": str(exc), "recoverable": True})

    return StreamingResponse(event_stream(), media_type="text/event-stream")
