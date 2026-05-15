import type { Asset } from '../../types/ops'
import { defaultLocalTerminalAsset, LOCAL_TERMINAL_ASSET_ID } from './consoleShared'

export type TerminalTabState = {
  assetId: number
  asset: Asset
  sessionId: string | null
  output: string
}

type PersistedTerminalTab = {
  assetId: number
  sessionId: string | null
}

export type PersistedTerminalState = {
  version: 1
  activeAssetId: number
  tabs: PersistedTerminalTab[]
}

const STORAGE_KEY = 'ops_agent_terminal_sessions'

export function readPersistedTerminalState(): PersistedTerminalState | null {
  try {
    const raw = localStorage.getItem(STORAGE_KEY)
    if (!raw) return null
    const parsed = JSON.parse(raw) as Partial<PersistedTerminalState>
    if (parsed.version !== 1 || !Array.isArray(parsed.tabs)) return null
    return {
      version: 1,
      activeAssetId:
        typeof parsed.activeAssetId === 'number'
          ? parsed.activeAssetId
          : LOCAL_TERMINAL_ASSET_ID,
      tabs: parsed.tabs
        .filter(
          (tab): tab is PersistedTerminalTab =>
            typeof tab?.assetId === 'number' &&
            (typeof tab.sessionId === 'string' || tab.sessionId === null)
        )
        .map((tab) => ({ assetId: tab.assetId, sessionId: tab.sessionId })),
    }
  } catch {
    return null
  }
}

export function persistTerminalState(tabs: TerminalTabState[], activeAssetId: number): void {
  const persisted: PersistedTerminalState = {
    version: 1,
    activeAssetId,
    tabs: tabs
      .filter((tab) => tab.assetId !== LOCAL_TERMINAL_ASSET_ID && tab.sessionId !== null)
      .map((tab) => ({ assetId: tab.assetId, sessionId: tab.sessionId })),
  }

  if (persisted.tabs.length === 0) {
    localStorage.removeItem(STORAGE_KEY)
    return
  }

  localStorage.setItem(STORAGE_KEY, JSON.stringify(persisted))
}

export function buildRestoredTerminalState({
  assets,
  localSessionId,
  localOutput,
  persisted,
}: {
  assets: Asset[]
  localSessionId: string | null
  localOutput: string
  persisted: PersistedTerminalState | null
}): { tabs: TerminalTabState[]; activeAssetId: number } {
  const localTab: TerminalTabState = {
    assetId: LOCAL_TERMINAL_ASSET_ID,
    asset: defaultLocalTerminalAsset,
    sessionId: localSessionId,
    output: localOutput,
  }

  if (!persisted) {
    return { tabs: [localTab], activeAssetId: LOCAL_TERMINAL_ASSET_ID }
  }

  const restoredTabs = persisted.tabs.flatMap((tab) => {
    if (tab.sessionId === null) return []
    const asset = assets.find((item) => item.id === tab.assetId)
    if (!asset) return []
    return [{ assetId: asset.id, asset, sessionId: tab.sessionId, output: '' }]
  })

  const tabs = [localTab, ...restoredTabs]
  const activeAssetId = tabs.some((tab) => tab.assetId === persisted.activeAssetId)
    ? persisted.activeAssetId
    : LOCAL_TERMINAL_ASSET_ID

  return { tabs, activeAssetId }
}
