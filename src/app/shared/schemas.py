from pydantic import BaseModel, Field, SecretStr

from app.shared.enums import AssetType, ModelProvider, TaskStatus


class AssetCreate(BaseModel):
    name: str
    asset_type: AssetType
    host: str
    port: int = 22
    username: str
    auth_type: str
    credential_secret: SecretStr | None = None
    tags: list[str] = Field(default_factory=list)
    description: str = ""


class ModelConfig(BaseModel):
    provider: ModelProvider
    model_name: str
    base_url: str
    api_key: SecretStr
    timeout_seconds: int = 30
    temperature: float = 0.2
    max_tokens: int = 1024


class TerminalContextAttachment(BaseModel):
    terminal_session_id: int
    selection_label: str
    selected_text: str


class PlanStep(BaseModel):
    title: str
    command: str
    reason: str
    risk_level: str = "low"


class AgentTaskSummary(BaseModel):
    task_id: int
    status: TaskStatus
    asset_type: AssetType
    model_name: str
    steps: list[PlanStep]


class ApprovalView(BaseModel):
    task_id: int
    run_id: str
    session_id: int
    status: str
    message: str
    steps: list[PlanStep]
    latest_decision: str | None = None
