from pydantic import SecretStr

from app.shared.enums import AssetType, ModelProvider, TaskStatus, TerminalEventType
from app.shared.schemas import AgentTaskSummary, AssetCreate, ModelConfig, TerminalContextAttachment


def test_desktop_workflow_schemas_capture_asset_model_and_terminal_context():
    asset = AssetCreate(
        name="core-router",
        asset_type=AssetType.HUAWEI,
        host="10.0.0.10",
        username="ops",
        auth_type="password",
        credential_secret=SecretStr("device-password"),
    )
    model = ModelConfig(
        provider=ModelProvider.ANTHROPIC,
        model_name="claude-sonnet-4-6",
        base_url="https://api.anthropic.com",
        api_key=SecretStr("test-key"),
        timeout_seconds=30,
        temperature=0.2,
        max_tokens=1024,
    )
    context = TerminalContextAttachment(
        terminal_session_id=5,
        selection_label="last route output",
        selected_text="display ip routing-table",
    )
    task = AgentTaskSummary(
        task_id=11,
        status=TaskStatus.PENDING_APPROVAL,
        asset_type=AssetType.HUAWEI,
        model_name="claude-sonnet-4-6",
        steps=[],
    )

    assert asset.asset_type is AssetType.HUAWEI
    assert asset.credential_secret is not None
    assert asset.credential_secret.get_secret_value() == "device-password"
    assert model.provider is ModelProvider.ANTHROPIC
    assert context.terminal_session_id == 5
    assert task.status is TaskStatus.PENDING_APPROVAL
    assert task.model_name == "claude-sonnet-4-6"
    assert TerminalEventType.CONTEXT_ATTACHED.value == "context_attached"
