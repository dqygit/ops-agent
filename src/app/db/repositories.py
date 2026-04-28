import json
from datetime import UTC, datetime
from typing import Any, cast

from sqlalchemy import desc
from sqlmodel import Session, select

from app.db.models import Approval, AgentTask, AssistantMessage, AssistantSession, Asset, Credential, ModelUsage, TaskStep, TerminalEvent, TerminalSession
from app.shared.enums import TaskStatus
from app.shared.schemas import AssetCreate, PlanStep


def create_asset(session: Session, data: AssetCreate) -> Asset:
    payload = data.model_dump(exclude={"credential_secret"})
    payload["asset_type"] = data.asset_type.value
    payload["tags"] = ",".join(data.tags)
    asset = Asset(**payload)
    session.add(asset)
    session.commit()
    session.refresh(asset)
    return asset


def list_assets(session: Session) -> list[Asset]:
    return list(session.exec(select(Asset).order_by(desc(cast(Any, Asset.id)))).all())


def get_credential_by_asset_id(session: Session, asset_id: int) -> Credential | None:
    return session.exec(select(Credential).where(Credential.asset_id == asset_id)).first()


def create_credential(
    session: Session,
    *,
    asset_id: int,
    encryption_version: str,
    encrypted_blob: str,
) -> Credential:
    row = Credential(
        asset_id=asset_id,
        encryption_version=encryption_version,
        encrypted_blob=encrypted_blob,
    )
    session.add(row)
    session.commit()
    session.refresh(row)
    return row


def update_credential(
    session: Session,
    asset_id: int,
    *,
    encryption_version: str,
    encrypted_blob: str,
) -> Credential | None:
    row = get_credential_by_asset_id(session, asset_id)
    if row is None:
        return None
    row.encryption_version = encryption_version
    row.encrypted_blob = encrypted_blob
    row.updated_at = datetime.now(UTC)
    session.add(row)
    session.commit()
    session.refresh(row)
    return row


def get_or_create_assistant_session(session: Session, asset_id: int, title: str, active_model: str) -> AssistantSession:
    row = session.exec(
        select(AssistantSession)
        .where(AssistantSession.asset_id == asset_id)
        .where(AssistantSession.title == title)
        .order_by(desc(cast(Any, AssistantSession.id)))
    ).first()
    if row is not None:
        row.active_model = active_model
        row.updated_at = datetime.now(UTC)
        session.add(row)
        session.commit()
        session.refresh(row)
        return row
    row = AssistantSession(asset_id=asset_id, title=title, active_model=active_model)
    session.add(row)
    session.commit()
    session.refresh(row)
    return row


def list_assistant_sessions_by_asset_id(session: Session, asset_id: int) -> list[AssistantSession]:
    return list(
        session.exec(
            select(AssistantSession)
            .where(AssistantSession.asset_id == asset_id)
            .order_by(desc(cast(Any, AssistantSession.updated_at)), desc(cast(Any, AssistantSession.id)))
        ).all()
    )


def get_assistant_session(session: Session, session_id: int) -> AssistantSession | None:
    return session.get(AssistantSession, session_id)


def create_assistant_message(session: Session, *, session_id: int, role: str, content: str) -> AssistantMessage:
    row = AssistantMessage(session_id=session_id, role=role, content=content)
    session.add(row)
    session.commit()
    session.refresh(row)
    return row


def list_assistant_messages(session: Session, session_id: int) -> list[AssistantMessage]:
    return list(
        session.exec(
            select(AssistantMessage)
            .where(AssistantMessage.session_id == session_id)
            .order_by(cast(Any, AssistantMessage.id))
        ).all()
    )


def create_agent_task(
    session: Session,
    *,
    session_id: int,
    run_id: str,
    asset_id: int,
    user_input: str,
    attached_terminal_context: str,
    task_type: str,
    risk_level: str,
    status: str,
) -> AgentTask:
    row = AgentTask(
        session_id=session_id,
        run_id=run_id,
        asset_id=asset_id,
        user_input=user_input,
        attached_terminal_context=attached_terminal_context,
        task_type=task_type,
        risk_level=risk_level,
        status=status,
    )
    session.add(row)
    session.commit()
    session.refresh(row)
    return row


def get_agent_task_by_run_id(session: Session, run_id: str) -> AgentTask | None:
    return session.exec(select(AgentTask).where(AgentTask.run_id == run_id)).first()


def update_agent_task(
    session: Session,
    task_id: int,
    *,
    status: str | None = None,
    final_summary: str | None = None,
) -> AgentTask | None:
    row = session.get(AgentTask, task_id)
    if row is None:
        return None
    if status is not None:
        row.status = status
    if final_summary is not None:
        row.final_summary = final_summary
    row.updated_at = datetime.now(UTC)
    session.add(row)
    session.commit()
    session.refresh(row)
    return row


def create_task_steps(session: Session, task_id: int, steps: list[PlanStep]) -> list[TaskStep]:
    rows = [
        TaskStep(
            task_id=task_id,
            step_order=index,
            title=step.title,
            command=step.command,
            reason=step.reason,
            risk_level=step.risk_level,
        )
        for index, step in enumerate(steps)
    ]
    for row in rows:
        session.add(row)
    session.commit()
    for row in rows:
        session.refresh(row)
    return rows


def update_task_step(
    session: Session,
    step_id: int,
    *,
    status: str | None = None,
    output: str | None = None,
    error_message: str | None = None,
    started_at: datetime | None = None,
    finished_at: datetime | None = None,
) -> TaskStep | None:
    row = session.get(TaskStep, step_id)
    if row is None:
        return None
    if status is not None:
        row.status = status
    if output is not None:
        row.output = output
    if error_message is not None:
        row.error_message = error_message
    if started_at is not None:
        row.started_at = started_at
    if finished_at is not None:
        row.finished_at = finished_at
    session.add(row)
    session.commit()
    session.refresh(row)
    return row


def create_approval(session: Session, *, task_id: int, decision: str, operator: str, comment: str = "") -> Approval:
    row = Approval(task_id=task_id, decision=decision, operator=operator, comment=comment)
    session.add(row)
    session.commit()
    session.refresh(row)
    return row


def get_latest_approval_by_task_id(session: Session, task_id: int) -> Approval | None:
    return session.exec(
        select(Approval)
        .where(Approval.task_id == task_id)
        .order_by(desc(cast(Any, Approval.created_at)), desc(cast(Any, Approval.id)))
    ).first()


def list_task_steps_by_task_id(session: Session, task_id: int) -> list[TaskStep]:
    return list(
        session.exec(
            select(TaskStep)
            .where(TaskStep.task_id == task_id)
            .order_by(cast(Any, TaskStep.step_order), cast(Any, TaskStep.id))
        ).all()
    )


def get_pending_agent_task_by_session_id(session: Session, session_id: int) -> AgentTask | None:
    return session.exec(
        select(AgentTask)
        .where(AgentTask.session_id == session_id)
        .where(AgentTask.status == TaskStatus.PENDING_APPROVAL.value)
        .order_by(desc(cast(Any, AgentTask.updated_at)), desc(cast(Any, AgentTask.id)))
    ).first()


def create_terminal_session(session: Session, asset_id: int, *, status: str = "connected", last_error: str = "") -> TerminalSession:
    row = TerminalSession(asset_id=asset_id, status=status, last_error=last_error)
    session.add(row)
    session.commit()
    session.refresh(row)
    return row


def update_terminal_session(
    session: Session,
    terminal_session_id: int,
    *,
    status: str | None = None,
    last_error: str | None = None,
    ended_at: datetime | None = None,
) -> TerminalSession | None:
    row = session.get(TerminalSession, terminal_session_id)
    if row is None:
        return None
    if status is not None:
        row.status = status
    if last_error is not None:
        row.last_error = last_error
    if ended_at is not None:
        row.ended_at = ended_at
    session.add(row)
    session.commit()
    session.refresh(row)
    return row


def create_terminal_event(
    session: Session,
    terminal_session_id: int,
    event_type: str,
    metadata: Any = "",
) -> TerminalEvent:
    event_data = metadata
    if not isinstance(metadata, str):
        event_data = json.dumps(metadata, ensure_ascii=False)
    row = TerminalEvent(
        terminal_session_id=terminal_session_id,
        event_type=event_type,
        event_data=event_data,
    )
    session.add(row)
    session.commit()
    session.refresh(row)
    return row


def create_model_usage(
    session: Session,
    *,
    task_id: int,
    provider: str,
    model_name: str,
    base_url_snapshot: str,
    temperature_snapshot: float,
    max_tokens_snapshot: int,
) -> ModelUsage:
    row = ModelUsage(
        task_id=task_id,
        provider=provider,
        model_name=model_name,
        base_url_snapshot=base_url_snapshot,
        temperature_snapshot=temperature_snapshot,
        max_tokens_snapshot=max_tokens_snapshot,
    )
    session.add(row)
    session.commit()
    session.refresh(row)
    return row


def list_model_usages_by_task_id(session: Session, task_id: int) -> list[ModelUsage]:
    return list(
        session.exec(
            select(ModelUsage)
            .where(ModelUsage.task_id == task_id)
            .order_by(cast(Any, ModelUsage.id))
        ).all()
    )
