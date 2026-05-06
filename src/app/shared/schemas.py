from pydantic import BaseModel, Field, SecretStr, model_validator

from app.shared.enums import AssetType, ModelProvider, TaskStatus


class AssetCreate(BaseModel):
    name: str
    asset_type: AssetType
    group_id: int | None = None
    ssh_key_id: int | None = None
    host: str = ""
    port: int = 22
    username: str = ""
    auth_type: str = ""
    credential_secret: SecretStr | None = None
    tags: list[str] = Field(default_factory=list)
    vendor: str = ""
    description: str = ""

    @model_validator(mode="after")
    def validate_connection_fields(self):
        if self.asset_type is AssetType.LOCAL_TERMINAL:
            return self
        if not self.host:
            raise ValueError("host is required for remote assets")
        if not self.username:
            raise ValueError("username is required for remote assets")
        if not self.auth_type:
            raise ValueError("auth_type is required for remote assets")
        return self


class SSHKeyCreate(BaseModel):
    name: str
    public_key: str = ""
    private_key: SecretStr
    passphrase: SecretStr | None = None


class SSHKeyUpdate(BaseModel):
    name: str | None = None
    public_key: str | None = None
    private_key: SecretStr | None = None
    passphrase: SecretStr | None = None


class ModelConfig(BaseModel):
    provider: ModelProvider
    model_name: str
    base_url: str
    api_key: SecretStr
    name: str = "default"
    is_default: bool = True
    description: str = ""
    timeout_seconds: int = 30
    temperature: float = 0.2
    max_tokens: int = 1024


class TerminalContextAttachment(BaseModel):
    terminal_session_id: int
    selection_label: str
    selected_text: str


class PlanStep(BaseModel):
    title: str
    command: str = ""
    reason: str
    risk_level: str = "low"
    working_directory: str = ""
    expected_output: str = ""


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
