import { requestJson, requestVoid } from './client'

type TerminalSessionResponse = {
  terminal_id: string | null
  channel: string | null
  error: string
}

export async function createTerminalSession(assetId: number): Promise<TerminalSessionResponse> {
  return requestJson<TerminalSessionResponse>('/api/terminal/sessions', {
    method: 'POST',
    body: JSON.stringify({ asset_id: assetId }),
  })
}

export async function closeTerminalSession(terminalSessionId: string): Promise<void> {
  return requestVoid(`/api/terminal/sessions/${terminalSessionId}`, {
    method: 'DELETE',
  })
}

export async function reconnectTerminalSession(terminalSessionId: string, assetId: number): Promise<TerminalSessionResponse> {
  return requestJson<TerminalSessionResponse>(`/api/terminal/sessions/${terminalSessionId}/reconnect`, {
    method: 'POST',
    body: JSON.stringify({ asset_id: assetId }),
  })
}
