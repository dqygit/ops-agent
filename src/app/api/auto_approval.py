from fastapi import APIRouter, Depends, HTTPException, Response
from sqlmodel import Session

from app.api.schemas import AutoApprovalMatchRequest, AutoApprovalMatchResponse, AutoApprovalRuleCreate, AutoApprovalRuleUpdate, AutoApprovalRuleView
from app.db.session import get_session
from app.services.assistant_session_service import get_assistant_session_record
from app.services.auto_approval_service import AutoApprovalService, tags_from_text

router = APIRouter()


def to_rule_view(rule) -> AutoApprovalRuleView:
    return AutoApprovalRuleView(
        id=rule.id or 0,
        session_id=rule.session_id,
        name=rule.name,
        asset_type=rule.asset_type,
        asset_tags=tags_from_text(rule.asset_tags),
        command_name=rule.command_name,
        command_pattern=rule.command_pattern,
        max_risk_level=rule.max_risk_level,
        readonly_only=rule.readonly_only,
        max_duration_seconds=rule.max_duration_seconds,
        enabled=rule.enabled,
        created_at=rule.created_at,
        updated_at=rule.updated_at,
    )


@router.get("/api/chat/sessions/{session_id}/auto-approval-rules")
def list_auto_approval_rules(session_id: int, session: Session = Depends(get_session)) -> list[AutoApprovalRuleView]:
    assistant_session = get_assistant_session_record(session, session_id)
    if assistant_session is None:
        raise HTTPException(status_code=404, detail="Chat session not found")
    service = AutoApprovalService()
    return [to_rule_view(rule) for rule in service.list_rules(session, session_id)]


@router.post("/api/chat/sessions/{session_id}/auto-approval-rules", status_code=201)
def create_auto_approval_rule(session_id: int, payload: AutoApprovalRuleCreate, session: Session = Depends(get_session)) -> AutoApprovalRuleView:
    assistant_session = get_assistant_session_record(session, session_id)
    if assistant_session is None:
        raise HTTPException(status_code=404, detail="Chat session not found")
    rule = AutoApprovalService().create_rule(session, session_id, payload)
    return to_rule_view(rule)


@router.put("/api/auto-approval-rules/{rule_id}")
def update_auto_approval_rule(rule_id: int, payload: AutoApprovalRuleUpdate, session: Session = Depends(get_session)) -> AutoApprovalRuleView:
    rule = AutoApprovalService().update_rule(session, rule_id, payload)
    if rule is None:
        raise HTTPException(status_code=404, detail="Auto approval rule not found")
    return to_rule_view(rule)


@router.delete("/api/auto-approval-rules/{rule_id}", status_code=204)
def delete_auto_approval_rule(rule_id: int, session: Session = Depends(get_session)) -> Response:
    deleted = AutoApprovalService().delete_rule(session, rule_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Auto approval rule not found")
    return Response(status_code=204)


@router.post("/api/chat/sessions/{session_id}/auto-approval-rules/match")
def match_auto_approval_rule(session_id: int, payload: AutoApprovalMatchRequest, session: Session = Depends(get_session)) -> AutoApprovalMatchResponse:
    assistant_session = get_assistant_session_record(session, session_id)
    if assistant_session is None:
        raise HTTPException(status_code=404, detail="Chat session not found")
    rule, reason = AutoApprovalService().match_rule(
        session,
        session_id,
        asset_type=payload.asset_type,
        asset_tags=payload.asset_tags,
        command=payload.command,
        risk_level=payload.risk_level,
        estimated_duration_seconds=payload.estimated_duration_seconds,
    )
    return AutoApprovalMatchResponse(matched=rule is not None, rule_id=rule.id if rule is not None else None, reason=reason)
