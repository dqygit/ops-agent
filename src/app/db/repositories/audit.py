from typing import Any, cast

from sqlalchemy import desc
from sqlmodel import Session, select

from app.db.models import AuditLog


def create_audit_log(session: Session, **payload: Any) -> AuditLog:
    row = AuditLog(**payload)
    session.add(row)
    session.commit()
    session.refresh(row)
    return row


def list_audit_logs(session: Session, limit: int = 100) -> list[AuditLog]:
    return list(
        session.exec(
            select(AuditLog)
            .order_by(desc(cast(Any, AuditLog.created_at)), desc(cast(Any, AuditLog.id)))
            .limit(limit)
        ).all()
    )
