from pydantic import SecretStr
from sqlmodel import SQLModel, Session, create_engine, select

from app.db.models import AgentTask, Asset, Credential, ModelUsage, TerminalEvent, TerminalSession
from app.db.repositories import create_model_usage, list_model_usages_by_task_id
from app.services.asset_service import (
    create_asset_record,
    delete_asset_record,
    get_asset_credential_record,
    get_asset_record,
    list_asset_records,
    update_asset_record,
)
from app.services.credential_service import CredentialService
from app.shared.enums import AssetType
from app.shared.schemas import AssetCreate


def test_database_models_include_terminal_and_agent_task_tables():
    engine = create_engine("sqlite://")
    SQLModel.metadata.create_all(engine)

    with Session(engine) as session:
        asset = Asset(
            name="linux-a",
            asset_type="linux",
            host="10.0.0.20",
            port=22,
            username="ops",
            auth_type="password",
        )
        session.add(asset)
        session.commit()
        rows = session.exec(select(Asset)).all()

    assert len(rows) == 1
    assert str(Credential.__tablename__) == "credential"
    assert str(TerminalSession.__tablename__) == "terminalsession"
    assert str(TerminalEvent.__tablename__) == "terminalevent"
    assert str(AgentTask.__tablename__) == "agenttask"


def test_asset_service_crud_runs_against_local_sqlite_in_tests():
    engine = create_engine("sqlite://")
    SQLModel.metadata.create_all(engine)

    with Session(engine) as session:
        created = create_asset_record(
            session,
            AssetCreate(
                name="edge-linux",
                asset_type=AssetType.LINUX,
                host="10.0.0.99",
                username="ops",
                auth_type="password",
            ),
        )
        fetched = get_asset_record(session, created.id)
        updated = update_asset_record(
            session,
            created.id,
            AssetCreate(
                name="edge-linux-b",
                asset_type=AssetType.HUAWEI,
                host="10.0.0.100",
                port=2222,
                username="root",
                auth_type="key",
                tags=["core", "prod"],
                description="updated",
            ),
        )
        rows = list_asset_records(session)
        deleted = delete_asset_record(session, created.id)
        after_delete = get_asset_record(session, created.id)

    assert fetched is not None
    assert fetched.id == created.id
    assert updated is not None
    assert updated.name == "edge-linux-b"
    assert updated.asset_type == "huawei"
    assert updated.host == "10.0.0.100"
    assert updated.port == 2222
    assert updated.username == "root"
    assert updated.auth_type == "key"
    assert updated.tags == "core,prod"
    assert updated.description == "updated"
    assert len(rows) == 1
    assert rows[0].id == created.id
    assert deleted is True
    assert after_delete is None


def test_asset_service_creates_and_updates_encrypted_credentials():
    engine = create_engine("sqlite://")
    SQLModel.metadata.create_all(engine)

    with Session(engine) as session:
        created = create_asset_record(
            session,
            AssetCreate(
                name="edge-linux",
                asset_type=AssetType.LINUX,
                host="10.0.0.99",
                username="ops",
                auth_type="password",
                credential_secret=SecretStr("initial-secret"),
            ),
        )
        created_credential = get_asset_credential_record(session, created.id)
        updated = update_asset_record(
            session,
            created.id,
            AssetCreate(
                name="edge-linux",
                asset_type=AssetType.LINUX,
                host="10.0.0.99",
                username="ops",
                auth_type="password",
                credential_secret=SecretStr("rotated-secret"),
            ),
        )
        updated_credential = get_asset_credential_record(session, created.id)

    assert updated is not None
    assert created_credential is not None
    assert updated_credential is not None
    assert created_credential.encryption_version == CredentialService.encryption_version
    assert updated_credential.encryption_version == CredentialService.encryption_version
    assert created_credential.encrypted_blob != "initial-secret"
    assert updated_credential.encrypted_blob != "rotated-secret"

    service = CredentialService(secret_key="dev-secret-key")

    assert service.decrypt_secret(created_credential.encrypted_blob) == "initial-secret"
    assert service.decrypt_secret(updated_credential.encrypted_blob) == "rotated-secret"


def test_model_usage_repository_persists_and_lists_usage_by_task_id():
    engine = create_engine("sqlite://")
    SQLModel.metadata.create_all(engine)

    with Session(engine) as session:
        create_model_usage(
            session,
            task_id=7,
            provider="anthropic",
            model_name="claude-sonnet-4-6",
            base_url_snapshot="https://api.anthropic.com",
            temperature_snapshot=0.2,
            max_tokens_snapshot=1024,
        )
        create_model_usage(
            session,
            task_id=8,
            provider="openai_compatible",
            model_name="gpt-4.1",
            base_url_snapshot="https://example.test/v1",
            temperature_snapshot=0.5,
            max_tokens_snapshot=2048,
        )
        rows = list_model_usages_by_task_id(session, 7)
        other_rows = list_model_usages_by_task_id(session, 8)

    assert str(ModelUsage.__tablename__) == "modelusage"
    assert len(rows) == 1
    assert rows[0].task_id == 7
    assert rows[0].provider == "anthropic"
    assert rows[0].model_name == "claude-sonnet-4-6"
    assert rows[0].base_url_snapshot == "https://api.anthropic.com"
    assert rows[0].temperature_snapshot == 0.2
    assert rows[0].max_tokens_snapshot == 1024
    assert len(other_rows) == 1
    assert other_rows[0].task_id == 8
