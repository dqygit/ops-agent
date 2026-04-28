from datetime import UTC, datetime

from sqlmodel import Field, SQLModel


class Asset(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    name: str
    asset_type: str
    host: str
    port: int = 22
    username: str
    auth_type: str
    tags: str = ""
    description: str = ""
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


class Credential(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    asset_id: int
    encryption_version: str
    encrypted_blob: str
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


class TerminalSession(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    asset_id: int
    started_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    ended_at: datetime | None = None
    status: str = "connected"
    last_error: str = ""


class TerminalEvent(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    terminal_session_id: int
    event_data: str = ""
    event_type: str
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


class AssistantSession(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    asset_id: int
    title: str
    active_model: str
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


class AssistantMessage(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    session_id: int
    role: str
    content: str
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


class AgentTask(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    session_id: int
    run_id: str = ""
    asset_id: int
    user_input: str
    attached_terminal_context: str = ""
    task_type: str
    risk_level: str
    status: str
    final_summary: str = ""
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


class TaskStep(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    task_id: int
    step_order: int
    title: str
    command: str
    reason: str
    risk_level: str = "low"
    status: str = "pending"
    output: str = ""
    error_message: str = ""
    started_at: datetime | None = None
    finished_at: datetime | None = None


class Approval(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    task_id: int
    decision: str
    operator: str
    comment: str = ""
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


class ModelUsage(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    task_id: int
    provider: str
    model_name: str
    base_url_snapshot: str
    temperature_snapshot: float
    max_tokens_snapshot: int
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
