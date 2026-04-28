from fastapi import APIRouter, Depends, HTTPException, Response
from sqlmodel import Session

from app.api_routes.schemas import AssetView, AssistantSessionView
from app.db.session import get_session
from app.services.asset_service import create_asset_record, delete_asset_record, get_asset_record, list_asset_records, update_asset_record
from app.services.assistant_session_service import list_assistant_session_records
from app.shared.schemas import AssetCreate

router = APIRouter()


def to_asset_view(asset) -> AssetView:
    return AssetView(
        id=asset.id or 0,
        name=asset.name,
        asset_type=asset.asset_type,
        host=asset.host,
        port=asset.port,
        username=asset.username,
        auth_type=asset.auth_type,
        tags=asset.tags.split(",") if asset.tags else [],
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


@router.get("/api/assets/{asset_id}/sessions")
def list_asset_sessions(asset_id: int, session: Session = Depends(get_session)) -> list[AssistantSessionView]:
    asset = get_asset_record(session, asset_id)
    if asset is None:
        raise HTTPException(status_code=404, detail="Asset not found")
    return [
        AssistantSessionView(
            id=assistant_session.id or 0,
            asset_id=assistant_session.asset_id,
            title=assistant_session.title,
            active_model=assistant_session.active_model,
        )
        for assistant_session in list_assistant_session_records(session, asset_id)
    ]


@router.post("/api/assets", status_code=201)
def create_asset(payload: AssetCreate, session: Session = Depends(get_session)) -> AssetView:
    asset = create_asset_record(session, payload)
    return to_asset_view(asset)


@router.put("/api/assets/{asset_id}")
def update_asset(asset_id: int, payload: AssetCreate, session: Session = Depends(get_session)) -> AssetView:
    asset = update_asset_record(session, asset_id, payload)
    if asset is None:
        raise HTTPException(status_code=404, detail="Asset not found")
    return to_asset_view(asset)


@router.delete("/api/assets/{asset_id}", status_code=204)
def delete_asset(asset_id: int, session: Session = Depends(get_session)) -> Response:
    deleted = delete_asset_record(session, asset_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Asset not found")
    return Response(status_code=204)
