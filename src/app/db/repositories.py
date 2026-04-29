import json
from datetime import UTC, datetime
from typing import Any, cast

from sqlalchemy import desc
from sqlmodel import Session, select

from app.db.models import (
    Approval,
    AgentTask,
    AssistantMessage,
    AssistantSession,
    Asset,
    AssetGroup,
    AuditLog,
    AutoApprovalMatch,
    AutoApprovalRule,
    CommandExecution,
    Credential,
    ModelConfigRecord,
    ModelUsage,
    TaskStep,
    TerminalEvent,
    TerminalSession,
)
from app.shared.enums import TaskStatus
from app.shared.schemas import AssetCreate, PlanStep


def create_asset_group(session: Session, *, name: str, description: str = "") -> AssetGroup:
    row = AssetGroup(name=name, description=description)
    session.add(row)
    session.commit()
    session.refresh(row)
    return row


def list_asset_groups(session: Session) -> list[AssetGroup]:
    return list(session.exec(select(AssetGroup).order_by(AssetGroup.name)).all())


def get_asset_group(session: Session, group_id: int) -> AssetGroup | None:
    return session.get(AssetGroup, group_id)


def update_asset_group(session: Session, group_id: int, *, name: str | None = None, description: str | None = None) -> AssetGroup | None:
    row = get_asset_group(session, group_id)
    if row is None:
        return None
    if name is not None:
        row.name = name
    if description is not None:
        row.description = description
    row.updated_at = datetime.now(UTC)
    session.add(row)
    session.commit()
    session.refresh(row)
    return row


def delete_asset_group(session: Session, group_id: int) -> bool:
    row = get_asset_group(session, group_id)
    if row is None:
        return False
    for asset in session.exec(select(Asset).where(Asset.group_id == group_id)).all():
        asset.group_id = None
        asset.updated_at = datetime.now(UTC)
        session.add(asset)
    session.delete(row)
    session.commit()
    return True


def create_asset(session: Session, data: AssetCreate) -> Asset:
    payload = data.model_dump(exclude={"credential_secret"})
    payload["asset_type"] = data.asset_type.value
    payload["tags"] = ",".join(data.tags)
    asset = Asset(**payload)
    session.add(asset)
    session.commit()
    session.refresh(asset)
    return asset


def list_assets(session: Session) -> list[Asset]:
    return list(session.exec(select(Asset).order_by(desc(cast(Any, Asset.id)))).all())


def get_credential_by_asset_id(session: Session, asset_id: int) -> Credential | None:
    return session.exec(select(Credential).where(Credential.asset_id == asset_id)).first()


def create_credential(
    session: Session,
    *,
    asset_id: int,
    encryption_version: str,
    encrypted_blob: str,
) -> Credential:
    row = Credential(
        asset_id=asset_id,
        encryption_version=encryption_version,
        encrypted_blob=encrypted_blob,
    )
    session.add(row)
    session.commit()
    session.refresh(row)
    return row


def update_credential(
    session: Session,
    asset_id: int,
    *,
    encryption_version: str,
    encrypted_blob: str,
) -> Credential | None:
    row = get_credential_by_asset_id(session, asset_id)
    if row is None:
        return None
    row.encryption_version = encryption_version
    row.encrypted_blob = encrypted_blob
    row.updated_at = datetime.now(UTC)
    session.add(row)
    session.commit()
    session.refresh(row)
    return row


def get_or_create_assistant_session(
    session: Session,
    asset_id: int,
    title: str,
    active_model: str,
    *,
    terminal_session_id: int | None = None,
    model_config_id: int | None = None,
    status: str = "active",
) -> AssistantSession:
    row = session.exec(
        select(AssistantSession)
        .where(AssistantSession.asset_id == asset_id)
        .where(AssistantSession.title == title)
        .order_by(desc(cast(Any, AssistantSession.id)))
    ).first()
    if row is not None:
        row.active_model = active_model
        row.terminal_session_id = terminal_session_id
        row.model_config_id = model_config_id
        row.status = status
        row.updated_at = datetime.now(UTC)
        session.add(row)
        session.commit()
        session.refresh(row)
        return row
    row = AssistantSession(
        asset_id=asset_id,
        title=title,
        active_model=active_model,
        terminal_session_id=terminal_session_id,
        model_config_id=model_config_id,
        status=status,
    )
    session.add(row)
    session.commit()
    session.refresh(row)
    return row


def list_assistant_sessions_by_asset_id(session: Session, asset_id: int) -> list[AssistantSession]:
    return list(
        session.exec(
            select(AssistantSession)
            .where(AssistantSession.asset_id == asset_id)
            .order_by(desc(cast(Any, AssistantSession.updated_at)), desc(cast(Any, AssistantSession.id)))
        ).all()
    )


def get_assistant_session(session: Session, session_id: int) -> AssistantSession | None:
    return session.get(AssistantSession, session_id)


def create_assistant_message(session: Session, *, session_id: int, role: str, content: str) -> AssistantMessage:
    row = AssistantMessage(session_id=session_id, role=role, content=content)
    session.add(row)
    session.commit()
    session.refresh(row)
    return row


def list_assistant_messages(session: Session, session_id: int) -> list[AssistantMessage]:
    return list(
        session.exec(
            select(AssistantMessage)
            .where(AssistantMessage.session_id == session_id)
            .order_by(cast(Any, AssistantMessage.id))
        ).all()
    )


def create_agent_task(
    session: Session,
    *,
    session_id: int,
    run_id: str,
    asset_id: int,
    user_input: str,
    attached_terminal_context: str,
    task_type: str,
    risk_level: str,
    status: str,
    parent_task_id: int | None = None,
    terminal_session_id: int | None = None,
) -> AgentTask:
    row = AgentTask(
        session_id=session_id,
        parent_task_id=parent_task_id,
        run_id=run_id,
        asset_id=asset_id,
        terminal_session_id=terminal_session_id,
        user_input=user_input,
        attached_terminal_context=attached_terminal_context,
        task_type=task_type,
        risk_level=risk_level,
        status=status,
    )
    session.add(row)
    session.commit()
    session.refresh(row)
    return row


def get_agent_task_by_run_id(session: Session, run_id: str) -> AgentTask | None:
    return session.exec(select(AgentTask).where(AgentTask.run_id == run_id)).first()


def get_agent_task_by_id(session: Session, task_id: int) -> AgentTask | None:
    return session.get(AgentTask, task_id)


def update_agent_task(
    session: Session,
    task_id: int,
    *,
    status: str | None = None,
    final_summary: str | None = None,
) -> AgentTask | None:
    row = session.get(AgentTask, task_id)
    if row is None:
        return None
    if status is not None:
        row.status = status
    if final_summary is not None:
        row.final_summary = final_summary
    row.updated_at = datetime.now(UTC)
    session.add(row)
    session.commit()
    session.refresh(row)
    return row


def create_task_steps(session: Session, task_id: int, steps: list[PlanStep]) -> list[TaskStep]:
    rows = [
        TaskStep(
            task_id=task_id,
            step_order=index,
            title=step.title,
            command=step.command,
            reason=step.reason,
            working_directory=step.working_directory,
            expected_output=step.expected_output,
            risk_level=step.risk_level,
        )
        for index, step in enumerate(steps)
    ]
    for row in rows:
        session.add(row)
    session.commit()
    for row in rows:
        session.refresh(row)
    return rows


def update_task_step(
    session: Session,
    step_id: int,
    *,
    status: str | None = None,
    output: str | None = None,
    error_message: str | None = None,
    exit_code: int | None = None,
    started_at: datetime | None = None,
    finished_at: datetime | None = None,
) -> TaskStep | None:
    row = session.get(TaskStep, step_id)
    if row is None:
        return None
    if status is not None:
        row.status = status
    if output is not None:
        row.output = output
    if error_message is not None:
        row.error_message = error_message
    if exit_code is not None:
        row.exit_code = exit_code
    if started_at is not None:
        row.started_at = started_at
    if finished_at is not None:
        row.finished_at = finished_at
    session.add(row)
    session.commit()
    session.refresh(row)
    return row


def create_approval(
    session: Session,
    *,
    task_id: int,
    decision: str,
    operator: str,
    comment: str = "",
    step_id: int | None = None,
    asset_id: int | None = None,
    terminal_session_id: int | None = None,
    command: str = "",
    working_directory: str = "",
    risk_level: str = "low",
    llm_explanation: str = "",
    expected_output: str = "",
) -> Approval:
    row = Approval(
        task_id=task_id,
        step_id=step_id,
        asset_id=asset_id,
        terminal_session_id=terminal_session_id,
        command=command,
        working_directory=working_directory,
        risk_level=risk_level,
        llm_explanation=llm_explanation,
        expected_output=expected_output,
        decision=decision,
        operator=operator,
        comment=comment,
    )
    session.add(row)
    session.commit()
    session.refresh(row)
    return row


def get_latest_approval_by_task_id(session: Session, task_id: int) -> Approval | None:
    return session.exec(
        select(Approval)
        .where(Approval.task_id == task_id)
        .order_by(desc(cast(Any, Approval.created_at)), desc(cast(Any, Approval.id)))
    ).first()


def list_approvals_by_task_id(session: Session, task_id: int) -> list[Approval]:
    return list(
        session.exec(
            select(Approval)
            .where(Approval.task_id == task_id)
            .order_by(cast(Any, Approval.id))
        ).all()
    )


def list_task_steps_by_task_id(session: Session, task_id: int) -> list[TaskStep]:
    return list(
        session.exec(
            select(TaskStep)
            .where(TaskStep.task_id == task_id)
            .order_by(cast(Any, TaskStep.step_order), cast(Any, TaskStep.id))
        ).all()
    )


def get_pending_agent_task_by_session_id(session: Session, session_id: int) -> AgentTask | None:
    return session.exec(
        select(AgentTask)
        .where(AgentTask.session_id == session_id)
        .where(AgentTask.status == TaskStatus.PENDING_APPROVAL.value)
        .order_by(desc(cast(Any, AgentTask.updated_at)), desc(cast(Any, AgentTask.id)))
    ).first()


def create_terminal_session(session: Session, asset_id: int, *, status: str = "connected", last_error: str = "") -> TerminalSession:
    row = TerminalSession(asset_id=asset_id, status=status, last_error=last_error)
    session.add(row)
    session.commit()
    session.refresh(row)
    return row


def update_terminal_session(
    session: Session,
    terminal_session_id: int,
    *,
    status: str | None = None,
    last_error: str | None = None,
    ended_at: datetime | None = None,
) -> TerminalSession | None:
    row = session.get(TerminalSession, terminal_session_id)
    if row is None:
        return None
    if status is not None:
        row.status = status
    if last_error is not None:
        row.last_error = last_error
    if ended_at is not None:
        row.ended_at = ended_at
    session.add(row)
    session.commit()
    session.refresh(row)
    return row


def create_terminal_event(
    session: Session,
    terminal_session_id: int,
    event_type: str,
    metadata: Any = "",
) -> TerminalEvent:
    event_data = metadata
    if not isinstance(metadata, str):
        event_data = json.dumps(metadata, ensure_ascii=False)
    row = TerminalEvent(
        terminal_session_id=terminal_session_id,
        event_type=event_type,
        event_data=event_data,
    )
    session.add(row)
    session.commit()
    session.refresh(row)
    return row


def get_terminal_session(session: Session, terminal_session_id: int) -> TerminalSession | None:
    return session.get(TerminalSession, terminal_session_id)


def list_terminal_sessions_by_asset_id(session: Session, asset_id: int) -> list[TerminalSession]:
    return list(
        session.exec(
            select(TerminalSession)
            .where(TerminalSession.asset_id == asset_id)
            .order_by(desc(cast(Any, TerminalSession.started_at)), desc(cast(Any, TerminalSession.id)))
        ).all()
    )


def list_terminal_events_by_session_id(session: Session, terminal_session_id: int, limit: int = 20) -> list[TerminalEvent]:
    rows = list(
        session.exec(
            select(TerminalEvent)
            .where(TerminalEvent.terminal_session_id == terminal_session_id)
            .order_by(desc(cast(Any, TerminalEvent.created_at)), desc(cast(Any, TerminalEvent.id)))
        ).all()
    )
    return list(reversed(rows[:limit]))


def create_model_usage(
    session: Session,
    *,
    task_id: int,
    provider: str,
    model_name: str,
    base_url_snapshot: str,
    temperature_snapshot: float,
    max_tokens_snapshot: int,
    model_config_id: int | None = None,
) -> ModelUsage:
    row = ModelUsage(
        task_id=task_id,
        model_config_id=model_config_id,
        provider=provider,
        model_name=model_name,
        base_url_snapshot=base_url_snapshot,
        temperature_snapshot=temperature_snapshot,
        max_tokens_snapshot=max_tokens_snapshot,
    )
    session.add(row)
    session.commit()
    session.refresh(row)
    return row


def list_model_usages_by_task_id(session: Session, task_id: int) -> list[ModelUsage]:
    return list(
        session.exec(
            select(ModelUsage)
            .where(ModelUsage.task_id == task_id)
            .order_by(cast(Any, ModelUsage.id))
        ).all()
    )


def create_model_config(
    session: Session,
    *,
    name: str,
    provider: str,
    base_url: str,
    api_key_encryption_version: str,
    encrypted_api_key: str,
    model_name: str,
    is_default: bool = False,
    timeout_seconds: int = 30,
    temperature: float = 0.2,
    max_tokens: int = 1024,
    description: str = "",
) -> ModelConfigRecord:
    if is_default:
        clear_default_model_configs(session)
    row = ModelConfigRecord(
        name=name,
        provider=provider,
        base_url=base_url,
        api_key_encryption_version=api_key_encryption_version,
        encrypted_api_key=encrypted_api_key,
        model_name=model_name,
        is_default=is_default,
        timeout_seconds=timeout_seconds,
        temperature=temperature,
        max_tokens=max_tokens,
        description=description,
    )
    session.add(row)
    session.commit()
    session.refresh(row)
    return row


def list_model_configs(session: Session) -> list[ModelConfigRecord]:
    return list(session.exec(select(ModelConfigRecord).order_by(desc(cast(Any, ModelConfigRecord.id)))).all())


def list_model_names_by_provider(session: Session, provider: str) -> list[str]:
    rows = session.exec(
        select(ModelConfigRecord.model_name)
        .where(ModelConfigRecord.provider == provider)
        .order_by(desc(cast(Any, ModelConfigRecord.id)))
    ).all()
    return list(dict.fromkeys(rows))


def get_model_config(session: Session, model_config_id: int) -> ModelConfigRecord | None:
    return session.get(ModelConfigRecord, model_config_id)


def get_default_model_config(session: Session) -> ModelConfigRecord | None:
    return session.exec(select(ModelConfigRecord).where(ModelConfigRecord.is_default == True)).first()


def clear_default_model_configs(session: Session) -> None:
    rows = session.exec(select(ModelConfigRecord).where(ModelConfigRecord.is_default == True)).all()
    for row in rows:
        row.is_default = False
        row.updated_at = datetime.now(UTC)
        session.add(row)
    session.commit()


def set_default_model_config(session: Session, model_config_id: int) -> ModelConfigRecord | None:
    row = get_model_config(session, model_config_id)
    if row is None:
        return None
    clear_default_model_configs(session)
    row.is_default = True
    row.updated_at = datetime.now(UTC)
    session.add(row)
    session.commit()
    session.refresh(row)
    return row


def update_model_config(session: Session, model_config_id: int, **updates: Any) -> ModelConfigRecord | None:
    row = get_model_config(session, model_config_id)
    if row is None:
        return None
    if updates.get("is_default") is True:
        clear_default_model_configs(session)
    for key, value in updates.items():
        if hasattr(row, key) and value is not None:
            setattr(row, key, value)
    row.updated_at = datetime.now(UTC)
    session.add(row)
    session.commit()
    session.refresh(row)
    return row


def delete_model_config(session: Session, model_config_id: int) -> bool:
    row = get_model_config(session, model_config_id)
    if row is None:
        return False
    session.delete(row)
    session.commit()
    return True


def create_command_execution(session: Session, **payload: Any) -> CommandExecution:
    row = CommandExecution(**payload)
    session.add(row)
    session.commit()
    session.refresh(row)
    return row


def update_command_execution(session: Session, command_execution_id: int, **updates: Any) -> CommandExecution | None:
    row = session.get(CommandExecution, command_execution_id)
    if row is None:
        return None
    for key, value in updates.items():
        if hasattr(row, key) and value is not None:
            setattr(row, key, value)
    session.add(row)
    session.commit()
    session.refresh(row)
    return row


def list_command_executions_by_task_id(session: Session, task_id: int) -> list[CommandExecution]:
    return list(
        session.exec(
            select(CommandExecution)
            .where(CommandExecution.task_id == task_id)
            .order_by(cast(Any, CommandExecution.id))
        ).all()
    )


def create_auto_approval_rule(session: Session, **payload: Any) -> AutoApprovalRule:
    row = AutoApprovalRule(**payload)
    session.add(row)
    session.commit()
    session.refresh(row)
    return row


def list_auto_approval_rules_by_session_id(session: Session, session_id: int) -> list[AutoApprovalRule]:
    return list(
        session.exec(
            select(AutoApprovalRule)
            .where(AutoApprovalRule.session_id == session_id)
            .order_by(cast(Any, AutoApprovalRule.id))
        ).all()
    )


def update_auto_approval_rule(session: Session, rule_id: int, **updates: Any) -> AutoApprovalRule | None:
    row = session.get(AutoApprovalRule, rule_id)
    if row is None:
        return None
    for key, value in updates.items():
        if hasattr(row, key) and value is not None:
            setattr(row, key, value)
    row.updated_at = datetime.now(UTC)
    session.add(row)
    session.commit()
    session.refresh(row)
    return row


def delete_auto_approval_rule(session: Session, rule_id: int) -> bool:
    row = session.get(AutoApprovalRule, rule_id)
    if row is None:
        return False
    session.delete(row)
    session.commit()
    return True


def create_auto_approval_match(session: Session, **payload: Any) -> AutoApprovalMatch:
    row = AutoApprovalMatch(**payload)
    session.add(row)
    session.commit()
    session.refresh(row)
    return row


def create_audit_log(session: Session, **payload: Any) -> AuditLog:
    row = AuditLog(**payload)
    session.add(row)
    session.commit()
    session.refresh(row)
    return row


def list_audit_logs(session: Session, limit: int = 100) -> list[AuditLog]:
    return list(
        session.exec(
            select(AuditLog)
            .order_by(desc(cast(Any, AuditLog.created_at)), desc(cast(Any, AuditLog.id)))
            .limit(limit)
        ).all()
    )


def delete_asset_graph(session: Session, asset_id: int) -> bool:
    asset = session.get(Asset, asset_id)
    if asset is None:
        return False

    sessions = list(session.exec(select(AssistantSession).where(AssistantSession.asset_id == asset_id)).all())
    session_ids = [row.id for row in sessions if row.id is not None]
    tasks = list(session.exec(select(AgentTask).where(AgentTask.asset_id == asset_id)).all())
    task_ids = [row.id for row in tasks if row.id is not None]
    terminal_sessions = list(session.exec(select(TerminalSession).where(TerminalSession.asset_id == asset_id)).all())
    terminal_session_ids = [row.id for row in terminal_sessions if row.id is not None]

    for task_id in task_ids:
        for row in session.exec(select(AutoApprovalMatch).where(AutoApprovalMatch.task_id == task_id)).all():
            session.delete(row)
        for row in session.exec(select(CommandExecution).where(CommandExecution.task_id == task_id)).all():
            session.delete(row)
        for row in session.exec(select(Approval).where(Approval.task_id == task_id)).all():
            session.delete(row)
        for row in session.exec(select(ModelUsage).where(ModelUsage.task_id == task_id)).all():
            session.delete(row)
        for row in session.exec(select(TaskStep).where(TaskStep.task_id == task_id)).all():
            session.delete(row)

    for session_id in session_ids:
        for row in session.exec(select(AutoApprovalRule).where(AutoApprovalRule.session_id == session_id)).all():
            session.delete(row)
        for row in session.exec(select(AssistantMessage).where(AssistantMessage.session_id == session_id)).all():
            session.delete(row)

    for terminal_session_id in terminal_session_ids:
        for row in session.exec(select(TerminalEvent).where(TerminalEvent.terminal_session_id == terminal_session_id)).all():
            session.delete(row)

    for row in tasks:
        session.delete(row)
    for row in sessions:
        session.delete(row)
    for row in terminal_sessions:
        session.delete(row)
    for row in session.exec(select(Credential).where(Credential.asset_id == asset_id)).all():
        session.delete(row)

    session.delete(asset)
    session.commit()
    return True
