import { useCallback, useState, type RefObject } from 'react'
import { appendConversationEvents, streamApproveAgent, streamRunAgent } from '../../api'
import type { Asset, EventItem } from '../../types/ops'
import { flushDeltaBuffer, LOCAL_TERMINAL_ASSET_ID, mergeDeltaEvent } from './consoleShared'

interface UseAgentRunProps {
  // 会话域依赖
  activeConversationId: string | null
  activeConversationIdRef: RefObject<string | null>
  events: EventItem[]
  setEvents: (updater: EventItem[] | ((prev: EventItem[]) => EventItem[])) => void
  createConversation: () => Promise<string>
  applyConversationDetailIfActive: (
    conversationId: string,
    detail: { title: string; events: EventItem[] }
  ) => void
  upsertConversationSummary: (detail: {
    id: string
    title: string
    selectedModel: string | null
    createdAt: string
    updatedAt: string
    events: EventItem[]
  }) => void
  refreshConversationList: () => Promise<any>

  // 终端域依赖
  selectedAsset: Asset
  activeTerminalTab: { sessionId: string | null } | null

  // 基础态依赖
  prompt: string
  selectedModel: string
  setLoadError: (error: string | null) => void
}

export function useAgentRun({
  activeConversationId,
  activeConversationIdRef,
  events,
  setEvents,
  createConversation,
  applyConversationDetailIfActive,
  upsertConversationSummary,
  refreshConversationList,
  selectedAsset,
  activeTerminalTab,
  prompt,
  selectedModel,
  setLoadError,
}: UseAgentRunProps) {
  const [pendingApprovalRunId, setPendingApprovalRunId] = useState<string | null>(null)

  const runAgent = useCallback(async (runPrompt: string) => {
    setLoadError(null)

    let conversationId = activeConversationId

    try {
      if (!conversationId) {
        conversationId = await createConversation()
      }

      if (!conversationId) {
        throw new Error('No active conversation available for agent run.')
      }

      const userEvent: EventItem = {
        id: `user-${Date.now()}`,
        kind: 'user',
        text: runPrompt,
      }

      const persisted = await appendConversationEvents(conversationId, [userEvent])
      const persistedEvents = persisted.events
      upsertConversationSummary(persisted)
      if (activeConversationIdRef.current === conversationId) {
        setEvents(persistedEvents)
        setPendingApprovalRunId(null)
      }

      const stream = await streamRunAgent(
        runPrompt,
        persistedEvents,
        selectedAsset?.id === LOCAL_TERMINAL_ASSET_ID ? undefined : selectedAsset?.id,
        activeTerminalTab?.sessionId ?? null,
        selectedModel,
        conversationId,
      )

      const deltaBuffer = new Map<string, string>()

      for await (const event of stream) {
        if (event.kind === 'delta' && event.messageId) {
          const currentText = deltaBuffer.get(event.messageId) || ''
          const newText = currentText + event.text
          deltaBuffer.set(event.messageId, newText)

          setEvents((currentEvents: EventItem[]) =>
            mergeDeltaEvent(
              currentEvents,
              event.messageId!,
              newText,
              'stage' in event ? event.stage : undefined
            )
          )
          continue
        }

        const detail = await appendConversationEvents(conversationId, [event])
        upsertConversationSummary(detail)
        applyConversationDetailIfActive(conversationId, detail)
        if (event.kind === 'approval' && activeConversationIdRef.current === conversationId) {
          setPendingApprovalRunId(event.runId ?? null)
        }
      }

      // 持久化 delta 缓冲区
      const finalEvents = flushDeltaBuffer(deltaBuffer, events)
      if (finalEvents.length > 0) {
        await appendConversationEvents(conversationId, finalEvents)
      }
    } catch (error) {
      const errorMessage = error instanceof Error ? error.message : 'Failed to run agent.'
      if (!conversationId || activeConversationIdRef.current === conversationId) {
        setLoadError(errorMessage)
      }

      if (conversationId) {
        try {
          const errorEvent: EventItem = {
            id: `error-${Date.now()}`,
            kind: 'error',
            text: errorMessage,
          }
          const detail = await appendConversationEvents(conversationId, [errorEvent])
          upsertConversationSummary(detail)
          applyConversationDetailIfActive(conversationId, detail)
        } catch {
          // Fall back to loadError if persisting the error event also fails.
        }
      }
    } finally {
      try {
        await refreshConversationList()
      } catch {
        // Keep the main error surfaced via loadError without throwing from cleanup.
      }
    }
  }, [
    activeConversationId,
    activeConversationIdRef,
    createConversation,
    prompt,
    selectedAsset,
    activeTerminalTab,
    selectedModel,
    setLoadError,
    upsertConversationSummary,
    setEvents,
    applyConversationDetailIfActive,
    refreshConversationList,
    events,
  ])

  const submitApproval = useCallback(
    async (approved: boolean) => {
      if (!pendingApprovalRunId || !activeConversationId) {
        return
      }

      const runId = pendingApprovalRunId
      const conversationId = activeConversationId
      setPendingApprovalRunId(null)

      try {
        const stream = await streamApproveAgent(runId, approved)
        const deltaBuffer = new Map<string, string>()

        for await (const event of stream) {
          if (event.kind === 'delta' && event.messageId) {
            const currentText = deltaBuffer.get(event.messageId) || ''
            const newText = currentText + event.text
            deltaBuffer.set(event.messageId, newText)

            setEvents((currentEvents: EventItem[]) =>
              mergeDeltaEvent(
                currentEvents,
                event.messageId!,
                newText,
                'stage' in event ? event.stage : undefined
              )
            )
            continue
          }

          const detail = await appendConversationEvents(conversationId, [event])
          upsertConversationSummary(detail)
          applyConversationDetailIfActive(conversationId, detail)
          if (event.kind === 'approval' && activeConversationIdRef.current === conversationId) {
            setPendingApprovalRunId(event.runId ?? null)
          }
        }

        // 持久化 delta 缓冲区
        const finalEvents = flushDeltaBuffer(deltaBuffer, events)
        if (finalEvents.length > 0) {
          await appendConversationEvents(conversationId, finalEvents)
        }
      } catch (error) {
        const errorMessage = error instanceof Error ? error.message : 'Failed to submit approval.'
        setLoadError(errorMessage)

        try {
          const errorEvent: EventItem = {
            id: `error-${Date.now()}`,
            kind: 'error',
            text: errorMessage,
          }
          const detail = await appendConversationEvents(conversationId, [errorEvent])
          upsertConversationSummary(detail)
          applyConversationDetailIfActive(conversationId, detail)
        } catch {
          // Fall back to loadError if persisting the error event also fails.
        }

        if (activeConversationIdRef.current === conversationId) {
          setPendingApprovalRunId(runId)
        }
      } finally {
        try {
          await refreshConversationList()
        } catch {
          // Keep the main error surfaced via loadError without throwing from cleanup.
        }
      }
    },
    [
      pendingApprovalRunId,
      activeConversationId,
      activeConversationIdRef,
      setLoadError,
      upsertConversationSummary,
      applyConversationDetailIfActive,
      setEvents,
      refreshConversationList,
      events,
    ]
  )

  return {
    pendingApprovalRunId,
    runAgent,
    approveRun: () => void submitApproval(true),
    rejectRun: () => void submitApproval(false),
  }
}
