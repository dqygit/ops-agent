from app.services.chat_service import ChatService


def get_chat_service() -> ChatService:
    from app.main import configured_chat_service

    return configured_chat_service()
