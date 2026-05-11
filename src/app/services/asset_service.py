import json
from datetime import UTC, datetime

from sqlmodel import select

from app.db.models import Asset, AssetGroup
from app.db.repositories.assets import create_asset, create_asset_group, delete_asset_graph, delete_asset_group, get_asset_group, list_asset_groups, list_assets, update_asset_group
from app.db.repositories.audit import create_audit_log
from app.db.repositories.credentials import create_credential, get_credential_by_asset_id, update_credential
from app.db.repositories.ssh_keys import get_ssh_key
from app.services.credential_service import CredentialService
from app.services.secret_key import get_ops_agent_secret_key


class GroupNotFoundError(ValueError):
    pass


class SSHKeyNotFoundError(ValueError):
    pass


def _build_credential_service():
    return CredentialService(secret_key=get_ops_agent_secret_key())


def _ensure_group_exists(session, group_id):
    if group_id is not None and get_asset_group(session, group_id) is None:
        raise GroupNotFoundError("Group not found")


def _ensure_ssh_key_exists(session, ssh_key_id):
    if ssh_key_id is not None and get_ssh_key(session, ssh_key_id) is None:
        raise SSHKeyNotFoundError("SSH key not found")


def create_asset_group_record(session, payload):
    return create_asset_group(session, name=payload.name, description=payload.description)


def ensure_default_asset_group(session):
    existing_group = session.exec(select(AssetGroup).where(AssetGroup.name == "default")).first()
    if existing_group is not None:
        return existing_group
    return create_asset_group(session, name="default", description="Default Group")


def list_asset_group_records(session):
    return list_asset_groups(session)


def get_asset_group_record(session, group_id):
    return get_asset_group(session, group_id)


def update_asset_group_record(session, group_id, payload):
    return update_asset_group(session, group_id, name=payload.name, description=payload.description)


def delete_asset_group_record(session, group_id):
    return delete_asset_group(session, group_id)


def create_asset_record(session, asset_data):
    _ensure_group_exists(session, asset_data.group_id)
    _ensure_ssh_key_exists(session, asset_data.ssh_key_id)
    asset = create_asset(session, asset_data)
    asset_id = asset.id
    if asset_id is None:
        raise ValueError("asset id is required")
    credential_secret = asset_data.credential_secret
    if credential_secret is None:
        return asset
    encrypted_blob = _build_credential_service().encrypt_secret(credential_secret.get_secret_value())
    create_credential(
        session,
        asset_id=asset_id,
        encryption_version=CredentialService.encryption_version,
        encrypted_blob=encrypted_blob,
    )
    return asset


def get_asset_record(session, asset_id):
    return session.exec(select(Asset).where(Asset.id == asset_id)).first()


def list_asset_records(session):
    return list_assets(session)


def get_asset_credential_record(session, asset_id):
    return get_credential_by_asset_id(session, asset_id)


def update_asset_record(session, asset_id, asset_data):
    asset = get_asset_record(session, asset_id)
    if asset is None:
        return None
    _ensure_group_exists(session, asset_data.group_id)
    _ensure_ssh_key_exists(session, asset_data.ssh_key_id)

    payload = asset_data.model_dump(exclude={"credential_secret"})
    payload["asset_type"] = asset_data.asset_type.value
    payload["tags"] = ",".join(asset_data.tags)

    for key, value in payload.items():
        setattr(asset, key, value)
    asset.updated_at = datetime.now(UTC)

    session.add(asset)
    session.commit()
    session.refresh(asset)

    credential_secret = asset_data.credential_secret
    if credential_secret is None:
        return asset
    encrypted_blob = _build_credential_service().encrypt_secret(credential_secret.get_secret_value())
    updated_credential = update_credential(
        session,
        asset_id,
        encryption_version=CredentialService.encryption_version,
        encrypted_blob=encrypted_blob,
    )
    if updated_credential is None:
        create_credential(
            session,
            asset_id=asset_id,
            encryption_version=CredentialService.encryption_version,
            encrypted_blob=encrypted_blob,
        )
    return asset


def delete_asset_record(session, asset_id):
    asset = get_asset_record(session, asset_id)
    if asset is None:
        return False

    snapshot = {
        "id": asset.id,
        "name": asset.name,
        "asset_type": asset.asset_type,
        "host": asset.host,
        "port": asset.port,
        "username": asset.username,
        "auth_type": asset.auth_type,
        "tags": asset.tags,
        "vendor": asset.vendor,
        "description": asset.description,
    }
    deleted = delete_asset_graph(session, asset_id)
    if deleted:
        create_audit_log(
            session,
            action="asset.deleted",
            entity_type="asset",
            entity_id=asset_id,
            asset_id=asset_id,
            details=json.dumps(snapshot, ensure_ascii=False),
        )
    return deleted
