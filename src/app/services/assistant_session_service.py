from app.db.repositories import (
    get_assistant_session,
    get_or_create_assistant_session,
    list_assistant_sessions_by_asset_id,
)


def create_or_get_assistant_session(session, *, asset_id: int, conversation_id: str, model_name: str):
    return get_or_create_assistant_session(
        session,
        asset_id=asset_id,
        title=conversation_id,
        active_model=model_name,
    )


def list_assistant_session_records(session, asset_id: int):
    return list_assistant_sessions_by_asset_id(session, asset_id)


def get_assistant_session_record(session, session_id: int):
    return get_assistant_session(session, session_id)
