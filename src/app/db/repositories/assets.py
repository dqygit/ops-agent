from datetime import UTC, datetime
from typing import Any, cast

from sqlalchemy import desc
from sqlmodel import Session, select

from app.db.models import AgentTask, Asset, AssetGroup, Approval, AutoApprovalMatch, AutoApprovalRule, CommandExecution, Credential, ModelUsage, TaskStep
from app.shared.schemas import AssetCreate


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


def delete_asset_graph(session: Session, asset_id: int) -> bool:
    asset = session.get(Asset, asset_id)
    if asset is None:
        return False

    tasks = list(session.exec(select(AgentTask).where(AgentTask.asset_id == asset_id)).all())
    task_ids = [row.id for row in tasks if row.id is not None]

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

    for row in tasks:
        session.delete(row)
    for row in session.exec(select(Credential).where(Credential.asset_id == asset_id)).all():
        session.delete(row)

    session.delete(asset)
    session.commit()
    return True
