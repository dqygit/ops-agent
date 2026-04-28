from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session

from app.api_routes.dependencies import get_chat_service
from app.api_routes.schemas import AssistantMessageView, ChatApprovalRequest, ChatRunRequest, ChatRunResponse, ChatSessionView, PendingApprovalStepView, PendingApprovalView
from app.db.session import get_session
from app.services.asset_service import get_asset_record
from app.services.assistant_session_service import get_assistant_session_record
from app.services.chat_service import ChatService
from app.services.message_service import AssistantMessageService
from app.shared.enums import AssetType

router = APIRouter()


@router.get("/api/chat/sessions/{session_id}")
def get_chat_session(session_id: int, session: Session = Depends(get_session)) -> ChatSessionView:
    assistant_session = get_assistant_session_record(session, session_id)
    if assistant_session is None:
        raise HTTPException(status_code=404, detail="Chat session not found")
    message_service = AssistantMessageService(lambda: session)
    return ChatSessionView(
        session_id=assistant_session.id or 0,
        asset_id=assistant_session.asset_id,
        model_name=assistant_session.active_model,
        messages=[
            AssistantMessageView(role=message["role"], content=message["content"])
            for message in message_service.list_recent_messages(session_id=session_id)
        ],
    )


@router.get("/api/chat/sessions/{session_id}/pending-approval")
def get_pending_approval(
    session_id: int,
    chat_service: ChatService = Depends(get_chat_service),
) -> PendingApprovalView | None:
    approval = chat_service.get_pending_approval(session_id=session_id)
    if approval is None:
        return None
    return PendingApprovalView(
        task_id=approval.task_id,
        run_id=approval.run_id,
        session_id=approval.session_id,
        status=approval.status,
        message=approval.message,
        latest_decision=approval.latest_decision,
        steps=[
            PendingApprovalStepView(
                title=step.title,
                command=step.command,
                reason=step.reason,
                risk_level=step.risk_level,
            )
            for step in approval.steps
        ],
    )


@router.post("/api/chat/runs")
def create_chat_run(
    payload: ChatRunRequest,
    session: Session = Depends(get_session),
    chat_service: ChatService = Depends(get_chat_service),
) -> ChatRunResponse:
    asset = get_asset_record(session, payload.asset_id)
    if asset is None:
        raise HTTPException(status_code=404, detail="Asset not found")
    result = chat_service.start_agent_run(
        conversation_id=payload.conversation_id,
        user_message=payload.user_message,
        asset=asset,
        asset_type=AssetType(asset.asset_type),
        model_name=payload.model_name,
        terminal_context=payload.terminal_context,
        recent_messages=payload.recent_messages,
    )
    return ChatRunResponse(
        run_id=result.get("run_id", ""),
        session_id=result.get("session_id", 0),
        ui_events=result.get("ui_events", []),
    )


@router.post("/api/chat/runs/{run_id}/approval")
def approve_chat_run(
    run_id: str,
    payload: ChatApprovalRequest,
    chat_service: ChatService = Depends(get_chat_service),
) -> ChatRunResponse:
    result = chat_service.resume_pending_approval(run_id=run_id, approved=payload.approved)
    return ChatRunResponse(
        run_id=result.get("run_id", run_id),
        session_id=result.get("session_id", 0),
        ui_events=result.get("ui_events", []),
    )
