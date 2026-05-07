export type AssetType = 'linux' | 'local_terminal' | 'network' | 'cisco' | 'huawei' | 'juniper' | 'h3c' | 'telnet' | 'serial'

export type AssetGroup = {
  id: number
  name: string
  description: string
  createdAt: string
  updatedAt: string
}

export type Asset = {
  id: number
  groupId: number | null
  sshKeyId: number | null
  name: string
  assetType: AssetType
  host: string
  port: number
  username: string
  authType: string
  tags: string[]
  vendor: string
  description: string
}

export type ModelConfig = {
  id: number
  name: string
  provider: string
  baseUrl: string
  apiKeyMasked: string
  modelName: string
  isDefault: boolean
  timeoutSeconds: number
  temperature: number
  maxTokens: number
  description: string
  createdAt: string | null
  updatedAt: string | null
}

export type SSHKey = {
  id: number
  name: string
  publicKey: string
  hasPassphrase: boolean
  createdAt: string
  updatedAt: string
}

export type SessionRecord = {
  id: number
  title: string
  model: string
}

export type PlanStepStatus = 'pending' | 'running' | 'completed'

export type PlanStep = {
  id?: string
  title: string
  command?: string
  summary?: string
  status?: PlanStepStatus
}

export type PlanEvent = {
  id: string
  kind: 'plan'
  planId?: string
  title?: string
  loading?: boolean
  version?: number
  isLatest?: boolean
  updated?: boolean
  steps: PlanStep[]
}

export type EventItem =
  | { id: string; kind: 'status'; text: string }
  | { id: string; kind: 'delta'; text: string; messageId: string; stage?: string }
  | PlanEvent
  | { id: string; kind: 'approval'; text: string; command: string; runId?: string }
  | { id: string; kind: 'output'; text: string }
  | { id: string; kind: 'final'; text: string }
  | { id: string; kind: 'error'; text: string }
  | { id: string; kind: 'user'; text: string }

export type AssetContext = {
  asset: Asset
  terminalSession: {
    id: number
    status: string
    lastError: string
    startedAt: string
    endedAt: string | null
  } | null
  recentTerminalEvents: Array<{
    id: number
    eventType: string
    eventData: string
    createdAt: string
  }>
  assistantSessions: SessionRecord[]
}
