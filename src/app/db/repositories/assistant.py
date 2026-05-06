from datetime import UTC, datetime
from typing import Any, cast

from sqlalchemy import desc
from sqlmodel import Session, select

from app.db.models import AssistantMessage, AssistantSession


def get_or_create_assistant_session(
    session: Session,
    asset_id: int,
    title: str,
    active_model: str,
    *,
    terminal_session_id: int | None = None,
    model_config_id: int | None = None,
    status: str = "active",
) -> AssistantSession:
    row = session.exec(
        select(AssistantSession)
        .where(AssistantSession.asset_id == asset_id)
        .where(AssistantSession.title == title)
        .order_by(desc(cast(Any, AssistantSession.id)))
    ).first()
    if row is not None:
        row.active_model = active_model
        row.terminal_session_id = terminal_session_id
        row.model_config_id = model_config_id
        row.status = status
        row.updated_at = datetime.now(UTC)
        session.add(row)
        session.commit()
        session.refresh(row)
        return row
    row = AssistantSession(
        asset_id=asset_id,
        title=title,
        active_model=active_model,
        terminal_session_id=terminal_session_id,
        model_config_id=model_config_id,
        status=status,
    )
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
