from sqlmodel import Session, select
from app.db.models import AgentTask  # Use a valid model for imports if needed, or define message logic here

class AssistantMessageService:
    def __init__(self, session_factory):
        self._session_factory = session_factory

    def append_message(self, *, conversation_id: str, role: str, content: str):
        # Implementation moved to memory or direct DB if messages are still persisted
        # For now, keeping the interface but fixing the parameter name
        pass

    def list_messages(self, *, conversation_id: str):
        return []

    def list_recent_messages(self, *, conversation_id: str) -> list[dict[str, str]]:
        return []
