import { useCallback, useEffect, useMemo, useRef, useState } from 'react'
import {
  closeTerminalSession as closeTerminalSessionApi,
  createTerminalSession,
  reconnectTerminalSession,
} from '../../api'
import type { Asset } from '../../types/ops'
import {
  buildTerminalWebSocketUrl,
  defaultLocalTerminalAsset,
  LOCAL_TERMINAL_ASSET_ID,
} from './consoleShared'

type TerminalTab = {
  assetId: number
  asset: Asset
  sessionId: string | null
  output: string
}

interface UseTerminalSessionsProps {
  assets: Asset[]
  historyByAsset: Record<number, any[]>
  setLoadError: (error: string | null) => void
}

export function useTerminalSessions({
  assets,
  historyByAsset,
  setLoadError,
}: UseTerminalSessionsProps) {
  const [terminalTabs, setTerminalTabs] = useState<TerminalTab[]>([
    {
      assetId: LOCAL_TERMINAL_ASSET_ID,
      asset: defaultLocalTerminalAsset,
      sessionId: null,
      output: '',
    },
  ])
  const [activeTerminalAssetId, setActiveTerminalAssetId] = useState<number>(
    LOCAL_TERMINAL_ASSET_ID
  )

  const terminalSocketsRef = useRef<Record<number, WebSocket | undefined>>({})
  const terminalSessionIdsRef = useRef<Record<number, string | null>>({
    [LOCAL_TERMINAL_ASSET_ID]: null,
  })
  const terminalTabsRef = useRef<TerminalTab[]>([
    {
      assetId: LOCAL_TERMINAL_ASSET_ID,
      asset: defaultLocalTerminalAsset,
      sessionId: null,
      output: '',
    },
  ])
  const terminalSocketRef = useRef<WebSocket | null>(null)
  const firstOutputHandledRef = useRef<Record<number, boolean>>({
    [LOCAL_TERMINAL_ASSET_ID]: false,
  })

  const syncTerminalTabs = useCallback(
    (updater: (currentTabs: TerminalTab[]) => TerminalTab[]) => {
      setTerminalTabs((currentTabs) => {
        const nextTabs = updater(currentTabs)
        terminalTabsRef.current = nextTabs
        terminalSessionIdsRef.current = Object.fromEntries(
          nextTabs.map((tab) => [tab.assetId, tab.sessionId])
        )
        return nextTabs
      })
    },
    []
  )

  const initializeLocalTerminal = useCallback(
    (terminalSessionId: string | null, terminalOutput: string) => {
      const localTab: TerminalTab = {
        assetId: LOCAL_TERMINAL_ASSET_ID,
        asset: defaultLocalTerminalAsset,
        sessionId: terminalSessionId,
        output: terminalOutput,
      }
      setTerminalTabs([localTab])
      terminalTabsRef.current = [localTab]
      terminalSessionIdsRef.current = {
        [LOCAL_TERMINAL_ASSET_ID]: terminalSessionId,
      }
      setActiveTerminalAssetId(LOCAL_TERMINAL_ASSET_ID)
    },
    []
  )

  const connectAssetTerminal = useCallback(async (asset: Asset) => {
      if (asset.id === LOCAL_TERMINAL_ASSET_ID) {
        setActiveTerminalAssetId(LOCAL_TERMINAL_ASSET_ID)
        return
      }

      setLoadError(null)
      setActiveTerminalAssetId(asset.id)

      const existingTab = terminalTabsRef.current.find(
        (item) => item.assetId === asset.id
      )
      if (existingTab) {
        return
      }

      syncTerminalTabs((currentTabs) => [
        ...currentTabs,
        { assetId: asset.id, asset, sessionId: null, output: '' },
      ])
      firstOutputHandledRef.current[asset.id] = false

      try {
        const result = await createTerminalSession(asset.id)
        if (result.error) {
          throw new Error(result.error)
        }
        if (result.terminal_id === null) {
          throw new Error('Failed to create terminal session')
        }
        syncTerminalTabs((currentTabs) =>
          currentTabs.map((tabItem) =>
            tabItem.assetId === asset.id
              ? { ...tabItem, sessionId: result.terminal_id }
              : tabItem
          )
        )
      } catch (error) {
        const errorMessage =
          error instanceof Error ? error.message : 'Failed to connect to asset terminal'
        setLoadError(errorMessage)

        syncTerminalTabs((currentTabs) =>
          currentTabs.map((tabItem) =>
            tabItem.assetId === asset.id
              ? {
                  ...tabItem,
                  output: `\r\n\x1b[31m[ERROR] ${errorMessage}\x1b[0m\r\n`,
                }
              : tabItem
          )
        )
      }
    },
    [syncTerminalTabs, setLoadError]
  )

  const removeTerminalTab = useCallback(
    (assetId: number) => {
      syncTerminalTabs((currentTabs) =>
        currentTabs.filter((item) => item.assetId !== assetId)
      )
      setActiveTerminalAssetId((currentId) =>
        currentId === assetId ? LOCAL_TERMINAL_ASSET_ID : currentId
      )
    },
    [syncTerminalTabs]
  )

  const sendTerminalInput = useCallback((data: string) => {
    const socket = terminalSocketRef.current
    if (socket?.readyState !== WebSocket.OPEN) {
      return
    }
    socket.send(JSON.stringify({ type: 'input', data }))
  }, [])

  const clearActiveTerminal = useCallback(() => {
    syncTerminalTabs((currentTabs) =>
      currentTabs.map((tab) =>
        tab.assetId === activeTerminalAssetId ? { ...tab, output: '' } : tab
      )
    )
    firstOutputHandledRef.current[activeTerminalAssetId] = true
  }, [activeTerminalAssetId, syncTerminalTabs])

  const copyActiveTerminalOutput = useCallback(async (): Promise<boolean> => {
    const tab = terminalTabsRef.current.find((item) => item.assetId === activeTerminalAssetId)
    const raw = tab?.output ?? ''
    if (!raw) return false
    const cleaned = raw.replace(/[\u001b\u009b][[()#;?]*(?:[0-9]{1,4}(?:;[0-9]{0,4})*)?[0-9A-ORZcf-nqry=><]/g, '')
    try {
      await navigator.clipboard.writeText(cleaned)
      return true
    } catch {
      return false
    }
  }, [activeTerminalAssetId])

  const reconnectActiveTerminal = useCallback(async () => {
    const tab = terminalTabsRef.current.find((item) => item.assetId === activeTerminalAssetId)
    if (!tab) return
    const existingSocket = terminalSocketsRef.current[activeTerminalAssetId]
    if (existingSocket && (existingSocket.readyState === WebSocket.OPEN || existingSocket.readyState === WebSocket.CONNECTING)) {
      existingSocket.close()
    }
    delete terminalSocketsRef.current[activeTerminalAssetId]
    if (terminalSocketRef.current === existingSocket) {
      terminalSocketRef.current = null
    }

    syncTerminalTabs((currentTabs) =>
      currentTabs.map((item) =>
        item.assetId === activeTerminalAssetId ? { ...item, sessionId: null, output: '' } : item
      )
    )
    firstOutputHandledRef.current[activeTerminalAssetId] = false

    try {
      let nextSessionId: string | null = null
      if (tab.sessionId) {
        const result = await reconnectTerminalSession(tab.sessionId, activeTerminalAssetId)
        if (result.error || !result.terminal_id) {
          throw new Error(result.error || 'Reconnection failed')
        }
        nextSessionId = result.terminal_id
      } else {
        const result = await createTerminalSession(activeTerminalAssetId)
        if (result.error || !result.terminal_id) {
          throw new Error(result.error || 'Reconnection failed')
        }
        nextSessionId = result.terminal_id
      }
      syncTerminalTabs((currentTabs) =>
        currentTabs.map((item) =>
          item.assetId === activeTerminalAssetId ? { ...item, sessionId: nextSessionId } : item
        )
      )
    } catch (error) {
      const errorMessage = error instanceof Error ? error.message : 'Terminal reconnection failed'
      setLoadError(errorMessage)
    }
  }, [activeTerminalAssetId, syncTerminalTabs, setLoadError])

  const lastTerminalSizeRef = useRef<{ cols: number; rows: number } | null>(null)

  const resizeTerminal = useCallback((cols: number, rows: number) => {
    lastTerminalSizeRef.current = { cols, rows }
    const socket = terminalSocketRef.current
    if (socket?.readyState !== WebSocket.OPEN) {
      return
    }
    socket.send(JSON.stringify({ type: 'resize', cols, rows }))
  }, [])

  const selectedAsset = useMemo(
    () =>
      terminalTabs.find((item) => item.assetId === activeTerminalAssetId)
        ?.asset ?? defaultLocalTerminalAsset,
    [activeTerminalAssetId, terminalTabs]
  )

  const activeTerminalTab = useMemo(
    () =>
      terminalTabs.find((item) => item.assetId === activeTerminalAssetId) ??
      terminalTabs[0],
    [activeTerminalAssetId, terminalTabs]
  )

  const history = selectedAsset ? historyByAsset[selectedAsset.id] ?? [] : []

  const selectAsset = useCallback(
    (assetId: number) => {
      setLoadError(null)
      if (assetId === LOCAL_TERMINAL_ASSET_ID) {
        setActiveTerminalAssetId(LOCAL_TERMINAL_ASSET_ID)
        return
      }
      const asset = assets.find((item) => item.id === assetId)
      if (!asset) {
        return
      }
      void connectAssetTerminal(asset)
    },
    [assets, connectAssetTerminal, setLoadError]
  )

  // WebSocket Management
  useEffect(() => {
    const currentSockets = terminalSocketsRef.current
    const activeTab = terminalTabs.find(
      (item) => item.assetId === activeTerminalAssetId
    )
    terminalSocketRef.current =
      activeTab?.sessionId !== null && activeTab?.sessionId !== undefined
        ? (currentSockets[activeTerminalAssetId] ?? null)
        : null

    for (const tabItem of terminalTabs) {
      if (tabItem.sessionId === null || currentSockets[tabItem.assetId]) {
        continue
      }

      const socket = new WebSocket(buildTerminalWebSocketUrl(tabItem.sessionId))
      currentSockets[tabItem.assetId] = socket
      if (tabItem.assetId === activeTerminalAssetId) {
        terminalSocketRef.current = socket
      }

      socket.addEventListener('open', () => {
        if (tabItem.assetId === activeTerminalAssetId) {
          terminalSocketRef.current = socket
          if (lastTerminalSizeRef.current) {
            socket.send(JSON.stringify({ type: 'resize', ...lastTerminalSizeRef.current }))
          }
        } else if (lastTerminalSizeRef.current) {
           // We might want to size background tabs too, but active is most important
           socket.send(JSON.stringify({ type: 'resize', ...lastTerminalSizeRef.current }))
        }
      })

      socket.addEventListener('message', (event) => {
        try {
          const payload = JSON.parse(event.data) as {
            type?: string
            data?: string
            message?: string
          }

          if (payload.type === 'output') {
            const incomingOutput = payload.data ?? ''
            syncTerminalTabs((currentTabs) =>
              currentTabs.map((item) => {
                if (item.assetId !== tabItem.assetId) {
                  return item
                }

                const firstHandled = firstOutputHandledRef.current[tabItem.assetId] ?? false
                if (!firstHandled) {
                  firstOutputHandledRef.current[tabItem.assetId] = true
                  if (incomingOutput.length > 0 && item.output.endsWith(incomingOutput)) {
                    return item
                  }
                  if (incomingOutput.length > 0 && incomingOutput.endsWith(item.output)) {
                    return { ...item, output: incomingOutput }
                  }
                }

                return { ...item, output: `${item.output}${incomingOutput}` }
              })
            )
            return
          }

          if (payload.type === 'error') {
            setLoadError(payload.message ?? 'Terminal session error.')
          }
        } catch {
          syncTerminalTabs((currentTabs) =>
            currentTabs.map((item) =>
              item.assetId === tabItem.assetId
                ? { ...item, output: `${item.output}${String(event.data)}` }
                : item
            )
          )
        }
      })

      socket.addEventListener('error', () => {
        setLoadError('Terminal websocket connection failed.')
      })

      socket.addEventListener('close', () => {
        if (terminalSocketsRef.current[tabItem.assetId] === socket) {
          delete terminalSocketsRef.current[tabItem.assetId]
        }
        if (tabItem.assetId === activeTerminalAssetId && terminalSocketRef.current === socket) {
          terminalSocketRef.current = null
        }
      })
    }

    const activeAssetIds = new Set(terminalTabs.map((item) => item.assetId))
    for (const key of Object.keys(currentSockets)) {
      const assetId = Number(key)
      if (activeAssetIds.has(assetId)) {
        continue
      }
      const socket = currentSockets[assetId]
      const sessionId = terminalSessionIdsRef.current[assetId]
      delete currentSockets[assetId]
      if (
        socket &&
        (socket.readyState === WebSocket.OPEN ||
          socket.readyState === WebSocket.CONNECTING)
      ) {
        socket.close()
      }
      if (sessionId !== null && sessionId !== undefined) {
        void closeTerminalSessionApi(sessionId).catch(() => undefined)
      }
      delete terminalSessionIdsRef.current[assetId]
      delete firstOutputHandledRef.current[assetId]
    }
  }, [activeTerminalAssetId, syncTerminalTabs, terminalTabs, setLoadError])

  // Cleanup all WebSockets
  useEffect(() => {
    return () => {
      for (const tabItem of terminalTabsRef.current) {
        if (
          tabItem.assetId === LOCAL_TERMINAL_ASSET_ID ||
          tabItem.sessionId === null
        ) {
          continue
        }
        const socket = terminalSocketsRef.current[tabItem.assetId]
        delete terminalSocketsRef.current[tabItem.assetId]
        if (
          socket &&
          (socket.readyState === WebSocket.OPEN ||
            socket.readyState === WebSocket.CONNECTING)
        ) {
          socket.close()
        }
        void closeTerminalSessionApi(tabItem.sessionId).catch(() => undefined)
      }
      terminalSocketRef.current = null
    }
  }, [])

  return {
    terminalTabs,
    activeTerminalAssetId,
    setActiveTerminalAssetId,
    selectedAsset,
    activeTerminalTab,
    history,
    connectAssetTerminal,
    removeTerminalTab,
    sendTerminalInput,
    resizeTerminal,
    initializeLocalTerminal,
    selectAsset,
    clearActiveTerminal,
    copyActiveTerminalOutput,
    reconnectActiveTerminal,
  }
}
