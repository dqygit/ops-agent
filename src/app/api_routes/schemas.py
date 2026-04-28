from pydantic import BaseModel, Field


class AssetView(BaseModel):
    id: int
    name: str
    asset_type: str
    host: str
    port: int
    username: str
    auth_type: str
    tags: list[str]
    description: str


class AssistantSessionView(BaseModel):
    id: int
    asset_id: int
    title: str
    active_model: str


class ModelsView(BaseModel):
    provider: str
    selected_model: str
    available_models: list[str]


class AssistantMessageView(BaseModel):
    role: str
    content: str


class ChatSessionView(BaseModel):
    session_id: int
    asset_id: int
    model_name: str
    messages: list[AssistantMessageView]


class ChatRunRequest(BaseModel):
    conversation_id: str
    user_message: str
    asset_id: int
    model_name: str
    terminal_context: dict | None = None
    recent_messages: list[dict[str, str]] = Field(default_factory=list)


class ChatRunResponse(BaseModel):
    run_id: str
    session_id: int
    ui_events: list[dict]


class ChatApprovalRequest(BaseModel):
    approved: bool


class PendingApprovalStepView(BaseModel):
    title: str
    command: str
    reason: str
    risk_level: str


class PendingApprovalView(BaseModel):
    task_id: int
    run_id: str
    session_id: int
    status: str
    message: str
    latest_decision: str | None = None
    steps: list[PendingApprovalStepView]
