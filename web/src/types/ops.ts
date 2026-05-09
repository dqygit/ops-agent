export type AssetType = 'linux' | 'local_terminal' | 'network' | 'cisco' | 'huawei' | 'juniper' | 'h3c' | 'serial'

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

export type RunMode = 'agent' | 'plan'

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
  runtimeId?: string
  mode?: RunMode
  lockedPlan?: boolean
}

export type TerminalStreamKind = 'echo' | 'stdout' | 'stderr' | 'status'

export type CommandStartEvent = {
  id: string
  kind: 'command_start'
  commandId: string
  terminalId?: string | null
  command: string
  title?: string
}

export type CommandChunkEvent = {
  id: string
  kind: 'command_chunk'
  commandId: string
  terminalId?: string | null
  stream: TerminalStreamKind
  text: string
  sequence?: number
}

export type CommandEndEvent = {
  id: string
  kind: 'command_end'
  commandId: string
  terminalId?: string | null
  exitCode: number | null
  summary?: string
}

export type RuntimeStep = {
  stepId: string
  title: string
  command: string
  reason: string
  riskLevel: string
  workingDirectory?: string | null
  expectedOutput?: string | null
  status: 'pending' | 'running' | 'completed' | 'failed'
  output?: string
  exitCode?: number | null
}

export type RuntimeSummary = {
  runtimeId: string
  conversationId: string
  assetId: number
  terminalId: string | null
  status: string
  currentStepId: string | null
  pendingApprovalStepId: string | null
  updatedAt: string
}

export type RuntimeSnapshot = {
  runtimeId: string
  conversationId: string
  assetId: number
  terminalId: string | null
  status: string
  steps: RuntimeStep[]
  currentStepId: string | null
  pendingApprovalStepId: string | null
  lastOutputExcerpt: string
  summary: string | null
  errorMessage: string | null
  createdAt: string
  updatedAt: string
  lastSequence: number
}

export type RuntimeEventEnvelope = {
  type: string
  conversationId: string
  runtimeId: string
  sequence: number
  timestamp: string
  [key: string]: unknown
}

export type TerminalStatusEvent = {
  id: string
  kind: 'terminal_status'
  terminalId?: string | null
  status: string
  message?: string
}

export type EventItem =
  | { id: string; kind: 'status'; text: string }
  | { id: string; kind: 'delta'; text: string; messageId: string; stage?: string }
  | PlanEvent
  | { id: string; kind: 'approval'; text: string; command: string; runtimeId?: string; stepId?: string }
  | { id: string; kind: 'output'; text: string }
  | CommandStartEvent
  | CommandChunkEvent
  | CommandEndEvent
  | TerminalStatusEvent
  | { id: string; kind: 'final'; text: string }
  | { id: string; kind: 'error'; text: string }
  | { id: string; kind: 'user'; text: string }

export type ConversationSummary = {
  id: string
  title: string
  selectedModel: string | null
  createdAt: string
  updatedAt: string
  eventCount: number
  lastEventKind: string | null
}

export type ConversationDetail = {
  id: string
  title: string
  selectedModel: string | null
  createdAt: string
  updatedAt: string
  events: EventItem[]
}

export type DeleteConversationResult = {
  deletedConversationId: string
  activeConversationId: string | null
}

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
