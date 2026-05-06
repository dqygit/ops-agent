from datetime import UTC, datetime
from typing import ClassVar

from sqlmodel import Field, SQLModel


class AssetGroup(SQLModel, table=True):
    __tablename__: ClassVar[str] = "asset_groups"
    id: int | None = Field(default=None, primary_key=True)
    name: str
    description: str = ""
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


class Asset(SQLModel, table=True):
    __tablename__: ClassVar[str] = "assets"
    id: int | None = Field(default=None, primary_key=True)
    group_id: int | None = None
    ssh_key_id: int | None = None
    name: str
    asset_type: str
    host: str = ""
    port: int = 22
    username: str = ""
    auth_type: str = ""
    tags: str = ""
    vendor: str = ""
    description: str = ""
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


class Credential(SQLModel, table=True):
    __tablename__: ClassVar[str] = "credentials"
    id: int | None = Field(default=None, primary_key=True)
    asset_id: int
    encryption_version: str
    encrypted_blob: str
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


class SSHKey(SQLModel, table=True):
    __tablename__: ClassVar[str] = "ssh_keys"
    id: int | None = Field(default=None, primary_key=True)
    name: str
    public_key: str = ""
    private_key_encryption_version: str
    encrypted_private_key: str
    passphrase_encryption_version: str | None = None
    encrypted_passphrase: str | None = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


class ModelConfigRecord(SQLModel, table=True):
    __tablename__: ClassVar[str] = "model_configs"
    id: int | None = Field(default=None, primary_key=True)
    name: str
    provider: str
    base_url: str
    api_key_encryption_version: str
    encrypted_api_key: str
    model_name: str
    is_default: bool = False
    timeout_seconds: int = 30
    temperature: float = 0.2
    max_tokens: int = 1024
    description: str = ""
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


class TerminalSession(SQLModel, table=True):
    __tablename__: ClassVar[str] = "terminal_sessions"
    id: int | None = Field(default=None, primary_key=True)
    asset_id: int
    started_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    ended_at: datetime | None = None
    status: str = "connected"
    last_error: str = ""


class TerminalEvent(SQLModel, table=True):
    __tablename__: ClassVar[str] = "terminal_events"
    id: int | None = Field(default=None, primary_key=True)
    terminal_session_id: int
    event_data: str = ""
    event_type: str
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


class AssistantSession(SQLModel, table=True):
    __tablename__: ClassVar[str] = "assistant_sessions"
    id: int | None = Field(default=None, primary_key=True)
    asset_id: int
    terminal_session_id: int | None = None
    model_config_id: int | None = None
    title: str
    active_model: str
    status: str = "active"
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


class AssistantMessage(SQLModel, table=True):
    __tablename__: ClassVar[str] = "assistant_messages"
    id: int | None = Field(default=None, primary_key=True)
    session_id: int
    role: str
    content: str
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


class AgentTask(SQLModel, table=True):
    __tablename__: ClassVar[str] = "agent_tasks"
    id: int | None = Field(default=None, primary_key=True)
    session_id: int
    parent_task_id: int | None = None
    run_id: str = ""
    asset_id: int
    terminal_session_id: int | None = None
    user_input: str
    attached_terminal_context: str = ""
    task_type: str
    risk_level: str
    status: str
    final_summary: str = ""
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


class TaskStep(SQLModel, table=True):
    __tablename__: ClassVar[str] = "task_steps"
    id: int | None = Field(default=None, primary_key=True)
    task_id: int
    step_order: int
    title: str
    command: str
    reason: str
    working_directory: str = ""
    expected_output: str = ""
    risk_level: str = "low"
    status: str = "pending"
    output: str = ""
    error_message: str = ""
    exit_code: int | None = None
    started_at: datetime | None = None
    finished_at: datetime | None = None


class Approval(SQLModel, table=True):
    __tablename__: ClassVar[str] = "approvals"
    id: int | None = Field(default=None, primary_key=True)
    task_id: int
    step_id: int | None = None
    asset_id: int | None = None
    terminal_session_id: int | None = None
    command: str = ""
    working_directory: str = ""
    risk_level: str = "low"
    llm_explanation: str = ""
    expected_output: str = ""
    decision: str
    operator: str
    comment: str = ""
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


class CommandExecution(SQLModel, table=True):
    __tablename__: ClassVar[str] = "command_executions"
    id: int | None = Field(default=None, primary_key=True)
    task_id: int
    step_id: int
    asset_id: int
    terminal_session_id: int
    command: str
    status: str
    approval_id: int | None = None
    working_directory: str = ""
    output: str = ""
    error_output: str = ""
    exit_code: int | None = None
    started_at: datetime | None = None
    finished_at: datetime | None = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


class AutoApprovalRule(SQLModel, table=True):
    __tablename__: ClassVar[str] = "auto_approval_rules"
    id: int | None = Field(default=None, primary_key=True)
    session_id: int
    name: str
    asset_type: str = ""
    asset_tags: str = ""
    command_name: str = ""
    command_pattern: str = ""
    max_risk_level: str = "low"
    readonly_only: bool = True
    max_duration_seconds: int = 30
    enabled: bool = True
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


class AutoApprovalMatch(SQLModel, table=True):
    __tablename__: ClassVar[str] = "auto_approval_matches"
    id: int | None = Field(default=None, primary_key=True)
    rule_id: int
    approval_id: int
    task_id: int
    step_id: int | None = None
    reason: str = ""
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


class ModelUsage(SQLModel, table=True):
    __tablename__: ClassVar[str] = "model_usages"
    id: int | None = Field(default=None, primary_key=True)
    task_id: int
    model_config_id: int | None = None
    provider: str
    model_name: str
    base_url_snapshot: str
    temperature_snapshot: float
    max_tokens_snapshot: int
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


class AuditLog(SQLModel, table=True):
    __tablename__: ClassVar[str] = "audit_logs"
    id: int | None = Field(default=None, primary_key=True)
    action: str
    entity_type: str
    actor: str = ""
    entity_id: int | None = None
    asset_id: int | None = None
    session_id: int | None = None
    task_id: int | None = None
    details: str = ""
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
