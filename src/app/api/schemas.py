from typing import Any

from datetime import datetime

from pydantic import BaseModel, Field, SecretStr


class AssetGroupCreate(BaseModel):
    name: str
    description: str = ""


class AssetGroupUpdate(BaseModel):
    name: str | None = None
    description: str | None = None


class AssetGroupView(BaseModel):
    id: int
    name: str
    description: str
    created_at: datetime
    updated_at: datetime


class AssetView(BaseModel):
    id: int
    group_id: int | None = None
    ssh_key_id: int | None = None
    name: str
    asset_type: str
    host: str
    port: int
    username: str
    auth_type: str
    tags: list[str]
    vendor: str
    description: str


class TerminalEventSummaryView(BaseModel):
    id: int
    event_type: str
    event_data: str
    created_at: datetime


class AssetContextView(BaseModel):
    asset: AssetView
    recent_terminal_events: list[TerminalEventSummaryView]


class ModelsView(BaseModel):
    provider: str
    selected_model: str
    available_models: list[str]


class ModelConfigView(BaseModel):
    id: int
    name: str
    provider: str
    base_url: str
    api_key_masked: str
    model_name: str
    is_default: bool
    timeout_seconds: int = 30
    temperature: float = 0.2
    max_tokens: int = 1024
    description: str
    created_at: datetime | None = None
    updated_at: datetime | None = None


class ModelConfigCreate(BaseModel):
    name: str
    provider: str
    base_url: str
    api_key: SecretStr
    model_name: str
    is_default: bool = False
    timeout_seconds: int = 30
    temperature: float = 0.2
    max_tokens: int = 1024
    description: str = ""


class ModelConfigUpdate(BaseModel):
    name: str | None = None
    provider: str | None = None
    base_url: str | None = None
    api_key: SecretStr | None = None
    model_name: str | None = None
    is_default: bool | None = None
    timeout_seconds: int | None = None
    temperature: float | None = None
    max_tokens: int | None = None
    description: str | None = None


class ModelConnectionTestRequest(BaseModel):
    provider: str
    base_url: str
    api_key: SecretStr
    model_name: str
    timeout_seconds: int = 30
    temperature: float = 0.2
    max_tokens: int = 1024


class ModelConnectionTestResponse(BaseModel):
    success: bool
    message: str


class SSHKeyView(BaseModel):
    id: int
    name: str
    public_key: str
    has_passphrase: bool
    created_at: datetime
    updated_at: datetime


class AssistantMessageView(BaseModel):
    role: str
    content: str


class ChatSessionView(BaseModel):
    conversation_id: str
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
    conversation_id: str
    ui_events: list[dict]


class ChatApprovalRequest(BaseModel):
    approved: bool


class AutoApprovalRuleCreate(BaseModel):
    name: str
    asset_type: str = ""
    asset_tags: list[str] = Field(default_factory=list)
    command_name: str = ""
    command_pattern: str = ""
    max_risk_level: str = "low"
    readonly_only: bool = True
    max_duration_seconds: int = 30
    enabled: bool = True


class AutoApprovalRuleUpdate(BaseModel):
    name: str | None = None
    asset_type: str | None = None
    asset_tags: list[str] | None = None
    command_name: str | None = None
    command_pattern: str | None = None
    max_risk_level: str | None = None
    readonly_only: bool | None = None
    max_duration_seconds: int | None = None
    enabled: bool | None = None


class AutoApprovalRuleView(BaseModel):
    id: int
    conversation_id: str
    name: str
    asset_type: str
    asset_tags: list[str]
    command_name: str
    command_pattern: str
    max_risk_level: str
    readonly_only: bool
    max_duration_seconds: int
    enabled: bool
    created_at: datetime
    updated_at: datetime


class AutoApprovalMatchRequest(BaseModel):
    asset_type: str = ""
    asset_tags: list[str] = Field(default_factory=list)
    command: str
    risk_level: str = "low"
    estimated_duration_seconds: int | None = None


class AutoApprovalMatchResponse(BaseModel):
    matched: bool
    rule_id: int | None = None
    reason: str


class ApprovalRecordView(BaseModel):
    id: int
    task_id: int
    step_id: int | None
    asset_id: int | None
    terminal_id: str | None
    command: str
    working_directory: str
    risk_level: str
    llm_explanation: str
    expected_output: str
    decision: str
    operator: str
    comment: str
    created_at: datetime


class CommandExecutionView(BaseModel):
    id: int
    task_id: int
    step_id: int
    asset_id: int
    terminal_id: str
    command: str
    status: str
    approval_id: int | None
    working_directory: str
    output: str
    error_output: str
    exit_code: int | None
    started_at: datetime | None
    finished_at: datetime | None
    created_at: datetime


class TaskStepRecordView(BaseModel):
    id: int
    task_id: int
    step_order: int
    title: str
    command: str
    reason: str
    working_directory: str
    expected_output: str
    risk_level: str
    status: str
    output: str
    error_message: str
    exit_code: int | None
    started_at: datetime | None
    finished_at: datetime | None


class TaskDetailView(BaseModel):
    id: int
    conversation_id: str
    parent_task_id: int | None
    run_id: str
    asset_id: int
    terminal_id: str | None
    user_input: str
    attached_terminal_context: str
    task_type: str
    risk_level: str
    status: str
    final_summary: str
    created_at: datetime
    updated_at: datetime
    steps: list[TaskStepRecordView]
    approvals: list[ApprovalRecordView]
    command_executions: list[CommandExecutionView]


class ConsoleSessionRecordView(BaseModel):
    id: int
    title: str
    model: str


class ConsoleBootstrapView(BaseModel):
    assets: list[AssetView]
    groups: list[AssetGroupView]
    historyByAsset: dict[int, list[ConsoleSessionRecordView]]
    modelOptions: list[str]
    sshKeys: list[SSHKeyView] = Field(default_factory=list)
    terminalSessionId: str | None = None
    terminalSessionChannel: str | None = None
    terminalSessionError: str = ""
    initialPrompt: str = ""
    terminalOutput: str = ""
    initialEvents: list[dict] = Field(default_factory=list)


class ConsoleRunRequest(BaseModel):
    prompt: str
    mode: str = "agent"
    currentEvents: list[dict] = Field(default_factory=list)
    asset_id: int | None = None
    terminal_id: str | None = None
    conversation_id: str = "console"
    model_name: str | None = None
    terminal_context: dict | None = None


class ConsoleApprovalRequest(BaseModel):
    runtime_id: str
    approved: bool
    approval_token: str | None = None
    allow_prefix: str | None = None


class RuntimeStepView(BaseModel):
    step_id: str
    title: str
    command: str
    reason: str
    risk_level: str
    working_directory: str | None = None
    expected_output: str | None = None
    status: str
    output: str = ""
    exit_code: int | None = None


class RuntimeSummaryView(BaseModel):
    runtime_id: str
    conversation_id: str
    asset_id: int
    terminal_id: str | None = None
    status: str
    current_step_id: str | None = None
    pending_approval_step_id: str | None = None
    updated_at: datetime


class RuntimeSnapshotView(BaseModel):
    runtime_id: str
    conversation_id: str
    asset_id: int
    terminal_id: str | None = None
    status: str
    steps: list[RuntimeStepView] = Field(default_factory=list)
    current_step_id: str | None = None
    pending_approval_step_id: str | None = None
    last_output_excerpt: str = ""
    summary: str | None = None
    error_message: str | None = None
    created_at: datetime
    updated_at: datetime
    last_sequence: int = 0


class RuntimeEventView(BaseModel):
    type: str
    conversation_id: str
    runtime_id: str
    sequence: int
    timestamp: str
    payload: dict = Field(default_factory=dict)


class RuntimeEventsResponse(BaseModel):
    latest_sequence: int
    events: list[dict[str, Any]] = Field(default_factory=list)


class ConversationSummaryView(BaseModel):
    id: str
    title: str
    selected_model: str | None = None
    created_at: datetime
    updated_at: datetime
    event_count: int
    last_event_kind: str | None = None


class ConversationDetailView(BaseModel):
    id: str
    title: str
    selected_model: str | None = None
    created_at: datetime
    updated_at: datetime
    events: list[dict] = Field(default_factory=list)


class ConversationCreateRequest(BaseModel):
    selected_model: str | None = None


class ConversationCreateResponse(BaseModel):
    conversation: ConversationSummaryView
    events: list[dict] = Field(default_factory=list)


class ConversationAppendEventsRequest(BaseModel):
    events: list[dict] = Field(default_factory=list)


class PendingApprovalStepView(BaseModel):
    title: str
    command: str
    reason: str
    risk_level: str
    working_directory: str = ""
    expected_output: str = ""


class PendingApprovalView(BaseModel):
    task_id: int
    run_id: str
    conversation_id: str
    status: str
    message: str
    latest_decision: str | None = None
    steps: list[PendingApprovalStepView]


class SerialPortView(BaseModel):
    device: str
    description: str
    hwid: str
    name: str | None = None
    vid: int | None = None
    pid: int | None = None
    serial_number: str | None = None
    location: str | None = None
    manufacturer: str | None = None
    product: str | None = None
    interface: str | None = None
