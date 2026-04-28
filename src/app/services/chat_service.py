from app.shared.enums import TaskStatus
from app.shared.schemas import AgentTaskSummary, ApprovalView, PlanStep


class ChatService:
    def __init__(self, runtime, session_store=None, message_service=None, approval_store=None):
        self._runtime = runtime
        self._session_store = session_store
        self._message_service = message_service
        self._approval_store = approval_store
        self._next_run_id = 1

    def start_agent_run(
        self,
        *,
        conversation_id: str,
        user_message: str,
        asset,
        asset_type,
        model_name: str,
        terminal_context=None,
        recent_messages=None,
    ):
        run_id = f"run-{self._next_run_id}"
        self._next_run_id += 1
        session_id = 0
        asset_id = getattr(asset, "id", None)
        if asset_id is None and isinstance(asset, dict):
            asset_id = asset.get("id")
        history_messages = recent_messages or []
        if self._session_store is not None and asset_id is not None:
            assistant_session = self._session_store.get_or_create(
                asset_id=asset_id,
                conversation_id=conversation_id,
                model_name=model_name,
            )
            session_id = assistant_session.id or 0
            if self._message_service is not None and session_id:
                history_messages = self._message_service.list_recent_messages(session_id=session_id)
                self._message_service.append_message(session_id=session_id, role="user", content=user_message)
                history_messages = [*history_messages, {"role": "user", "content": user_message}]
        if hasattr(self._runtime, "set_active_model_name"):
            self._runtime.set_active_model_name(model_name)
        result = self._runtime.start_run(
            conversation_id=conversation_id,
            run_id=run_id,
            user_message=user_message,
            asset_type=asset_type,
            asset_id=asset_id or 0,
            session_id=session_id,
            model_name=model_name,
            terminal_context=terminal_context,
            recent_messages=history_messages,
        )
        assistant_message = result.get("assistant_message")
        if self._message_service is not None and session_id and assistant_message:
            self._message_service.append_message(session_id=session_id, role="assistant", content=assistant_message)
        return result

    def resume_agent_run(self, *, run_id: str, approved: bool):
        result = self._runtime.resume_run(run_id=run_id, approved=approved)
        assistant_message = result.get("assistant_message")
        session_id = result.get("session_id", 0)
        if self._message_service is not None and session_id and assistant_message:
            self._message_service.append_message(session_id=session_id, role="assistant", content=assistant_message)
        return result

    def list_assistant_sessions(self, *, asset_id: int):
        if self._session_store is None:
            return []
        return self._session_store.list_by_asset_id(asset_id)

    def list_assistant_messages(self, *, session_id: int):
        if self._message_service is None:
            return []
        return self._message_service.list_recent_messages(session_id=session_id)

    def get_pending_approval(self, *, session_id: int) -> ApprovalView | None:
        if self._approval_store is None:
            return None
        task = self._approval_store.get_pending_task_by_session_id(session_id)
        if task is None:
            return None
        steps = self._approval_store.list_steps_by_task_id(task.id or 0)
        latest_approval = self._approval_store.get_latest_approval_by_task_id(task.id or 0)
        return ApprovalView(
            task_id=task.id or 0,
            run_id=task.run_id,
            session_id=task.session_id,
            status=task.status,
            message="Approve this execution plan?",
            steps=[
                PlanStep(
                    title=step.title,
                    command=step.command,
                    reason=step.reason,
                    risk_level=step.risk_level,
                )
                for step in steps
            ],
            latest_decision=latest_approval.decision if latest_approval is not None else None,
        )

    def resume_pending_approval(self, *, run_id: str, approved: bool):
        return self.resume_agent_run(run_id=run_id, approved=approved)


def create_pending_task(asset_type, user_input: str, planner, active_model_name: str, terminal_context=None) -> AgentTaskSummary:
    plan = planner(asset_type, user_input, terminal_context=terminal_context)
    return AgentTaskSummary(
        task_id=1,
        status=TaskStatus.PENDING_APPROVAL,
        asset_type=asset_type,
        model_name=active_model_name,
        steps=plan,
    )
