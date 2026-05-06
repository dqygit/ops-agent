from fastapi import APIRouter, Depends, HTTPException, Response
from sqlmodel import Session

from app.api.schemas import SSHKeyView
from app.db.repositories.ssh_keys import count_assets_by_ssh_key_id
from app.db.session import get_session
from app.services.ssh_key_service import create_ssh_key_record, delete_ssh_key_record, get_ssh_key_record, list_ssh_key_records, update_ssh_key_record
from app.shared.schemas import SSHKeyCreate, SSHKeyUpdate

router = APIRouter()


def to_ssh_key_view(record) -> SSHKeyView:
    return SSHKeyView(
        id=record.id or 0,
        name=record.name,
        public_key=record.public_key,
        has_passphrase=bool(record.encrypted_passphrase),
        created_at=record.created_at,
        updated_at=record.updated_at,
    )


@router.get("/api/ssh-keys")
def list_ssh_keys(session: Session = Depends(get_session)) -> list[SSHKeyView]:
    return [to_ssh_key_view(record) for record in list_ssh_key_records(session)]


@router.get("/api/ssh-keys/{ssh_key_id}")
def get_ssh_key(ssh_key_id: int, session: Session = Depends(get_session)) -> SSHKeyView:
    record = get_ssh_key_record(session, ssh_key_id)
    if record is None:
        raise HTTPException(status_code=404, detail="SSH key not found")
    return to_ssh_key_view(record)


@router.post("/api/ssh-keys", status_code=201)
def create_ssh_key(payload: SSHKeyCreate, session: Session = Depends(get_session)) -> SSHKeyView:
    return to_ssh_key_view(create_ssh_key_record(session, payload))


@router.put("/api/ssh-keys/{ssh_key_id}")
def update_ssh_key(ssh_key_id: int, payload: SSHKeyUpdate, session: Session = Depends(get_session)) -> SSHKeyView:
    record = update_ssh_key_record(session, ssh_key_id, payload)
    if record is None:
        raise HTTPException(status_code=404, detail="SSH key not found")
    return to_ssh_key_view(record)


@router.delete("/api/ssh-keys/{ssh_key_id}", status_code=204)
def delete_ssh_key(ssh_key_id: int, session: Session = Depends(get_session)) -> Response:
    if get_ssh_key_record(session, ssh_key_id) is None:
        raise HTTPException(status_code=404, detail="SSH key not found")
    if count_assets_by_ssh_key_id(session, ssh_key_id) > 0:
        raise HTTPException(status_code=409, detail="SSH key is referenced by assets")
    delete_ssh_key_record(session, ssh_key_id)
    return Response(status_code=204)
