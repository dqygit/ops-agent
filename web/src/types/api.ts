import type { Asset, EventItem, SessionRecord } from './ops'

export type ConsoleBootstrap = {
  assets: Asset[]
  historyByAsset: Record<number, SessionRecord[]>
  modelOptions: string[]
  initialPrompt: string
  terminalOutput: string
  initialEvents: EventItem[]
}
