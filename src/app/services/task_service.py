from app.services.chat_service import create_pending_task


def queue_pending_task(asset_type, user_input: str, planner, active_model_name: str, terminal_context=None):
    return create_pending_task(
        asset_type=asset_type,
        user_input=user_input,
        planner=planner,
        active_model_name=active_model_name,
        terminal_context=terminal_context,
    )
