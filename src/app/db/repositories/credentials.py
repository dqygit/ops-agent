from datetime import UTC, datetime

from sqlmodel import Session, select

from app.db.models import Credential


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
