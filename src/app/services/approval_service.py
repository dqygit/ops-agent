def approve_task(chat_service, *, run_id: str):
    return chat_service.resume_pending_approval(run_id=run_id, approved=True)


def reject_task(chat_service, *, run_id: str):
    return chat_service.resume_pending_approval(run_id=run_id, approved=False)
