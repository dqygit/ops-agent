from datetime import UTC, datetime

from sqlmodel import Session, col, select

from app.db.models import Asset, SSHKey


def list_ssh_keys(session: Session) -> list[SSHKey]:
    return list(session.exec(select(SSHKey).order_by(col(SSHKey.updated_at).desc())).all())


def get_ssh_key(session: Session, ssh_key_id: int) -> SSHKey | None:
    return session.get(SSHKey, ssh_key_id)


def create_ssh_key(
    session: Session,
    *,
    name: str,
    public_key: str,
    private_key_encryption_version: str,
    encrypted_private_key: str,
    passphrase_encryption_version: str | None,
    encrypted_passphrase: str | None,
) -> SSHKey:
    row = SSHKey(
        name=name,
        public_key=public_key,
        private_key_encryption_version=private_key_encryption_version,
        encrypted_private_key=encrypted_private_key,
        passphrase_encryption_version=passphrase_encryption_version,
        encrypted_passphrase=encrypted_passphrase,
    )
    session.add(row)
    session.commit()
    session.refresh(row)
    return row


def update_ssh_key(session: Session, ssh_key_id: int, **updates) -> SSHKey | None:
    row = get_ssh_key(session, ssh_key_id)
    if row is None:
        return None
    for key, value in updates.items():
        setattr(row, key, value)
    row.updated_at = datetime.now(UTC)
    session.add(row)
    session.commit()
    session.refresh(row)
    return row


def delete_ssh_key(session: Session, ssh_key_id: int) -> bool:
    row = get_ssh_key(session, ssh_key_id)
    if row is None:
        return False
    session.delete(row)
    session.commit()
    return True


def count_assets_by_ssh_key_id(session: Session, ssh_key_id: int) -> int:
    return len(session.exec(select(Asset).where(Asset.ssh_key_id == ssh_key_id)).all())
