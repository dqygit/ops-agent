from sqlmodel import SQLModel, Session, create_engine

from app.db.models import AssistantSession
from app.services.assistant_session_service import (
    create_or_get_assistant_session,
    get_assistant_session_record,
    list_assistant_session_records,
)


def test_assistant_session_service_creates_and_lists_sessions_per_conversation():
    engine = create_engine("sqlite://")
    SQLModel.metadata.create_all(engine)

    with Session(engine) as session:
        first = create_or_get_assistant_session(
            session,
            asset_id=7,
            conversation_id="conv-1",
            model_name="claude-sonnet-4-6",
        )
        same = create_or_get_assistant_session(
            session,
            asset_id=7,
            conversation_id="conv-1",
            model_name="claude-opus-4-7",
        )
        second = create_or_get_assistant_session(
            session,
            asset_id=7,
            conversation_id="conv-2",
            model_name="claude-sonnet-4-6",
        )
        rows = list_assistant_session_records(session, 7)
        fetched = get_assistant_session_record(session, first.id)

    assert first.id is not None
    assert same.id == first.id
    assert same.active_model == "claude-opus-4-7"
    assert second.id is not None
    assert second.id != first.id
    assert [row.title for row in rows] == ["conv-2", "conv-1"]
    assert fetched is not None
    assert fetched.id == first.id
    assert all(isinstance(row, AssistantSession) for row in rows)
