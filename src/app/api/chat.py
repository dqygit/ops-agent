from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session

from app.api.dependencies import get_chat_service
from app.api.schemas import ApprovalRecordView, AssistantMessageView, ChatApprovalRequest, ChatRunRequest, ChatRunResponse, ChatSessionView, CommandExecutionView, PendingApprovalStepView, PendingApprovalView, TaskDetailView, TaskStepRecordView
from app.db.repositories import get_agent_task_by_id, get_agent_task_by_run_id, list_approvals_by_task_id, list_command_executions_by_task_id, list_task_steps_by_task_id, update_agent_task
from app.db.session import get_session
from app.services.asset_service import get_asset_record
from app.services.assistant_session_service import get_assistant_session_record
from app.services.chat_service import ChatService
from app.services.message_service import AssistantMessageService
from app.shared.enums import AssetType

router = APIRouter()


def to_task_detail_view(task, session: Session) -> TaskDetailView:
    steps = list_task_steps_by_task_id(session, task.id or 0)
    approvals = list_approvals_by_task_id(session, task.id or 0)
    executions = list_command_executions_by_task_id(session, task.id or 0)
    return TaskDetailView(
        id=task.id or 0,
        session_id=task.session_id,
        parent_task_id=task.parent_task_id,
        run_id=task.run_id,
        asset_id=task.asset_id,
        terminal_session_id=task.terminal_session_id,
        user_input=task.user_input,
        attached_terminal_context=task.attached_terminal_context,
        task_type=task.task_type,
        risk_level=task.risk_level,
        status=task.status,
        final_summary=task.final_summary,
        created_at=task.created_at,
        updated_at=task.updated_at,
        steps=[
            TaskStepRecordView(
                id=step.id or 0,
                task_id=step.task_id,
                step_order=step.step_order,
                title=step.title,
                command=step.command,
                reason=step.reason,
                working_directory=step.working_directory,
                expected_output=step.expected_output,
                risk_level=step.risk_level,
                status=step.status,
                output=step.output,
                error_message=step.error_message,
                exit_code=step.exit_code,
                started_at=step.started_at,
                finished_at=step.finished_at,
            )
            for step in steps
        ],
        approvals=[
            ApprovalRecordView(
                id=approval.id or 0,
                task_id=approval.task_id,
                step_id=approval.step_id,
                asset_id=approval.asset_id,
                terminal_session_id=approval.terminal_session_id,
                command=approval.command,
                working_directory=approval.working_directory,
                risk_level=approval.risk_level,
                llm_explanation=approval.llm_explanation,
                expected_output=approval.expected_output,
                decision=approval.decision,
                operator=approval.operator,
                comment=approval.comment,
                created_at=approval.created_at,
            )
            for approval in approvals
        ],
        command_executions=[
            CommandExecutionView(
                id=execution.id or 0,
                task_id=execution.task_id,
                step_id=execution.step_id,
                asset_id=execution.asset_id,
                terminal_session_id=execution.terminal_session_id,
                command=execution.command,
                status=execution.status,
                approval_id=execution.approval_id,
                working_directory=execution.working_directory,
                output=execution.output,
                error_output=execution.error_output,
                exit_code=execution.exit_code,
                started_at=execution.started_at,
                finished_at=execution.finished_at,
                created_at=execution.created_at,
            )
            for execution in executions
        ],
    )


@router.get("/api/chat/sessions/{session_id}")
def get_chat_session(session_id: int, session: Session = Depends(get_session)) -> ChatSessionView:
    assistant_session = get_assistant_session_record(session, session_id)
    if assistant_session is None:
        raise HTTPException(status_code=404, detail="Chat session not found")
    message_service = AssistantMessageService(lambda: session)
    return ChatSessionView(
        session_id=assistant_session.id or 0,
        asset_id=assistant_session.asset_id,
        model_name=assistant_session.active_model,
        messages=[
            AssistantMessageView(role=message["role"], content=message["content"])
            for message in message_service.list_recent_messages(session_id=session_id)
        ],
    )


@router.get("/api/chat/sessions/{session_id}/pending-approval")
def get_pending_approval(
    session_id: int,
    chat_service: ChatService = Depends(get_chat_service),
) -> PendingApprovalView | None:
    approval = chat_service.get_pending_approval(session_id=session_id)
    if approval is None:
        return None
    return PendingApprovalView(
        task_id=approval.task_id,
        run_id=approval.run_id,
        session_id=approval.session_id,
        status=approval.status,
        message=approval.message,
        latest_decision=approval.latest_decision,
        steps=[
            PendingApprovalStepView(
                title=step.title,
                command=step.command,
                reason=step.reason,
                risk_level=step.risk_level,
                working_directory=step.working_directory,
                expected_output=step.expected_output,
            )
            for step in approval.steps
        ],
    )


@router.post("/api/chat/runs")
def create_chat_run(
    payload: ChatRunRequest,
    session: Session = Depends(get_session),
    chat_service: ChatService = Depends(get_chat_service),
) -> ChatRunResponse:
    asset = get_asset_record(session, payload.asset_id)
    if asset is None:
        raise HTTPException(status_code=404, detail="Asset not found")
    result = chat_service.start_agent_run(
        conversation_id=payload.conversation_id,
        user_message=payload.user_message,
        asset=asset,
        asset_type=AssetType(asset.asset_type),
        model_name=payload.model_name,
        terminal_context=payload.terminal_context,
        recent_messages=payload.recent_messages,
    )
    return ChatRunResponse(
        run_id=result.get("run_id", ""),
        session_id=result.get("session_id", 0),
        ui_events=result.get("ui_events", []),
    )


@router.post("/api/chat/runs/{run_id}/approval")
def approve_chat_run(
    run_id: str,
    payload: ChatApprovalRequest,
    chat_service: ChatService = Depends(get_chat_service),
) -> ChatRunResponse:
    result = chat_service.resume_pending_approval(run_id=run_id, approved=payload.approved)
    return ChatRunResponse(
        run_id=result.get("run_id", run_id),
        session_id=result.get("session_id", 0),
        ui_events=result.get("ui_events", []),
    )


@router.get("/api/chat/runs/{run_id}")
def get_chat_run(run_id: str, session: Session = Depends(get_session)) -> TaskDetailView:
    task = get_agent_task_by_run_id(session, run_id)
    if task is None:
        raise HTTPException(status_code=404, detail="Run not found")
    return to_task_detail_view(task, session)


@router.get("/api/tasks/{task_id}")
def get_task_detail(task_id: int, session: Session = Depends(get_session)) -> TaskDetailView:
    task = get_agent_task_by_id(session, task_id)
    if task is None:
        raise HTTPException(status_code=404, detail="Task not found")
    return to_task_detail_view(task, session)


@router.post("/api/tasks/{task_id}/stop")
def stop_task(task_id: int, session: Session = Depends(get_session)) -> TaskDetailView:
    task = update_agent_task(session, task_id, status="stopped")
    if task is None:
        raise HTTPException(status_code=404, detail="Task not found")
    return to_task_detail_view(task, session)
