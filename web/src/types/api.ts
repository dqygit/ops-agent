import type { Asset, AssetGroup, EventItem, SessionRecord, SSHKey } from './ops'

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
