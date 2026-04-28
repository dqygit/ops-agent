from sqlmodel import Session, SQLModel, create_engine

from app.db.models import AssistantMessage
from app.services.history_service import serialize_session_messages, list_session_messages, split_active_and_completed_tasks


def test_split_active_and_completed_tasks_moves_completed_items_to_history():
    tasks = [
        {"task_id": 1, "status": "pending_approval"},
        {"task_id": 2, "status": "running"},
        {"task_id": 3, "status": "completed"},
        {"task_id": 4, "status": "rejected"},
    ]

    active, history = split_active_and_completed_tasks(tasks)

    assert [item["task_id"] for item in active] == [1, 2]
    assert [item["task_id"] for item in history] == [3, 4]


def test_history_service_lists_and_serializes_session_messages_in_order():
    engine = create_engine("sqlite://")
    SQLModel.metadata.create_all(engine)

    with Session(engine) as session:
        session.add(AssistantMessage(session_id=7, role="user", content="第一条"))
        session.add(AssistantMessage(session_id=7, role="assistant", content="第二条"))
        session.add(AssistantMessage(session_id=8, role="user", content="其他会话"))
        session.commit()
        messages = list_session_messages(session, 7)

    assert [message.content for message in messages] == ["第一条", "第二条"]
    assert serialize_session_messages(messages) == [
        {"role": "user", "content": "第一条"},
        {"role": "assistant", "content": "第二条"},
    ]
