import { useCallback, useEffect, useMemo, useRef, useState } from 'react'

import {
  approveAgent,
  closeTerminalSession as closeTerminalSessionApi,
  createAsset,
  createTerminalSession,
  deleteAsset as deleteAssetApi,
  getAssetContext,
  getConsoleBootstrap,
  runAgent as runAgentApi,
  streamApproveAgent,
  streamRunAgent,
  updateAsset as updateAssetApi,
} from '../api'
import type { AssetPayload } from '../api'
import type { ConsoleBootstrap } from '../types/api'
import type { Asset, AssetGroup, EventItem, PlanStepStatus, SSHKey } from '../types/ops'

const LOCAL_TERMINAL_ASSET_ID = 0

type TerminalTab = {
  assetId: number
  asset: Asset
  sessionId: number | null
  output: string
}

const defaultLocalTerminalAsset: Asset = {
  id: LOCAL_TERMINAL_ASSET_ID,
  groupId: null,
  name: '本地终端',
  assetType: 'local_terminal',
  host: '',
  port: 0,
  username: '',
  authType: '',
  tags: [],
  vendor: '',
  description: '默认本地终端',
  sshKeyId: null,
}

const emptyBootstrap: ConsoleBootstrap = {
  assets: [],
  groups: [],
  historyByAsset: {},
  modelOptions: [],
  terminalSessionId: null,
  terminalSessionChannel: null,
  terminalSessionError: '',
  initialPrompt: '',
  terminalOutput: '',
  initialEvents: [],
  sshKeys: [],
}

function normalizePlanEvents(rawEvents: EventItem[]): EventItem[] {
  const latestPlanEventIndexByPlanId = new Map<string, number>()

  rawEvents.forEach((event, index) => {
    if (event.kind !== 'plan') {
      return
    }

    const planId = event.planId ?? event.id
    latestPlanEventIndexByPlanId.set(planId, index)
  })

  return rawEvents.map((event, index) => {
    if (event.kind !== 'plan') {
      return event
    }

    const normalizedSteps = event.steps.map((step, stepIndex, steps) => {
      if (step.status) {
        return step
      }

      const fallbackStatus: PlanStepStatus = stepIndex === steps.length - 1 ? 'running' : 'completed'
      return {
        ...step,
        status: fallbackStatus,
      }
    })

    const planId = event.planId ?? event.id
    const latestIndex = latestPlanEventIndexByPlanId.get(planId) ?? index
    return {
      ...event,
      planId,
      title: event.title ?? 'Task Plan',
      loading: event.loading ?? false,
      version: event.version ?? latestIndex + 1,
      isLatest: index === latestIndex,
      updated: event.updated ?? index !== latestIndex,
      steps: normalizedSteps,
    }
  })
}

function mergeStreamEvent(currentEvents: EventItem[], incomingEvent: EventItem): EventItem[] {
  if (incomingEvent.kind !== 'delta') {
    return normalizePlanEvents([...currentEvents, incomingEvent])
  }
  const index = currentEvents.findIndex((item) => item.kind === 'delta' && item.messageId === incomingEvent.messageId)
  if (index < 0) {
    return normalizePlanEvents([...currentEvents, incomingEvent])
  }
  const nextEvents = [...currentEvents]
  const previous = nextEvents[index]
  if (previous.kind === 'delta') {
    nextEvents[index] = { ...previous, text: `${previous.text}${incomingEvent.text}` }
  }
  return normalizePlanEvents(nextEvents)
}

function buildTerminalWebSocketUrl(terminalSessionId: number) {
  const apiBaseUrl = import.meta.env.VITE_API_BASE_URL

  if (apiBaseUrl && apiBaseUrl.length > 0) {
    const baseUrl = new URL(apiBaseUrl, window.location.origin)
    baseUrl.protocol = baseUrl.protocol === 'https:' ? 'wss:' : 'ws:'
    baseUrl.pathname = `/api/terminal/sessions/${terminalSessionId}/ws`
    baseUrl.search = ''
    baseUrl.hash = ''
    return baseUrl.toString()
  }

  const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:'
  return `${protocol}//${window.location.host}/api/terminal/sessions/${terminalSessionId}/ws`
}

export function useConsoleData() {
  const [tab, setTab] = useState<'assets' | 'history'>('assets')
  const [bootstrap, setBootstrap] = useState<ConsoleBootstrap>(emptyBootstrap)
  const [terminalTabs, setTerminalTabs] = useState<TerminalTab[]>([{ assetId: LOCAL_TERMINAL_ASSET_ID, asset: defaultLocalTerminalAsset, sessionId: null, output: '' }])
  const [activeTerminalAssetId, setActiveTerminalAssetId] = useState<number>(LOCAL_TERMINAL_ASSET_ID)
  const [selectedModel, setSelectedModel] = useState<string>('')
  const [prompt, setPrompt] = useState('')
  const [events, setEvents] = useState<EventItem[]>([])
  const [pendingApprovalRunId, setPendingApprovalRunId] = useState<string | null>(null)
  const [selectedAssetContext, setSelectedAssetContext] = useState<import('../types/ops').AssetContext | null>(null)
  const [loadError, setLoadError] = useState<string | null>(null)
  const terminalSocketsRef = useRef<Record<number, WebSocket | undefined>>({})
  const terminalSessionIdsRef = useRef<Record<number, number | null>>({ [LOCAL_TERMINAL_ASSET_ID]: null })
  const terminalTabsRef = useRef<TerminalTab[]>([{ assetId: LOCAL_TERMINAL_ASSET_ID, asset: defaultLocalTerminalAsset, sessionId: null, output: '' }])
  const terminalSocketRef = useRef<WebSocket | null>(null)

  const syncTerminalTabs = useCallback((updater: (currentTabs: TerminalTab[]) => TerminalTab[]) => {
    setTerminalTabs((currentTabs) => {
      const nextTabs = updater(currentTabs)
      terminalTabsRef.current = nextTabs
      terminalSessionIdsRef.current = Object.fromEntries(nextTabs.map((tab) => [tab.assetId, tab.sessionId]))
      return nextTabs
    })
  }, [])

  const connectAssetTerminal = useCallback(async (asset: Asset) => {
    if (asset.id === LOCAL_TERMINAL_ASSET_ID) {
      setActiveTerminalAssetId(LOCAL_TERMINAL_ASSET_ID)
      return
    }

    setLoadError(null)
    setActiveTerminalAssetId(asset.id)

    const existingTab = terminalTabsRef.current.find((item) => item.assetId === asset.id)
    if (existingTab) {
      return
    }

    syncTerminalTabs((currentTabs) => [...currentTabs, { assetId: asset.id, asset, sessionId: null, output: '' }])

    try {
      const result = await createTerminalSession(asset.id)
      if (result.error) {
        throw new Error(result.error)
      }
      if (result.terminal_session_id === null) {
        throw new Error('终端会话创建失败')
      }
      syncTerminalTabs((currentTabs) => currentTabs.map((tabItem) => (tabItem.assetId === asset.id ? { ...tabItem, sessionId: result.terminal_session_id } : tabItem)))
    } catch (error) {
      syncTerminalTabs((currentTabs) => currentTabs.filter((tabItem) => tabItem.assetId !== asset.id))
      setLoadError(error instanceof Error ? error.message : '连接资产终端失败')
    }
  }, [syncTerminalTabs])

  useEffect(() => {
    let active = true

    void getConsoleBootstrap()
      .then((data) => {
        if (!active) {
          return
        }
        setBootstrap(data)
        setSelectedModel(data.modelOptions[0] ?? '')
        setPrompt(data.initialPrompt)
        setEvents(normalizePlanEvents(data.initialEvents))
        const localTab: TerminalTab = {
          assetId: LOCAL_TERMINAL_ASSET_ID,
          asset: defaultLocalTerminalAsset,
          sessionId: data.terminalSessionId,
          output: data.terminalOutput,
        }
        setTerminalTabs([localTab])
        terminalTabsRef.current = [localTab]
        terminalSessionIdsRef.current = { [LOCAL_TERMINAL_ASSET_ID]: data.terminalSessionId }
        setActiveTerminalAssetId(LOCAL_TERMINAL_ASSET_ID)
        setLoadError(null)
      })
      .catch((error: unknown) => {
        if (!active) {
          return
        }
        setLoadError(error instanceof Error ? error.message : 'Failed to load console data.')
      })

    return () => {
      active = false
    }
  }, [])

  useEffect(() => {
    const currentSockets = terminalSocketsRef.current
    const activeTab = terminalTabs.find((item) => item.assetId === activeTerminalAssetId)
    terminalSocketRef.current = activeTab?.sessionId !== null && activeTab?.sessionId !== undefined ? (currentSockets[activeTerminalAssetId] ?? null) : null

    for (const tabItem of terminalTabs) {
      if (tabItem.sessionId === null || currentSockets[tabItem.assetId]) {
        continue
      }

      const socket = new WebSocket(buildTerminalWebSocketUrl(tabItem.sessionId))
      currentSockets[tabItem.assetId] = socket

      socket.addEventListener('message', (event) => {
        try {
          const payload = JSON.parse(event.data) as {
            type?: string
            data?: string
            message?: string
          }

          if (payload.type === 'output') {
            syncTerminalTabs((currentTabs) => currentTabs.map((item) => (item.assetId === tabItem.assetId ? { ...item, output: `${item.output}${payload.data ?? ''}` } : item)))
            return
          }

          if (payload.type === 'error') {
            setLoadError(payload.message ?? 'Terminal session error.')
          }
        } catch {
          syncTerminalTabs((currentTabs) => currentTabs.map((item) => (item.assetId === tabItem.assetId ? { ...item, output: `${item.output}${String(event.data)}` } : item)))
        }
      })

      socket.addEventListener('error', () => {
        setLoadError('Terminal websocket connection failed.')
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
      if (socket && (socket.readyState === WebSocket.OPEN || socket.readyState === WebSocket.CONNECTING)) {
        socket.close()
      }
      if (sessionId !== null && sessionId !== undefined) {
        void closeTerminalSessionApi(sessionId).catch(() => undefined)
      }
      delete terminalSessionIdsRef.current[assetId]
    }
  }, [activeTerminalAssetId, syncTerminalTabs, terminalTabs])

  useEffect(() => {
    return () => {
      for (const tabItem of terminalTabsRef.current) {
        if (tabItem.assetId === LOCAL_TERMINAL_ASSET_ID || tabItem.sessionId === null) {
          continue
        }
        const socket = terminalSocketsRef.current[tabItem.assetId]
        delete terminalSocketsRef.current[tabItem.assetId]
        if (socket && (socket.readyState === WebSocket.OPEN || socket.readyState === WebSocket.CONNECTING)) {
          socket.close()
        }
        void closeTerminalSessionApi(tabItem.sessionId).catch(() => undefined)
      }
      terminalSocketRef.current = null
    }
  }, [])

  const sendTerminalInput = useCallback((data: string) => {
    const socket = terminalSocketRef.current
    if (socket?.readyState !== WebSocket.OPEN) {
      return
    }
    socket.send(JSON.stringify({ type: 'input', data }))
  }, [])

  const resizeTerminal = useCallback((cols: number, rows: number) => {
    const socket = terminalSocketRef.current
    if (socket?.readyState !== WebSocket.OPEN) {
      return
    }
    socket.send(JSON.stringify({ type: 'resize', cols, rows }))
  }, [])

  const selectedAsset = useMemo(
    () => {
      return terminalTabs.find((item) => item.assetId === activeTerminalAssetId)?.asset ?? defaultLocalTerminalAsset
    },
    [activeTerminalAssetId, terminalTabs],
  )

  const activeTerminalTab = useMemo(() => terminalTabs.find((item) => item.assetId === activeTerminalAssetId) ?? terminalTabs[0], [activeTerminalAssetId, terminalTabs])

  const history = selectedAsset ? bootstrap.historyByAsset[selectedAsset.id] ?? [] : []

  const selectAsset = useCallback((assetId: number) => {
    if (assetId === LOCAL_TERMINAL_ASSET_ID) {
      setActiveTerminalAssetId(LOCAL_TERMINAL_ASSET_ID)
      return
    }
    const asset = bootstrap.assets.find((item) => item.id === assetId)
    if (!asset) {
      return
    }
    void connectAssetTerminal(asset)
    void getAssetContext(asset.id).then(setSelectedAssetContext).catch(() => undefined)
  }, [bootstrap.assets, connectAssetTerminal])

  const addAsset = async (payload: AssetPayload) => {
    const asset = await createAsset(payload)
    setBootstrap((currentBootstrap) => ({
      ...currentBootstrap,
      assets: [asset, ...currentBootstrap.assets],
    }))
    selectAsset(asset.id)
  }

  const updateAsset = async (assetId: number, payload: AssetPayload) => {
    const asset = await updateAssetApi(assetId, payload)
    setBootstrap((currentBootstrap) => ({
      ...currentBootstrap,
      assets: currentBootstrap.assets.map((item) => (item.id === asset.id ? asset : item)),
    }))
    selectAsset(asset.id)
    return asset
  }

  const deleteAsset = async (assetId: number) => {
    await deleteAssetApi(assetId)
    setBootstrap((currentBootstrap) => {
      const nextAssets = currentBootstrap.assets.filter((item) => item.id !== assetId)
      return {
        ...currentBootstrap,
        assets: nextAssets,
      }
    })
    syncTerminalTabs((currentTabs) => currentTabs.filter((item) => item.assetId !== assetId))
    setActiveTerminalAssetId((currentId) => (currentId === assetId ? LOCAL_TERMINAL_ASSET_ID : currentId))
  }

  const replaceGroups = (groups: AssetGroup[]) => {
    const groupIds = new Set(groups.map((group) => group.id))
    setBootstrap((currentBootstrap) => ({
      ...currentBootstrap,
      groups,
      assets: currentBootstrap.assets.map((asset) => (asset.groupId !== null && !groupIds.has(asset.groupId) ? { ...asset, groupId: null } : asset)),
    }))
  }

  const replaceModelOptions = (modelOptions: string[]) => {
    setBootstrap((currentBootstrap) => ({
      ...currentBootstrap,
      modelOptions: modelOptions.length > 0 ? modelOptions : currentBootstrap.modelOptions,
    }))
    setSelectedModel((currentModel) => (modelOptions.length === 0 || modelOptions.includes(currentModel) ? currentModel : modelOptions[0]))
  }

  const replaceSSHKeys = (sshKeys: SSHKey[]) => {
    setBootstrap((currentBootstrap) => ({
      ...currentBootstrap,
      sshKeys,
      assets: currentBootstrap.assets.map((asset) => (asset.sshKeyId !== null && !sshKeys.some((sshKey) => sshKey.id === asset.sshKeyId) ? { ...asset, sshKeyId: null } : asset)),
    }))
  }

  const runAgent = async () => {
    try {
      const stream = await streamRunAgent(
        prompt,
        events,
        selectedAsset?.id === LOCAL_TERMINAL_ASSET_ID ? undefined : selectedAsset?.id,
        selectedModel,
      )
      for await (const event of stream) {
        setEvents((currentEvents) => mergeStreamEvent(currentEvents, event))
        if (event.kind === 'approval') {
          setPendingApprovalRunId(event.runId ?? null)
        }
      }
    } catch (error) {
      setEvents((currentEvents) => normalizePlanEvents([
        ...currentEvents,
        {
          id: `error-${Date.now()}`,
          kind: 'error',
          text: error instanceof Error ? error.message : 'Failed to run agent.',
        },
      ]))
    }
  }

  const submitApproval = async (approved: boolean) => {
    if (!pendingApprovalRunId) {
      return
    }
    const stream = await streamApproveAgent(pendingApprovalRunId, approved)
    setPendingApprovalRunId(null)
    for await (const event of stream) {
      setEvents((currentEvents) => mergeStreamEvent(currentEvents, event))
      if (event.kind === 'approval') {
        setPendingApprovalRunId(event.runId ?? null)
      }
    }
  }

  return {
    tab,
    setTab,
    bootstrap,
    terminalOutput: activeTerminalTab?.output ?? '',
    terminalSessionId: activeTerminalTab?.sessionId ?? null,
    terminalTabs,
    activeTerminalAssetId,
    setActiveTerminalAssetId,
    selectedAsset,
    loadError,
    selectedModel,
    setSelectedModel,
    prompt,
    setPrompt,
    events,
    pendingApprovalRunId,
    selectedAssetContext,
    history,
    setSelectedAssetId: selectAsset,
    addAsset,
    updateAsset,
    deleteAsset,
    replaceGroups,
    replaceModelOptions,
    replaceSSHKeys,
    runAgent,
    approveRun: () => void submitApproval(true),
    rejectRun: () => void submitApproval(false),
    sendTerminalInput,
    resizeTerminal,
    defaultLocalTerminalAsset,
  }
}
