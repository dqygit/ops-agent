import type { Asset, AssetGroup, EventItem, SessionRecord, SSHKey } from './ops'

export type ConversationSummaryDto = {
  id: string
  title: string
  selected_model: string | null
  created_at: string
  updated_at: string
  event_count: number
  last_event_kind: string | null
}

export type ConversationDetailDto = {
  id: string
  title: string
  selected_model: string | null
  created_at: string
  updated_at: string
  events: EventItem[]
}

export type ConversationCreateResponseDto = {
  conversation: ConversationSummaryDto
  events: EventItem[]
}

export type ConsoleBootstrap = {
  assets: Asset[]
  groups: AssetGroup[]
  historyByAsset: Record<number, SessionRecord[]>
  modelOptions: string[]
  terminalSessionId: string | null
  terminalSessionChannel: string | null
  terminalSessionError: string
  initialPrompt: string
  terminalOutput: string
  initialEvents: EventItem[]
  sshKeys: SSHKey[]
}
