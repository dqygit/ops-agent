from pydantic import SecretStr
from sqlmodel import SQLModel, Session, create_engine, select

from app.db.models import (
    AgentTask,
    Asset,
    AssetGroup,
    AuditLog,
    AutoApprovalMatch,
    AutoApprovalRule,
    CommandExecution,
    Credential,
    ModelConfigRecord,
    ModelUsage,
    TerminalEvent,
    TerminalSession,
)
from app.db.repositories import (
    create_audit_log,
    create_auto_approval_match,
    create_auto_approval_rule,
    create_command_execution,
    create_model_config,
    create_model_usage,
    get_default_model_config,
    list_audit_logs,
    list_auto_approval_rules_by_session_id,
    list_command_executions_by_task_id,
    list_model_usages_by_task_id,
    set_default_model_config,
)
from app.services.asset_service import (
    GroupNotFoundError,
    create_asset_group_record,
    create_asset_record,
    delete_asset_group_record,
    delete_asset_record,
    get_asset_credential_record,
    get_asset_record,
    list_asset_group_records,
    list_asset_records,
    update_asset_group_record,
    update_asset_record,
)
from app.services.credential_service import CredentialService
from app.shared.enums import AssetType
from app.shared.schemas import AssetCreate
from app.api.schemas import AssetGroupCreate, AssetGroupUpdate


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
    assert str(Credential.__tablename__) == "credentials"
    assert str(TerminalSession.__tablename__) == "terminal_sessions"
    assert str(TerminalEvent.__tablename__) == "terminal_events"
    assert str(AgentTask.__tablename__) == "agent_tasks"
    assert str(ModelConfigRecord.__tablename__) == "model_configs"
    assert str(CommandExecution.__tablename__) == "command_executions"
    assert str(AutoApprovalRule.__tablename__) == "auto_approval_rules"
    assert str(AutoApprovalMatch.__tablename__) == "auto_approval_matches"
    assert str(AuditLog.__tablename__) == "audit_logs"
    assert str(AssetGroup.__tablename__) == "asset_groups"


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
    assert updated.vendor == ""
    assert updated.description == "updated"
    assert len(rows) == 1
    assert rows[0].id == created.id
    assert deleted is True
    assert after_delete is None


def test_asset_group_service_links_assets_and_preserves_assets_on_delete():
    engine = create_engine("sqlite://")
    SQLModel.metadata.create_all(engine)

    with Session(engine) as session:
        group = create_asset_group_record(session, AssetGroupCreate(name="生产环境", description="prod hosts"))
        created = create_asset_record(
            session,
            AssetCreate(
                name="edge-linux",
                asset_type=AssetType.LINUX,
                group_id=group.id,
                host="10.0.0.99",
                username="ops",
                auth_type="password",
            ),
        )
        updated_group = update_asset_group_record(
            session,
            group.id or 0,
            AssetGroupUpdate(name="核心生产", description="core prod hosts"),
        )
        created_group_id = created.group_id
        groups = list_asset_group_records(session)
        deleted = delete_asset_group_record(session, group.id or 0)
        preserved_asset = get_asset_record(session, created.id)
        missing_group_deleted = delete_asset_group_record(session, group.id or 0)

    assert created_group_id == group.id
    assert updated_group is not None
    assert updated_group.name == "核心生产"
    assert updated_group.description == "core prod hosts"
    assert len(groups) == 1
    assert deleted is True
    assert missing_group_deleted is False
    assert preserved_asset is not None
    assert preserved_asset.group_id is None


def test_asset_service_rejects_missing_group_id():
    engine = create_engine("sqlite://")
    SQLModel.metadata.create_all(engine)

    with Session(engine) as session:
        try:
            create_asset_record(
                session,
                AssetCreate(
                    name="edge-linux",
                    asset_type=AssetType.LINUX,
                    group_id=999,
                    host="10.0.0.99",
                    username="ops",
                    auth_type="password",
                ),
            )
        except GroupNotFoundError as exc:
            error = exc
        else:
            error = None

    assert error is not None


def test_asset_service_encrypts_and_rotates_asset_credentials():
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
        assert created_credential is not None
        created_encrypted_blob = created_credential.encrypted_blob
        created_encryption_version = created_credential.encryption_version
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
        assert updated_credential is not None
        updated_encrypted_blob = updated_credential.encrypted_blob
        updated_encryption_version = updated_credential.encryption_version

    assert updated is not None
    assert created_encryption_version == CredentialService.encryption_version
    assert updated_encryption_version == CredentialService.encryption_version
    assert created_encrypted_blob != "initial-secret"
    assert updated_encrypted_blob != "rotated-secret"

    service = CredentialService(secret_key="dev-secret-key")

    assert service.decrypt_secret(created_encrypted_blob) == "initial-secret"
    assert service.decrypt_secret(updated_encrypted_blob) == "rotated-secret"


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

    assert str(ModelUsage.__tablename__) == "model_usages"
    assert len(rows) == 1
    assert rows[0].task_id == 7
    assert rows[0].provider == "anthropic"
    assert rows[0].model_name == "claude-sonnet-4-6"
    assert rows[0].base_url_snapshot == "https://api.anthropic.com"
    assert rows[0].temperature_snapshot == 0.2
    assert rows[0].max_tokens_snapshot == 1024
    assert len(other_rows) == 1
    assert other_rows[0].task_id == 8


def test_workflow_model_config_repository_keeps_one_default_model():
    engine = create_engine("sqlite://")
    SQLModel.metadata.create_all(engine)

    with Session(engine) as session:
        first = create_model_config(
            session,
            name="primary",
            provider="anthropic",
            base_url="https://api.anthropic.com",
            api_key_encryption_version="v1",
            encrypted_api_key="encrypted-one",
            model_name="claude-opus-4-7",
            is_default=True,
        )
        second = create_model_config(
            session,
            name="secondary",
            provider="openai_compatible",
            base_url="https://example.test/v1",
            api_key_encryption_version="v1",
            encrypted_api_key="encrypted-two",
            model_name="gpt-5.5",
        )
        promoted = set_default_model_config(session, second.id or 0)
        default = get_default_model_config(session)
        refreshed_first = session.get(ModelConfigRecord, first.id)

    assert promoted is not None
    assert default is not None
    assert default.id == second.id
    assert default.is_default is True
    assert refreshed_first is not None
    assert refreshed_first.is_default is False


def test_workflow_command_execution_repository_persists_results_by_task_id():
    engine = create_engine("sqlite://")
    SQLModel.metadata.create_all(engine)

    with Session(engine) as session:
        execution = create_command_execution(
            session,
            task_id=7,
            step_id=8,
            asset_id=9,
            terminal_session_id=10,
            command="display interface brief",
            status="completed",
            working_directory="/ops",
            output="GigabitEthernet0/0/1 up",
            error_output="",
            exit_code=0,
        )
        rows = list_command_executions_by_task_id(session, 7)

    assert execution.id is not None
    assert len(rows) == 1
    assert rows[0].command == "display interface brief"
    assert rows[0].working_directory == "/ops"
    assert rows[0].output == "GigabitEthernet0/0/1 up"
    assert rows[0].exit_code == 0


def test_workflow_auto_approval_and_audit_repositories_persist_records():
    engine = create_engine("sqlite://")
    SQLModel.metadata.create_all(engine)

    with Session(engine) as session:
        rule = create_auto_approval_rule(
            session,
            session_id=9,
            name="readonly disk checks",
            asset_type="linux",
            command_name="df",
            command_pattern="df *",
            max_risk_level="low",
        )
        match = create_auto_approval_match(
            session,
            rule_id=rule.id or 0,
            approval_id=3,
            task_id=4,
            step_id=5,
            reason="readonly low-risk command",
        )
        audit = create_audit_log(
            session,
            actor="tester",
            action="auto_approval_rule.created",
            entity_type="auto_approval_rule",
            entity_id=rule.id,
            session_id=9,
        )
        rules = list_auto_approval_rules_by_session_id(session, 9)
        logs = list_audit_logs(session)
        match_id = match.id
        match_reason = match.reason
        audit_id = audit.id

    assert rule.id is not None
    assert rule.readonly_only is True
    assert len(rules) == 1
    assert rules[0].command_name == "df"
    assert match_id is not None
    assert match_reason == "readonly low-risk command"
    assert audit_id is not None
    assert logs[0].action == "auto_approval_rule.created"
