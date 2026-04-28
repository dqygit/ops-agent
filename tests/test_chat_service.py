from app.services.chat_service import ChatService, create_pending_task
from app.shared.enums import AssetType, TaskStatus
from app.shared.schemas import TerminalContextAttachment


class FakePlanner:
    def __call__(self, asset_type, user_input, terminal_context=None, recent_messages=None):
        from app.shared.schemas import PlanStep

        assert terminal_context is not None
        return [
            PlanStep(
                title="Check route table",
                command="display ip routing-table",
                reason=terminal_context.selection_label,
                risk_level="low",
            )
        ]


class FakeRuntime:
    def __init__(self):
        self.start_calls = []
        self.resume_calls = []

    def start_run(self, **kwargs):
        self.start_calls.append(kwargs)
        return {"run_id": kwargs["run_id"], "ui_events": []}

    def resume_run(self, *, run_id: str, approved: bool):
        self.resume_calls.append({"run_id": run_id, "approved": approved})
        return {"run_id": run_id, "ui_events": []}


class FakeSessionStore:
    def __init__(self):
        self.get_or_create_calls = []
        self.list_calls = []

    def get_or_create(self, *, asset_id: int, conversation_id: str, model_name: str):
        self.get_or_create_calls.append(
            {
                "asset_id": asset_id,
                "conversation_id": conversation_id,
                "model_name": model_name,
            }
        )
        return type("AssistantSessionRow", (), {"id": 12})()

    def list_by_asset_id(self, asset_id: int):
        self.list_calls.append(asset_id)
        return [{"id": 12, "asset_id": asset_id, "title": "conv-1"}]


class FakeApprovalStore:
    def __init__(self, task=None, steps=None, latest_approval=None):
        self.task = task
        self.steps = steps or []
        self.latest_approval = latest_approval
        self.pending_calls = []
        self.step_calls = []
        self.approval_calls = []

    def get_pending_task_by_session_id(self, session_id: int):
        self.pending_calls.append(session_id)
        return self.task

    def list_steps_by_task_id(self, task_id: int):
        self.step_calls.append(task_id)
        return list(self.steps)

    def get_latest_approval_by_task_id(self, task_id: int):
        self.approval_calls.append(task_id)
        return self.latest_approval


class FakeMessageService:
    def __init__(self, recent_messages=None):
        self.recent_messages = recent_messages or []
        self.append_calls = []
        self.list_calls = []

    def list_recent_messages(self, *, session_id: int):
        self.list_calls.append(session_id)
        return list(self.recent_messages)

    def append_message(self, *, session_id: int, role: str, content: str):
        self.append_calls.append({"session_id": session_id, "role": role, "content": content})


def test_create_pending_task_uses_explicit_terminal_context():
    result = create_pending_task(
        asset_type=AssetType.HUAWEI,
        user_input="检查路由",
        planner=FakePlanner(),
        active_model_name="claude-sonnet-4-6",
        terminal_context=TerminalContextAttachment(
            terminal_session_id=9,
            selection_label="selected route output",
            selected_text="10.0.0.0/24 via 10.0.0.1",
        ),
    )

    assert result.status is TaskStatus.PENDING_APPROVAL
    assert result.model_name == "claude-sonnet-4-6"
    assert result.steps[0].reason == "selected route output"


def test_chat_service_starts_runtime_with_incrementing_run_ids():
    runtime = FakeRuntime()
    session_store = FakeSessionStore()
    service = ChatService(runtime=runtime, session_store=session_store)

    result = service.start_agent_run(
        conversation_id="conv-1",
        user_message="检查路由",
        asset={"id": 9, "asset_type": "huawei"},
        asset_type=AssetType.HUAWEI,
        model_name="claude-sonnet-4-6",
        terminal_context=TerminalContextAttachment(
            terminal_session_id=9,
            selection_label="selected route output",
            selected_text="10.0.0.0/24 via 10.0.0.1",
        ),
        recent_messages=[{"role": "user", "content": "上一轮"}],
    )

    assert result["run_id"] == "run-1"
    assert session_store.get_or_create_calls == [
        {
            "asset_id": 9,
            "conversation_id": "conv-1",
            "model_name": "claude-sonnet-4-6",
        }
    ]
    assert runtime.start_calls[0]["conversation_id"] == "conv-1"
    assert runtime.start_calls[0]["session_id"] == 12
    assert runtime.start_calls[0]["recent_messages"] == [{"role": "user", "content": "上一轮"}]


def test_chat_service_lists_assistant_sessions_for_asset():
    runtime = FakeRuntime()
    session_store = FakeSessionStore()
    service = ChatService(runtime=runtime, session_store=session_store)

    rows = service.list_assistant_sessions(asset_id=9)

    assert session_store.list_calls == [9]
    assert rows == [{"id": 12, "asset_id": 9, "title": "conv-1"}]


def test_chat_service_resumes_runtime_with_explicit_decision():
    runtime = FakeRuntime()
    service = ChatService(runtime=runtime)

    service.resume_agent_run(run_id="run-7", approved=False)

    assert runtime.resume_calls == [{"run_id": "run-7", "approved": False}]


def test_chat_service_persists_user_message_and_loads_history_before_run():
    runtime = FakeRuntime()
    session_store = FakeSessionStore()
    message_service = FakeMessageService(recent_messages=[{"role": "assistant", "content": "上一轮回复"}])
    service = ChatService(runtime=runtime, session_store=session_store, message_service=message_service)

    service.start_agent_run(
        conversation_id="conv-1",
        user_message="检查路由",
        asset={"id": 9, "asset_type": "huawei"},
        asset_type=AssetType.HUAWEI,
        model_name="claude-sonnet-4-6",
    )

    assert message_service.list_calls == [12]
    assert message_service.append_calls == [{"session_id": 12, "role": "user", "content": "检查路由"}]
    assert runtime.start_calls[0]["recent_messages"] == [
        {"role": "assistant", "content": "上一轮回复"},
        {"role": "user", "content": "检查路由"},
    ]


def test_chat_service_persists_assistant_message_after_resume():
    runtime = FakeRuntime()
    message_service = FakeMessageService()
    service = ChatService(runtime=runtime, message_service=message_service)
    runtime.resume_run = lambda *, run_id, approved: {
        "run_id": run_id,
        "session_id": 12,
        "assistant_message": "检查完成",
        "ui_events": [],
    }

    service.resume_agent_run(run_id="run-7", approved=True)

    assert message_service.append_calls == [{"session_id": 12, "role": "assistant", "content": "检查完成"}]


def test_chat_service_lists_assistant_messages_for_session():
    runtime = FakeRuntime()
    message_service = FakeMessageService(recent_messages=[{"role": "user", "content": "上一轮"}])
    service = ChatService(runtime=runtime, message_service=message_service)

    rows = service.list_assistant_messages(session_id=12)

    assert message_service.list_calls == [12]
    assert rows == [{"role": "user", "content": "上一轮"}]


def test_chat_service_returns_pending_approval_view_from_store():
    runtime = FakeRuntime()
    approval_store = FakeApprovalStore(
        task=type("TaskRow", (), {"id": 8, "run_id": "run-8", "session_id": 12, "status": "pending_approval"})(),
        steps=[type("StepRow", (), {"title": "Check route", "command": "display ip routing-table", "reason": "selected route", "risk_level": "low"})()],
    )
    service = ChatService(runtime=runtime, approval_store=approval_store)

    result = service.get_pending_approval(session_id=12)

    assert result is not None
    assert result.task_id == 8
    assert result.run_id == "run-8"
    assert result.status == "pending_approval"
    assert result.steps[0].command == "display ip routing-table"
    assert approval_store.pending_calls == [12]
    assert approval_store.step_calls == [8]
    assert approval_store.approval_calls == [8]


def test_chat_service_resumes_pending_approval_through_runtime():
    runtime = FakeRuntime()
    service = ChatService(runtime=runtime)

    service.resume_pending_approval(run_id="run-8", approved=True)

    assert runtime.resume_calls == [{"run_id": "run-8", "approved": True}]
