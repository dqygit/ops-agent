from app.db.repositories import create_assistant_message, list_assistant_messages


class AssistantMessageService:
    def __init__(self, session_factory):
        self._session_factory = session_factory

    def append_message(self, *, session_id: int, role: str, content: str):
        with self._session_factory() as session:
            return create_assistant_message(session, session_id=session_id, role=role, content=content)

    def list_messages(self, *, session_id: int):
        with self._session_factory() as session:
            return list_assistant_messages(session, session_id)

    def list_recent_messages(self, *, session_id: int) -> list[dict[str, str]]:
        rows = self.list_messages(session_id=session_id)
        return [{"role": row.role, "content": row.content} for row in rows]
