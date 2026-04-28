from app.services.approval_service import approve_task, reject_task


class FakeChatService:
    def __init__(self):
        self.calls = []

    def resume_pending_approval(self, *, run_id: str, approved: bool):
        self.calls.append({"run_id": run_id, "approved": approved})
        return {"run_id": run_id, "approved": approved}


def test_approve_task_routes_through_chat_service():
    service = FakeChatService()

    result = approve_task(service, run_id="run-7")

    assert result == {"run_id": "run-7", "approved": True}
    assert service.calls == [{"run_id": "run-7", "approved": True}]


def test_reject_task_routes_through_chat_service():
    service = FakeChatService()

    result = reject_task(service, run_id="run-7")

    assert result == {"run_id": "run-7", "approved": False}
    assert service.calls == [{"run_id": "run-7", "approved": False}]
