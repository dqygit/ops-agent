import type { Asset, AssetGroup, EventItem, SessionRecord } from './ops'

export type ConsoleBootstrap = {
  assets: Asset[]
  groups: AssetGroup[]
  historyByAsset: Record<number, SessionRecord[]>
  modelOptions: string[]
  terminalSessionId: number | null
  terminalSessionChannel: string | null
  terminalSessionError: string
  initialPrompt: string
  terminalOutput: string
  initialEvents: EventItem[]
}
