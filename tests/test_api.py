from fastapi.testclient import TestClient
from sqlalchemy.pool import StaticPool
from sqlmodel import SQLModel, Session, create_engine

from app.api import app, get_chat_service, get_terminal_service
from app.services.assistant_session_service import create_or_get_assistant_session
from app.services.message_service import AssistantMessageService
from app.services.model_service import ModelService
from app.db.session import get_session
from app.shared.enums import AssetType, ModelProvider


class FakeChatService:
    def __init__(self):
        self.calls = []
        self.resume_calls = []
        self.pending_calls = []
        self.pending_approval = None

    def start_agent_run(self, **kwargs):
        self.calls.append(kwargs)
        return {
            "run_id": "run-1",
            "session_id": 12,
            "ui_events": [
                {"type": "assistant_status", "payload": {"value": "thinking"}},
                {"type": "approval_requested", "payload": {"message": "Approve this execution plan?"}},
            ],
        }

    def get_pending_approval(self, *, session_id):
        self.pending_calls.append(session_id)
        if self.pending_approval is None:
            return None
        if getattr(self.pending_approval, "session_id", None) != session_id:
            return None
        return self.pending_approval

    def resume_pending_approval(self, *, run_id, approved):
        self.resume_calls.append({"run_id": run_id, "approved": approved})
        return {
            "run_id": run_id,
            "session_id": 12,
            "ui_events": [
                {"type": "assistant_status", "payload": {"value": "executing"}},
                {"type": "assistant_final", "payload": {"message": "检查完成"}},
            ],
        }


class FakeTerminalService:
    def __init__(self):
        self.open_calls = []
        self.close_calls = []
        self.attach_calls = []

    def open_session(self, asset):
        self.open_calls.append(asset)
        return {
            "terminal_session_id": 5,
            "channel": "channel-1",
            "error": "",
        }

    def attach_context(self, terminal_session_id, selection_label, selected_text):
        self.attach_calls.append(
            {
                "terminal_session_id": terminal_session_id,
                "selection_label": selection_label,
                "selected_text": selected_text,
            }
        )
        return type(
            "Attachment",
            (),
            {
                "terminal_session_id": terminal_session_id,
                "selection_label": selection_label,
                "selected_text": selected_text,
            },
        )()

    def close_session(self, terminal_session_id):
        self.close_calls.append(terminal_session_id)
        return terminal_session_id == 5


client = TestClient(app)


def test_health_endpoint_reports_ok():
    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"ok": True}


def test_models_api_lists_selected_and_available_models(tmp_path):
    settings_path = tmp_path / "settings.json"
    ModelService(settings_path=settings_path).save_settings(
        ModelService(settings_path=settings_path).build_default_config().model_copy(
            update={
                "provider": ModelProvider.OPENAI_COMPATIBLE,
                "model_name": "gpt-5.4",
                "base_url": "https://example.test/v1",
            }
        )
    )

    original_init = ModelService.__init__

    def patched_init(self, provider_client=None, settings_path=None):
        original_init(self, provider_client=provider_client, settings_path=settings_path or settings_path_override)

    settings_path_override = settings_path
    ModelService.__init__ = patched_init

    try:
        response = client.get("/api/models")
    finally:
        ModelService.__init__ = original_init

    assert response.status_code == 200
    assert response.json() == {
        "provider": ModelProvider.OPENAI_COMPATIBLE.value,
        "selected_model": "gpt-5.4",
        "available_models": ["gpt-5.5", "gpt-5.4"],
    }


def test_assets_api_lists_created_assets():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    SQLModel.metadata.create_all(engine)

    def override_session():
        with Session(engine) as session:
            yield session

    app.dependency_overrides[get_session] = override_session

    try:
        create_response = client.post(
            "/api/assets",
            json={
                "name": "edge-linux",
                "asset_type": AssetType.LINUX.value,
                "host": "10.0.0.99",
                "port": 22,
                "username": "ops",
                "auth_type": "password",
                "tags": ["core", "prod"],
                "description": "edge node",
            },
        )
        list_response = client.get("/api/assets")
    finally:
        app.dependency_overrides.clear()

    assert create_response.status_code == 201
    assert create_response.json()["name"] == "edge-linux"
    assert create_response.json()["asset_type"] == AssetType.LINUX.value
    assert create_response.json()["tags"] == ["core", "prod"]

    assert list_response.status_code == 200
    assert list_response.json() == [
        {
            "id": 1,
            "name": "edge-linux",
            "asset_type": AssetType.LINUX.value,
            "host": "10.0.0.99",
            "port": 22,
            "username": "ops",
            "auth_type": "password",
            "tags": ["core", "prod"],
            "description": "edge node",
        }
    ]


def test_assets_api_lists_sessions_for_one_asset():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    SQLModel.metadata.create_all(engine)

    def override_session():
        with Session(engine) as session:
            yield session

    app.dependency_overrides[get_session] = override_session

    try:
        create_response = client.post(
            "/api/assets",
            json={
                "name": "core-router",
                "asset_type": AssetType.HUAWEI.value,
                "host": "10.0.0.10",
                "port": 22,
                "username": "ops",
                "auth_type": "password",
                "tags": ["core"],
                "description": "router",
            },
        )
        asset_id = create_response.json()["id"]

        with Session(engine) as session:
            create_or_get_assistant_session(
                session,
                asset_id=asset_id,
                conversation_id="conv-1",
                model_name="claude-sonnet-4-6",
            )
            create_or_get_assistant_session(
                session,
                asset_id=asset_id,
                conversation_id="conv-2",
                model_name="claude-opus-4-6",
            )

        sessions_response = client.get(f"/api/assets/{asset_id}/sessions")
        missing_response = client.get("/api/assets/999/sessions")
    finally:
        app.dependency_overrides.clear()

    assert sessions_response.status_code == 200
    assert sessions_response.json() == [
        {
            "id": 2,
            "asset_id": asset_id,
            "title": "conv-2",
            "active_model": "claude-opus-4-6",
        },
        {
            "id": 1,
            "asset_id": asset_id,
            "title": "conv-1",
            "active_model": "claude-sonnet-4-6",
        },
    ]

    assert missing_response.status_code == 404
    assert missing_response.json() == {"detail": "Asset not found"}


def test_chat_session_api_returns_model_and_messages():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    SQLModel.metadata.create_all(engine)

    def override_session():
        with Session(engine) as session:
            yield session

    app.dependency_overrides[get_session] = override_session

    try:
        create_response = client.post(
            "/api/assets",
            json={
                "name": "chat-node",
                "asset_type": AssetType.LINUX.value,
                "host": "10.0.0.50",
                "port": 22,
                "username": "ops",
                "auth_type": "password",
                "tags": [],
                "description": "",
            },
        )
        asset_id = create_response.json()["id"]

        with Session(engine) as session:
            assistant_session = create_or_get_assistant_session(
                session,
                asset_id=asset_id,
                conversation_id="conversation-1",
                model_name="claude-sonnet-4-6",
            )
            session_id = assistant_session.id or 0
            message_service = AssistantMessageService(lambda: session)
            message_service.append_message(session_id=session_id, role="user", content="检查路由")
            message_service.append_message(session_id=session_id, role="assistant", content="检查完成")

        session_response = client.get(f"/api/chat/sessions/{session_id}")
        missing_response = client.get("/api/chat/sessions/999")
    finally:
        app.dependency_overrides.clear()

    assert session_response.status_code == 200
    assert session_response.json() == {
        "session_id": session_id,
        "asset_id": asset_id,
        "model_name": "claude-sonnet-4-6",
        "messages": [
            {"role": "user", "content": "检查路由"},
            {"role": "assistant", "content": "检查完成"},
        ],
    }

    assert missing_response.status_code == 404
    assert missing_response.json() == {"detail": "Chat session not found"}


def test_chat_run_api_starts_run_restores_pending_approval_and_returns_ui_events():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    SQLModel.metadata.create_all(engine)
    fake_chat_service = FakeChatService()
    fake_chat_service.pending_approval = type(
        "ApprovalView",
        (),
        {
            "task_id": 8,
            "run_id": "run-1",
            "session_id": 12,
            "status": "pending_approval",
            "message": "Approve this execution plan?",
            "latest_decision": None,
            "steps": [
                type(
                    "PlanStep",
                    (),
                    {
                        "title": "Check interface status",
                        "command": "display interface brief",
                        "reason": "selected interface",
                        "risk_level": "low",
                    },
                )()
            ],
        },
    )()

    def override_session():
        with Session(engine) as session:
            yield session

    app.dependency_overrides[get_session] = override_session
    app.dependency_overrides[get_chat_service] = lambda: fake_chat_service

    try:
        create_response = client.post(
            "/api/assets",
            json={
                "name": "run-node",
                "asset_type": AssetType.HUAWEI.value,
                "host": "10.0.0.60",
                "port": 22,
                "username": "ops",
                "auth_type": "password",
                "tags": [],
                "description": "",
            },
        )
        asset_id = create_response.json()["id"]
        run_response = client.post(
            "/api/chat/runs",
            json={
                "conversation_id": "conversation-1",
                "user_message": "检查接口状态",
                "asset_id": asset_id,
                "model_name": "claude-sonnet-4-6",
                "terminal_context": {"selection_label": "selected interface"},
                "recent_messages": [{"role": "user", "content": "上一轮"}],
            },
        )
        pending_response = client.get("/api/chat/sessions/12/pending-approval")
        approval_response = client.post(
            "/api/chat/runs/run-1/approval",
            json={"approved": True},
        )
        missing_pending_response = client.get("/api/chat/sessions/999/pending-approval")
        missing_asset_response = client.post(
            "/api/chat/runs",
            json={
                "conversation_id": "conversation-1",
                "user_message": "检查接口状态",
                "asset_id": 999,
                "model_name": "claude-sonnet-4-6",
                "recent_messages": [],
            },
        )
    finally:
        app.dependency_overrides.clear()

    assert run_response.status_code == 200
    assert run_response.json() == {
        "run_id": "run-1",
        "session_id": 12,
        "ui_events": [
            {"type": "assistant_status", "payload": {"value": "thinking"}},
            {"type": "approval_requested", "payload": {"message": "Approve this execution plan?"}},
        ],
    }

    assert pending_response.status_code == 200
    assert pending_response.json() == {
        "task_id": 8,
        "run_id": "run-1",
        "session_id": 12,
        "status": "pending_approval",
        "message": "Approve this execution plan?",
        "latest_decision": None,
        "steps": [
            {
                "title": "Check interface status",
                "command": "display interface brief",
                "reason": "selected interface",
                "risk_level": "low",
            }
        ],
    }

    assert approval_response.status_code == 200
    assert approval_response.json() == {
        "run_id": "run-1",
        "session_id": 12,
        "ui_events": [
            {"type": "assistant_status", "payload": {"value": "executing"}},
            {"type": "assistant_final", "payload": {"message": "检查完成"}},
        ],
    }

    assert len(fake_chat_service.calls) == 1
    assert fake_chat_service.calls[0]["conversation_id"] == "conversation-1"
    assert fake_chat_service.calls[0]["user_message"] == "检查接口状态"
    assert fake_chat_service.calls[0]["asset"].id == asset_id
    assert fake_chat_service.calls[0]["asset_type"] is AssetType.HUAWEI
    assert fake_chat_service.calls[0]["model_name"] == "claude-sonnet-4-6"
    assert fake_chat_service.calls[0]["terminal_context"] == {"selection_label": "selected interface"}
    assert fake_chat_service.calls[0]["recent_messages"] == [{"role": "user", "content": "上一轮"}]

    assert fake_chat_service.pending_calls == [12, 999]
    assert fake_chat_service.resume_calls == [{"run_id": "run-1", "approved": True}]

    assert missing_pending_response.status_code == 200
    assert missing_pending_response.json() is None

    assert missing_asset_response.status_code == 404
    assert missing_asset_response.json() == {"detail": "Asset not found"}


def test_terminal_session_api_opens_attaches_context_and_closes_session():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    SQLModel.metadata.create_all(engine)
    fake_terminal_service = FakeTerminalService()

    def override_session():
        with Session(engine) as session:
            yield session

    app.dependency_overrides[get_session] = override_session
    app.dependency_overrides[get_terminal_service] = lambda: fake_terminal_service

    try:
        create_response = client.post(
            "/api/assets",
            json={
                "name": "term-node",
                "asset_type": AssetType.LINUX.value,
                "host": "10.0.0.70",
                "port": 22,
                "username": "ops",
                "auth_type": "password",
                "tags": [],
                "description": "",
            },
        )
        asset_id = create_response.json()["id"]
        open_response = client.post(
            "/api/terminal/sessions",
            json={"asset_id": asset_id},
        )
        context_response = client.post(
            "/api/terminal/sessions/5/context",
            json={
                "selection_label": "selected terminal output",
                "selected_text": "channel-1",
            },
        )
        close_response = client.delete("/api/terminal/sessions/5")
        missing_asset_response = client.post(
            "/api/terminal/sessions",
            json={"asset_id": 999},
        )
        missing_session_response = client.delete("/api/terminal/sessions/999")
    finally:
        app.dependency_overrides.clear()

    assert open_response.status_code == 200
    assert open_response.json() == {
        "terminal_session_id": 5,
        "channel": "channel-1",
        "error": "",
    }
    assert len(fake_terminal_service.open_calls) == 1
    assert fake_terminal_service.open_calls[0].id == asset_id

    assert context_response.status_code == 200
    assert context_response.json() == {
        "terminal_session_id": 5,
        "selection_label": "selected terminal output",
        "selected_text": "channel-1",
    }
    assert fake_terminal_service.attach_calls == [
        {
            "terminal_session_id": 5,
            "selection_label": "selected terminal output",
            "selected_text": "channel-1",
        }
    ]

    assert close_response.status_code == 204
    assert close_response.text == ""
    assert fake_terminal_service.close_calls == [5, 999]

    assert missing_asset_response.status_code == 404
    assert missing_asset_response.json() == {"detail": "Asset not found"}

    assert missing_session_response.status_code == 404
    assert missing_session_response.json() == {"detail": "Terminal session not found"}


def test_assets_api_gets_updates_and_deletes_one_asset():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    SQLModel.metadata.create_all(engine)

    def override_session():
        with Session(engine) as session:
            yield session

    app.dependency_overrides[get_session] = override_session

    try:
        create_response = client.post(
            "/api/assets",
            json={
                "name": "core-router",
                "asset_type": AssetType.HUAWEI.value,
                "host": "10.0.0.10",
                "port": 22,
                "username": "ops",
                "auth_type": "password",
                "tags": ["core"],
                "description": "router",
            },
        )
        asset_id = create_response.json()["id"]
        get_response = client.get(f"/api/assets/{asset_id}")
        update_response = client.put(
            f"/api/assets/{asset_id}",
            json={
                "name": "core-router-b",
                "asset_type": AssetType.LINUX.value,
                "host": "10.0.0.20",
                "port": 2222,
                "username": "root",
                "auth_type": "key",
                "tags": ["prod", "db"],
                "description": "updated router",
            },
        )
        delete_response = client.delete(f"/api/assets/{asset_id}")
        missing_get_response = client.get(f"/api/assets/{asset_id}")
        missing_update_response = client.put(
            f"/api/assets/{asset_id}",
            json={
                "name": "missing",
                "asset_type": AssetType.LINUX.value,
                "host": "10.0.0.30",
                "port": 22,
                "username": "ops",
                "auth_type": "password",
                "tags": [],
                "description": "",
            },
        )
        missing_delete_response = client.delete(f"/api/assets/{asset_id}")
    finally:
        app.dependency_overrides.clear()

    assert create_response.status_code == 201

    assert get_response.status_code == 200
    assert get_response.json() == {
        "id": asset_id,
        "name": "core-router",
        "asset_type": AssetType.HUAWEI.value,
        "host": "10.0.0.10",
        "port": 22,
        "username": "ops",
        "auth_type": "password",
        "tags": ["core"],
        "description": "router",
    }

    assert update_response.status_code == 200
    assert update_response.json() == {
        "id": asset_id,
        "name": "core-router-b",
        "asset_type": AssetType.LINUX.value,
        "host": "10.0.0.20",
        "port": 2222,
        "username": "root",
        "auth_type": "key",
        "tags": ["prod", "db"],
        "description": "updated router",
    }

    assert delete_response.status_code == 204
    assert delete_response.text == ""

    assert missing_get_response.status_code == 404
    assert missing_get_response.json() == {"detail": "Asset not found"}

    assert missing_update_response.status_code == 404
    assert missing_update_response.json() == {"detail": "Asset not found"}

    assert missing_delete_response.status_code == 404
    assert missing_delete_response.json() == {"detail": "Asset not found"}
