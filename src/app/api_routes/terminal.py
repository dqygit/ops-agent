from fastapi import APIRouter, Depends, HTTPException, Response
from pydantic import BaseModel
from sqlmodel import Session

from app.db.session import get_session
from app.services.asset_service import get_asset_record
from app.services.terminal_service import TerminalService

router = APIRouter()


class TerminalSessionRequest(BaseModel):
    asset_id: int


class TerminalSessionResponse(BaseModel):
    terminal_session_id: int | None
    channel: str | None
    error: str


class TerminalContextRequest(BaseModel):
    selection_label: str
    selected_text: str


class TerminalContextResponse(BaseModel):
    terminal_session_id: int
    selection_label: str
    selected_text: str


def get_terminal_service() -> TerminalService:
    raise NotImplementedError("Terminal service dependency is not configured yet")


@router.post("/api/terminal/sessions")
def open_terminal_session(
    payload: TerminalSessionRequest,
    session: Session = Depends(get_session),
    terminal_service: TerminalService = Depends(get_terminal_service),
) -> TerminalSessionResponse:
    asset = get_asset_record(session, payload.asset_id)
    if asset is None:
        raise HTTPException(status_code=404, detail="Asset not found")
    result = terminal_service.open_session(asset)
    return TerminalSessionResponse(
        terminal_session_id=result.get("terminal_session_id"),
        channel=result.get("channel"),
        error=result.get("error", ""),
    )


@router.post("/api/terminal/sessions/{terminal_session_id}/context")
def attach_terminal_context(
    terminal_session_id: int,
    payload: TerminalContextRequest,
    terminal_service: TerminalService = Depends(get_terminal_service),
) -> TerminalContextResponse:
    attachment = terminal_service.attach_context(
        terminal_session_id,
        payload.selection_label,
        payload.selected_text,
    )
    return TerminalContextResponse(
        terminal_session_id=attachment.terminal_session_id,
        selection_label=attachment.selection_label,
        selected_text=attachment.selected_text,
    )


@router.delete("/api/terminal/sessions/{terminal_session_id}", status_code=204)
def close_terminal_session(
    terminal_session_id: int,
    terminal_service: TerminalService = Depends(get_terminal_service),
) -> Response:
    closed = terminal_service.close_session(terminal_session_id)
    if not closed:
        raise HTTPException(status_code=404, detail="Terminal session not found")
    return Response(status_code=204)
