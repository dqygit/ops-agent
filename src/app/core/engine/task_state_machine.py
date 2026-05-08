from __future__ import annotations

from sqlmodel import Session

from app.db.repositories.tasks import update_agent_task
from app.shared.enums import TaskStatus


class TaskStateMachine:
    def transition(self, session: Session, task_id: int, to_status: TaskStatus, *, final_summary: str | None = None):
        return update_agent_task(
            session,
            task_id,
            status=to_status.value,
            final_summary=final_summary,
        )

    def mark_pending_approval(self, session: Session, task_id: int, *, final_summary: str | None = None):
        return self.transition(session, task_id, TaskStatus.PENDING_APPROVAL, final_summary=final_summary)

    def mark_running(self, session: Session, task_id: int, *, final_summary: str | None = None):
        return self.transition(session, task_id, TaskStatus.RUNNING, final_summary=final_summary)

    def mark_completed(self, session: Session, task_id: int, summary: str):
        return self.transition(session, task_id, TaskStatus.COMPLETED, final_summary=summary)

    def mark_failed(self, session: Session, task_id: int, summary: str):
        return self.transition(session, task_id, TaskStatus.FAILED, final_summary=summary)
