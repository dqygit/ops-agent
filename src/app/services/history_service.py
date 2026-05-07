from typing import Any, cast

from sqlalchemy import desc
from sqlmodel import Session, select

from app.db.models import AgentTask, ModelUsage


def list_recent_tasks(session: Session) -> list[AgentTask]:
    return list(session.exec(select(AgentTask).order_by(desc(cast(Any, AgentTask.id)))).all())


def serialize_model_usages(usages: list[ModelUsage]) -> list[dict[str, object]]:
    return [
        {
            "id": usage.id or 0,
            "task_id": usage.task_id,
            "provider": usage.provider,
            "model_name": usage.model_name,
            "base_url_snapshot": usage.base_url_snapshot,
            "temperature_snapshot": usage.temperature_snapshot,
            "max_tokens_snapshot": usage.max_tokens_snapshot,
            "created_at": usage.created_at,
        }
        for usage in usages
    ]


def split_active_and_completed_tasks(tasks: list[dict]):
    active = [task for task in tasks if task["status"] in {"pending_approval", "running"}]
    history = [task for task in tasks if task["status"] not in {"pending_approval", "running"}]
    return active, history
