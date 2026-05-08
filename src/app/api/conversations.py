import os
from pathlib import Path

from fastapi import APIRouter, HTTPException, Response, status

from app.api.schemas import (
    ConversationAppendEventsRequest,
    ConversationCreateRequest,
    ConversationCreateResponse,
    ConversationDetailView,
    ConversationSummaryView,
)
from app.services.conversation_service import ConversationService
from app.services.model_service import ModelService

router = APIRouter()


def get_conversation_service() -> ConversationService:
    configured = os.getenv("OPS_AGENT_CONVERSATIONS_DIR", "")
    base_dir = Path(configured) if configured else Path.cwd() / ".ops-agent" / "conversations"
    return ConversationService(base_dir=base_dir, model_service=ModelService())


@router.get("/api/conversations", response_model=list[ConversationSummaryView])
def list_conversations() -> list[ConversationSummaryView]:
    service = get_conversation_service()
    return [ConversationSummaryView.model_validate(summary.__dict__) for summary in service.list_conversations()]


@router.post("/api/conversations", response_model=ConversationCreateResponse)
def create_conversation(payload: ConversationCreateRequest) -> ConversationCreateResponse:
    service = get_conversation_service()
    summary = service.create_conversation(selected_model=payload.selected_model)
    return ConversationCreateResponse(
        conversation=ConversationSummaryView.model_validate(summary.__dict__),
        events=[],
    )


@router.get("/api/conversations/{conversation_id}", response_model=ConversationDetailView)
def get_conversation(conversation_id: str) -> ConversationDetailView:
    service = get_conversation_service()
    try:
        detail = service.get_conversation(conversation_id)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail="Conversation not found") from exc
    return ConversationDetailView.model_validate(detail.__dict__)


@router.post("/api/conversations/{conversation_id}/events", response_model=ConversationDetailView)
def append_conversation_events(conversation_id: str, payload: ConversationAppendEventsRequest) -> ConversationDetailView:
    service = get_conversation_service()
    try:
        detail = service.append_events(conversation_id, payload.events)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail="Conversation not found") from exc
    return ConversationDetailView.model_validate(detail.__dict__)


@router.delete("/api/conversations/{conversation_id}", status_code=status.HTTP_204_NO_CONTENT, response_class=Response)
def delete_conversation(conversation_id: str) -> Response:
    service = get_conversation_service()
    try:
        service.delete_conversation(conversation_id)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail="Conversation not found") from exc
    return Response(status_code=status.HTTP_204_NO_CONTENT)
