from datetime import UTC, datetime


from sqlmodel import Field, SQLModel


class AssetGroup(SQLModel, table=True):
    __tablename__ = "asset_groups"
    id: int | None = Field(default=None, primary_key=True)
    name: str
    description: str = ""
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


class Asset(SQLModel, table=True):
    __tablename__ = "assets"
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
    __tablename__ = "credentials"
    id: int | None = Field(default=None, primary_key=True)
    asset_id: int
    encryption_version: str
    encrypted_blob: str
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


class SSHKey(SQLModel, table=True):
    __tablename__ = "ssh_keys"
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
    __tablename__ = "model_configs"
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



class ModelUsage(SQLModel, table=True):
    __tablename__ = "model_usages"
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
    __tablename__ = "audit_logs"
    id: int | None = Field(default=None, primary_key=True)
    action: str
    entity_type: str
    actor: str = ""
    entity_id: int | None = None
    asset_id: int | None = None
    conversation_id: str | None = None
    task_id: int | None = None
    details: str = ""
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
