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

export type PlanStepStatus = 'pending' | 'running' | 'completed' | 'failed'

export type PlanStep = {
  id?: string
  title: string
  command?: string
  reason?: string
  riskLevel?: string
  workingDirectory?: string | null
  expectedOutput?: string | null
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
  runtimeId?: string
  stepId?: string
  terminalId?: string | null
  command: string
  title?: string
}

export type CommandChunkEvent = {
  id: string
  kind: 'command_chunk'
  commandId: string
  runtimeId?: string
  stepId?: string
  terminalId?: string | null
  stream: TerminalStreamKind
  text: string
  sequence?: number
}

export type CommandEndEvent = {
  id: string
  kind: 'command_end'
  commandId: string
  runtimeId?: string
  stepId?: string
  terminalId?: string | null
  exitCode: number | null
  summary?: string
}

export type ApprovalEvent = {
  id: string
  kind: 'approval_required' | 'approval_decision' | 'approval_granted' | 'approval_rejected'
  text: string
  command: string
  runtimeId?: string
  stepId?: string
  approvalToken?: string
  approved?: boolean
  status?: 'pending' | 'approved' | 'rejected'
  reason?: string
}

export type ExecutionStartedEvent = {
  id: string
  kind: 'execution_started'
  command_id: string
  terminal_id?: string | null
  command: string
  title: string
  step_id?: string
  runtimeId?: string
  stepId?: string
}

export type ExecutionOutputEvent = {
  id: string
  kind: 'execution_output'
  command_id: string
  terminal_id?: string | null
  stream: TerminalStreamKind
  text: string
  step_id?: string
  runtimeId?: string
  stepId?: string
}

export type ExecutionCompletedEvent = {
  id: string
  kind: 'execution_completed'
  command_id: string
  terminal_id?: string | null
  exit_code: number | null
  completed: boolean
  success: boolean
  step_id?: string
  runtimeId?: string
  stepId?: string
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
  mode: RunMode
  planVersion: number
  lockedPlan: boolean
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
  mode: RunMode
  planVersion: number
  lockedPlan: boolean
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

export type ConversationContextStatus = {
  contextPercent: number
  contextStatus: 'normal' | 'warning' | 'critical'
}

export type ContextStatusEvent = ConversationContextStatus & {
  id: string
  kind: 'context_status'
  compactionApplied?: boolean
  fitStatus?: 'fits' | 'compacted_to_fit' | 'overflow'
  summaryRevision?: string | null
  sourceConversationRevision?: string
}

export type TerminalStatusEvent = {
  id: string
  kind: 'terminal_status'
  terminalId?: string | null
  status: string
  message?: string
}

export type AgentMessage = {
  id: string
  kind: 'message'
  ts: number
  type: 'say' | 'ask'
  say?: 'text' | 'tool_use' | 'error'
  ask?: 'command' | 'followup' | 'completion_result'
  text?: string
  partial: boolean
  toolCall?: {
    id: string
    name: string
    command?: string
    args: Record<string, any>
  }
  toolOutput?: string
  exitCode?: number
  thinking?: string
}

export type EventItem =
  | { id: string; kind: 'delta'; text: string; messageId: string; stage?: string }
  | PlanEvent
  | ApprovalEvent
  | CommandStartEvent
  | CommandChunkEvent
  | CommandEndEvent
  | ExecutionStartedEvent
  | ExecutionOutputEvent
  | ExecutionCompletedEvent
  | ContextStatusEvent
  | TerminalStatusEvent
  | AgentMessage
  | { id: string; kind: 'message_update'; payload: AgentMessage } // For raw event wrapper if needed
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
