import { requestJson, requestVoid } from './client'

type TerminalSessionResponse = {
  terminal_session_id: number | null
  channel: string | null
  error: string
}

export async function createTerminalSession(assetId: number): Promise<TerminalSessionResponse> {
  return requestJson<TerminalSessionResponse>('/api/terminal/sessions', {
    method: 'POST',
    body: JSON.stringify({ asset_id: assetId }),
  })
}

export async function closeTerminalSession(terminalSessionId: number): Promise<void> {
  return requestVoid(`/api/terminal/sessions/${terminalSessionId}`, {
    method: 'DELETE',
  })
}
