from sqlmodel import Session, SQLModel, create_engine

from app.services.message_service import AssistantMessageService


def test_message_service_appends_and_lists_session_messages():
    engine = create_engine("sqlite://")
    SQLModel.metadata.create_all(engine)
    service = AssistantMessageService(lambda: Session(engine))

    service.append_message(session_id=3, role="user", content="检查路由")
    service.append_message(session_id=3, role="assistant", content="检查完成")
    service.append_message(session_id=4, role="user", content="其他会话")

    messages = service.list_messages(session_id=3)

    assert [message.content for message in messages] == ["检查路由", "检查完成"]
    assert service.list_recent_messages(session_id=3) == [
        {"role": "user", "content": "检查路由"},
        {"role": "assistant", "content": "检查完成"},
    ]
