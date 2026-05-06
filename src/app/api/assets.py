from fastapi import APIRouter, Depends, HTTPException, Response
from sqlmodel import Session

from app.api.schemas import AssetContextView, AssetView, AssistantSessionView, TerminalEventSummaryView, TerminalSessionSummaryView
from app.db.repositories.terminal import list_terminal_events_by_session_id, list_terminal_sessions_by_asset_id
from app.db.session import get_session
from app.services.asset_service import GroupNotFoundError, create_asset_record, delete_asset_record, get_asset_record, list_asset_records, update_asset_record
from app.shared.schemas import AssetCreate

router = APIRouter()


def to_asset_view(asset) -> AssetView:
    return AssetView(
        id=asset.id or 0,
        group_id=asset.group_id,
        name=asset.name,
        asset_type=asset.asset_type,
        host=asset.host,
        port=asset.port,
        username=asset.username,
        auth_type=asset.auth_type,
        tags=asset.tags.split(",") if asset.tags else [],
        vendor=asset.vendor,
        description=asset.description,
    )


@router.get("/api/assets")
def list_assets(session: Session = Depends(get_session)) -> list[AssetView]:
    return [to_asset_view(asset) for asset in list_asset_records(session)]


@router.get("/api/assets/{asset_id}")
def get_asset(asset_id: int, session: Session = Depends(get_session)) -> AssetView:
    asset = get_asset_record(session, asset_id)
    if asset is None:
        raise HTTPException(status_code=404, detail="Asset not found")
    return to_asset_view(asset)


@router.post("/api/assets", status_code=201)
def create_asset(payload: AssetCreate, session: Session = Depends(get_session)) -> AssetView:
    try:
        asset = create_asset_record(session, payload)
    except GroupNotFoundError as exc:
        raise HTTPException(status_code=404, detail="Group not found") from exc
    return to_asset_view(asset)


@router.put("/api/assets/{asset_id}")
def update_asset(asset_id: int, payload: AssetCreate, session: Session = Depends(get_session)) -> AssetView:
    try:
        asset = update_asset_record(session, asset_id, payload)
    except GroupNotFoundError as exc:
        raise HTTPException(status_code=404, detail="Group not found") from exc
    if asset is None:
        raise HTTPException(status_code=404, detail="Asset not found")
    return to_asset_view(asset)


@router.delete("/api/assets/{asset_id}", status_code=204)
def delete_asset(asset_id: int, session: Session = Depends(get_session)) -> Response:
    deleted = delete_asset_record(session, asset_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Asset not found")
    return Response(status_code=204)
