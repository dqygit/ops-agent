from datetime import UTC, datetime
from typing import Any, TypeVar

from sqlmodel import Session

RowT = TypeVar("RowT")


def touch_updated_at(row: Any) -> None:
    row.updated_at = datetime.now(UTC)


def commit_refresh(session: Session, row: RowT) -> RowT:
    session.add(row)
    session.commit()
    session.refresh(row)
    return row
