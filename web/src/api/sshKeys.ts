import { requestJson, requestVoid } from './client'
import type { SSHKey } from '../types/ops'

export type SSHKeyPayload = {
  name: string
  public_key: string
  private_key?: string
  passphrase?: string
}

type SSHKeyDto = {
  id: number
  name: string
  public_key: string
  has_passphrase: boolean
  created_at: string
  updated_at: string
}

export function mapSSHKey(dto: SSHKeyDto): SSHKey {
  return {
    id: dto.id,
    name: dto.name,
    publicKey: dto.public_key,
    hasPassphrase: dto.has_passphrase,
    createdAt: dto.created_at,
    updatedAt: dto.updated_at,
  }
}

export async function getSSHKeys(): Promise<SSHKey[]> {
  const items = await requestJson<SSHKeyDto[]>('/api/ssh-keys')
  return items.map(mapSSHKey)
}

export async function createSSHKey(payload: SSHKeyPayload): Promise<SSHKey> {
  const item = await requestJson<SSHKeyDto>('/api/ssh-keys', {
    method: 'POST',
    body: JSON.stringify(payload),
  })
  return mapSSHKey(item)
}

export async function updateSSHKey(sshKeyId: number, payload: SSHKeyPayload): Promise<SSHKey> {
  const item = await requestJson<SSHKeyDto>(`/api/ssh-keys/${sshKeyId}`, {
    method: 'PUT',
    body: JSON.stringify(payload),
  })
  return mapSSHKey(item)
}

export async function deleteSSHKey(sshKeyId: number): Promise<void> {
  await requestVoid(`/api/ssh-keys/${sshKeyId}`, {
    method: 'DELETE',
  })
}
