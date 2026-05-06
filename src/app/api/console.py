from types import SimpleNamespace

from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session

from app.api.assets import to_asset_view
from app.api.groups import to_asset_group_view
from app.api.ssh_keys import to_ssh_key_view
from app.api.schemas import ConsoleApprovalRequest, ConsoleBootstrapView, ConsoleRunRequest, ConsoleSessionRecordView
from app.services.ssh_key_service import list_ssh_key_records
from app.api.terminal import get_terminal_service
from app.db.repositories.models import get_default_model_config, list_model_configs
from app.db.session import get_session
from app.services.asset_service import get_asset_record, list_asset_group_records, list_asset_records
from app.services.model_service import ModelService
from app.services.terminal_service import TerminalService
from app.shared.enums import AssetType

router = APIRouter()


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
