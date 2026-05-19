import { requestJson, requestVoid } from './client'
import { mapTimestamps } from './mappers'
import type { MCPApprovalPolicy, MCPConnectionTestResult, MCPServer, MCPTool, MCPTransport } from '../types/ops'

export type MCPServerPayload = {
  name: string
  transport: MCPTransport
  command: string
  args: string[]
  env: Record<string, string>
  url: string
  headers: Record<string, string>
  timeoutSeconds: number
}

export type MCPServerUpdatePayload = Partial<MCPServerPayload>

export type MCPToolUpdatePayload = {
  enabled?: boolean
  approvalPolicy?: MCPApprovalPolicy
}

type MCPTransportDto = 'stdio' | 'http_sse'
type MCPConnectionStatusDto = 'untested' | 'ok' | 'failed'
type MCPDiscoveryStatusDto = 'never' | 'ok' | 'failed'
type MCPApprovalPolicyDto = 'allow' | 'ask' | 'deny'

type MCPToolDto = {
  id: string
  original_name: string
  exposed_name: string
  description: string
  input_schema: Record<string, unknown>
  approval_policy: MCPApprovalPolicyDto
  enabled: boolean
  discovered: boolean
  last_discovered_at: string | null
  created_at: string | null
  updated_at: string | null
}

type MCPServerDto = {
  id: string
  name: string
  slug: string
  enabled: boolean
  transport: MCPTransportDto
  command: string
  args: string[]
  env: Record<string, string>
  url: string
  headers: Record<string, string>
  timeout_seconds: number
  connection_status: MCPConnectionStatusDto
  discovery_status: MCPDiscoveryStatusDto
  last_error: string
  last_discovered_at: string | null
  last_refresh_succeeded: boolean
  tools: MCPToolDto[]
  created_at: string | null
  updated_at: string | null
}

type MCPServerRequest = {
  name: string
  transport: MCPTransportDto
  command: string
  args: string[]
  env: Record<string, string>
  url: string
  headers: Record<string, string>
  timeout_seconds: number
}

type MCPServerUpdateRequest = Partial<MCPServerRequest>

type MCPServerEnabledRequest = {
  enabled: boolean
}

type MCPToolUpdateRequest = {
  enabled?: boolean
  approval_policy?: MCPApprovalPolicyDto
}

type MCPConnectionTestResultDto = {
  success: boolean
  message: string
  server: MCPServerDto | null
}

type DeleteResultDto = {
  success: boolean
}

function toTransportDto(transport: MCPTransport): MCPTransportDto {
  return transport === 'httpSse' ? 'http_sse' : 'stdio'
}

function fromTransportDto(transport: MCPTransportDto): MCPTransport {
  return transport === 'http_sse' ? 'httpSse' : 'stdio'
}

function toServerRequest(payload: MCPServerPayload): MCPServerRequest {
  return {
    name: payload.name,
    transport: toTransportDto(payload.transport),
    command: payload.command,
    args: payload.args,
    env: payload.env,
    url: payload.url,
    headers: payload.headers,
    timeout_seconds: payload.timeoutSeconds,
  }
}

function toServerUpdateRequest(payload: MCPServerUpdatePayload): MCPServerUpdateRequest {
  return {
    ...(payload.name !== undefined ? { name: payload.name } : {}),
    ...(payload.transport !== undefined ? { transport: toTransportDto(payload.transport) } : {}),
    ...(payload.command !== undefined ? { command: payload.command } : {}),
    ...(payload.args !== undefined ? { args: payload.args } : {}),
    ...(payload.env !== undefined ? { env: payload.env } : {}),
    ...(payload.url !== undefined ? { url: payload.url } : {}),
    ...(payload.headers !== undefined ? { headers: payload.headers } : {}),
    ...(payload.timeoutSeconds !== undefined ? { timeout_seconds: payload.timeoutSeconds } : {}),
  }
}

function toToolUpdateRequest(payload: MCPToolUpdatePayload): MCPToolUpdateRequest {
  return {
    ...(payload.enabled !== undefined ? { enabled: payload.enabled } : {}),
    ...(payload.approvalPolicy !== undefined ? { approval_policy: payload.approvalPolicy } : {}),
  }
}

export function mapMCPTool(dto: MCPToolDto): MCPTool {
  return {
    id: dto.id,
    originalName: dto.original_name,
    exposedName: dto.exposed_name,
    description: dto.description,
    inputSchema: dto.input_schema,
    approvalPolicy: dto.approval_policy,
    enabled: dto.enabled,
    discovered: dto.discovered,
    lastDiscoveredAt: dto.last_discovered_at,
    ...mapTimestamps(dto),
  }
}

export function mapMCPServer(dto: MCPServerDto): MCPServer {
  return {
    id: dto.id,
    name: dto.name,
    slug: dto.slug,
    enabled: dto.enabled,
    transport: fromTransportDto(dto.transport),
    command: dto.command,
    args: dto.args,
    env: dto.env,
    url: dto.url,
    headers: dto.headers,
    timeoutSeconds: dto.timeout_seconds,
    connectionStatus: dto.connection_status,
    discoveryStatus: dto.discovery_status,
    lastError: dto.last_error,
    lastDiscoveredAt: dto.last_discovered_at,
    lastRefreshSucceeded: dto.last_refresh_succeeded,
    tools: dto.tools.map(mapMCPTool),
    ...mapTimestamps(dto),
  }
}

export async function listMCPServers(): Promise<MCPServer[]> {
  const servers = await requestJson<MCPServerDto[]>('/api/mcp/servers')
  return servers.map(mapMCPServer)
}

export async function createMCPServer(payload: MCPServerPayload): Promise<MCPServer> {
  const server = await requestJson<MCPServerDto>('/api/mcp/servers', {
    method: 'POST',
    body: JSON.stringify(toServerRequest(payload)),
  })
  return mapMCPServer(server)
}

export async function updateMCPServer(serverId: string, payload: MCPServerUpdatePayload): Promise<MCPServer> {
  const server = await requestJson<MCPServerDto>(`/api/mcp/servers/${serverId}`, {
    method: 'PUT',
    body: JSON.stringify(toServerUpdateRequest(payload)),
  })
  return mapMCPServer(server)
}

export async function deleteMCPServer(serverId: string): Promise<boolean> {
  const result = await requestJson<DeleteResultDto>(`/api/mcp/servers/${serverId}`, {
    method: 'DELETE',
  })
  return result.success
}

export async function setMCPServerEnabled(serverId: string, enabled: boolean): Promise<MCPServer> {
  const server = await requestJson<MCPServerDto>(`/api/mcp/servers/${serverId}/enabled`, {
    method: 'POST',
    body: JSON.stringify({ enabled } satisfies MCPServerEnabledRequest),
  })
  return mapMCPServer(server)
}

export async function refreshMCPServer(serverId: string): Promise<MCPServer> {
  const server = await requestJson<MCPServerDto>(`/api/mcp/servers/${serverId}/refresh`, {
    method: 'POST',
  })
  return mapMCPServer(server)
}

export async function testMCPServer(serverId: string): Promise<MCPConnectionTestResult> {
  const result = await requestJson<MCPConnectionTestResultDto>(`/api/mcp/servers/${serverId}/test`, {
    method: 'POST',
  })
  return {
    success: result.success,
    message: result.message,
    server: result.server ? mapMCPServer(result.server) : null,
  }
}

export async function updateMCPTool(toolId: string, payload: MCPToolUpdatePayload): Promise<MCPServer> {
  const server = await requestJson<MCPServerDto>(`/api/mcp/tools/${toolId}`, {
    method: 'PATCH',
    body: JSON.stringify(toToolUpdateRequest(payload)),
  })
  return mapMCPServer(server)
}
