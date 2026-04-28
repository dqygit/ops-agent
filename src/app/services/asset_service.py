import os
from datetime import UTC, datetime

from sqlmodel import select

from app.db.models import Asset
from app.db.repositories import (
    create_asset,
    create_credential,
    get_credential_by_asset_id,
    list_assets,
    update_credential,
)
from app.services.credential_service import CredentialService


def _build_credential_service():
    secret_key = os.environ.get("OPS_AGENT_SECRET_KEY", "dev-secret-key")
    return CredentialService(secret_key=secret_key)


def create_asset_record(session, asset_data):
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

    session.delete(asset)
    session.commit()
    return True
