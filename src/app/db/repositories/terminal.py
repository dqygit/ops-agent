import json
from datetime import UTC, datetime
from typing import Any, cast

from sqlalchemy import desc
from sqlmodel import Session, select

from app.db.models import TerminalEvent, TerminalSession


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
    ended_at=None,
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


def get_terminal_session(session: Session, terminal_session_id: int) -> TerminalSession | None:
    return session.get(TerminalSession, terminal_session_id)


def list_terminal_sessions_by_asset_id(session: Session, asset_id: int) -> list[TerminalSession]:
    return list(
        session.exec(
            select(TerminalSession)
            .where(TerminalSession.asset_id == asset_id)
            .order_by(desc(cast(Any, TerminalSession.started_at)), desc(cast(Any, TerminalSession.id)))
        ).all()
    )


def list_terminal_events_by_session_id(session: Session, terminal_session_id: int, limit: int = 20) -> list[TerminalEvent]:
    rows = list(
        session.exec(
            select(TerminalEvent)
            .where(TerminalEvent.terminal_session_id == terminal_session_id)
            .order_by(desc(cast(Any, TerminalEvent.created_at)), desc(cast(Any, TerminalEvent.id)))
        ).all()
    )
    return list(reversed(rows[:limit]))


class TerminalSessionRepository:
    def __init__(self, engine):
        self._engine = engine

    def create_session(self, asset_id: int) -> int:
        with Session(self._engine) as session:
            row = create_terminal_session(session, asset_id)
            if row.id is None:
                raise ValueError("terminal session id is required")
            return row.id

    def update_session(self, terminal_session_id: int, *, status: str | None = None, last_error: str | None = None, ended: bool = False) -> None:
        with Session(self._engine) as session:
            update_terminal_session(
                session,
                terminal_session_id,
                status=status,
                last_error=last_error,
                ended_at=datetime.now(UTC) if ended else None,
            )

    def record_event(self, terminal_session_id: int, event_type: str, metadata: Any = "") -> None:
        with Session(self._engine) as session:
            create_terminal_event(session, terminal_session_id, event_type, metadata)
