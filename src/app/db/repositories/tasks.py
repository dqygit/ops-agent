from datetime import UTC, datetime
from typing import Any, cast

from sqlalchemy import desc
from sqlmodel import Session, select

from app.db.models import AgentTask, Approval, AutoApprovalMatch, AutoApprovalRule, CommandExecution, ModelUsage, TaskStep
from app.shared.enums import TaskStatus
from app.shared.schemas import PlanStep


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
