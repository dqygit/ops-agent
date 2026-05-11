import { useCallback, useState, type RefObject } from 'react'
import { appendConversationEvents, streamApproveAgent, streamRunAgent } from '../../api'
import type { RunMode } from '../../types/api'
import type { Asset, EventItem, RuntimeSummary } from '../../types/ops'
import { flushDeltaBuffer, LOCAL_TERMINAL_ASSET_ID, mergeDeltaEvent, mergePersistedEventsWithTransient, PENDING_ASSISTANT_MESSAGE_ID } from './consoleShared'

interface UseAgentRunProps {
  // Conversation dependencies
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
  syncConversationRuntimes: (conversationId: string) => Promise<RuntimeSummary[]>

  // Terminal dependencies
  selectedAsset: Asset
  activeTerminalTab: { sessionId: string | null } | null

  // Base state dependencies
  selectedModel: string
  runMode: RunMode
  setLoadError: (error: string | null) => void
}

function shouldSyncRuntimeForEvent(event: EventItem) {
  return event.kind === 'approval_required' || event.kind === 'approval_decision' || event.kind === 'command_end' || event.kind === 'final' || event.kind === 'error'
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
  syncConversationRuntimes,
  selectedAsset,
  activeTerminalTab,
  selectedModel,
  runMode,
  setLoadError,
}: UseAgentRunProps) {
  const [pendingApprovalRuntimeId, setPendingApprovalRuntimeId] = useState<string | null>(null)
  const [pendingApprovalToken, setPendingApprovalToken] = useState<string | null>(null)

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

      const pendingStatusEvent: EventItem = {
        id: PENDING_ASSISTANT_MESSAGE_ID,
        kind: 'delta',
        messageId: PENDING_ASSISTANT_MESSAGE_ID,
        stage: 'assistant',
        text: 'Initiating request and waiting for model response...',
      }

      if (activeConversationIdRef.current === conversationId) {
        setEvents((currentEvents: EventItem[]) => [...currentEvents, userEvent, pendingStatusEvent])
        setPendingApprovalRuntimeId(null)
        setPendingApprovalToken(null)
      }

      const stream = await streamRunAgent(
        runPrompt,
        [...events, userEvent],
        selectedAsset?.id === LOCAL_TERMINAL_ASSET_ID ? undefined : selectedAsset?.id,
        activeTerminalTab?.sessionId ?? null,
        selectedModel,
        conversationId,
        runMode,
      )

      const deltaBuffer = new Map<string, string>()
      const pendingPersistEvents: EventItem[] = []

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

        // Immediately update UI with transient event, don't block SSE stream
        if (activeConversationIdRef.current === conversationId) {
          setEvents((currentEvents: EventItem[]) => [...currentEvents, event])
        }

        // Collect non-delta events, batch persist after stream ends
        pendingPersistEvents.push(event)

        if (event.kind === 'approval_required' && activeConversationIdRef.current === conversationId) {
          setPendingApprovalRuntimeId(event.runtimeId ?? null)
          setPendingApprovalToken(event.approvalToken ?? null)
        }
        if (event.kind === 'approval_decision' && activeConversationIdRef.current === conversationId) {
          setPendingApprovalRuntimeId(null)
          setPendingApprovalToken(null)
        }
      }

      // Batch persist all non-delta events + delta buffer after stream ends
      const finalEvents = flushDeltaBuffer(deltaBuffer, events)
      const allPersistEvents = [...pendingPersistEvents, ...finalEvents]
      if (allPersistEvents.length > 0) {
        const detail = await appendConversationEvents(conversationId, allPersistEvents)
        upsertConversationSummary(detail)
        if (activeConversationIdRef.current === conversationId) {
          setEvents((currentEvents: EventItem[]) => mergePersistedEventsWithTransient(detail.events, currentEvents))
        } else {
          applyConversationDetailIfActive(conversationId, detail)
        }
      }
      await syncConversationRuntimes(conversationId)
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
          if (activeConversationIdRef.current === conversationId) {
            setEvents((currentEvents: EventItem[]) => mergePersistedEventsWithTransient(detail.events, currentEvents))
          } else {
            applyConversationDetailIfActive(conversationId, detail)
          }
          await syncConversationRuntimes(conversationId)
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
    selectedAsset,
    activeTerminalTab,
    selectedModel,
    runMode,
    setLoadError,
    upsertConversationSummary,
    setEvents,
    applyConversationDetailIfActive,
    refreshConversationList,
    syncConversationRuntimes,
    events,
  ])

  const submitApproval = useCallback(
    async (approved: boolean) => {
      if (!pendingApprovalRuntimeId || !activeConversationId) {
        return
      }

      const runId = pendingApprovalRuntimeId
      const approvalToken = pendingApprovalToken
      const conversationId = activeConversationId
      setPendingApprovalRuntimeId(null)
      setPendingApprovalToken(null)

      if (activeConversationIdRef.current === conversationId) {
        setEvents((currentEvents: EventItem[]) => [
          ...currentEvents,
          {
            id: PENDING_ASSISTANT_MESSAGE_ID,
            kind: 'delta',
            messageId: PENDING_ASSISTANT_MESSAGE_ID,
            stage: 'assistant',
            text: approved ? 'Approval submitted, waiting for model to continue...' : 'Rejection submitted, waiting for model to continue...',
          },
        ])
      }

      try {
        const stream = await streamApproveAgent(runId, approved, approvalToken ?? undefined)
        const deltaBuffer = new Map<string, string>()
        const pendingPersistEvents: EventItem[] = []

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

          // Immediately update UI with transient event, don't block SSE stream
          if (activeConversationIdRef.current === conversationId) {
            setEvents((currentEvents: EventItem[]) => [...currentEvents, event])
          }

          // Collect non-delta events, batch persist after stream ends
          pendingPersistEvents.push(event)

          if (event.kind === 'approval_required' && activeConversationIdRef.current === conversationId) {
            setPendingApprovalRuntimeId(event.runtimeId ?? null)
            setPendingApprovalToken(event.approvalToken ?? null)
          }
          if (event.kind === 'approval_decision' && activeConversationIdRef.current === conversationId) {
            setPendingApprovalRuntimeId(null)
            setPendingApprovalToken(null)
          }
        }

        // Batch persist all non-delta events + delta buffer after stream ends
        const finalEvents = flushDeltaBuffer(deltaBuffer, events)
        const allPersistEvents = [...pendingPersistEvents, ...finalEvents]
        if (allPersistEvents.length > 0) {
          const detail = await appendConversationEvents(conversationId, allPersistEvents)
          upsertConversationSummary(detail)
          if (activeConversationIdRef.current === conversationId) {
            setEvents((currentEvents: EventItem[]) => mergePersistedEventsWithTransient(detail.events, currentEvents))
          } else {
            applyConversationDetailIfActive(conversationId, detail)
          }
        }
        await syncConversationRuntimes(conversationId)
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
          if (activeConversationIdRef.current === conversationId) {
            setEvents((currentEvents: EventItem[]) => mergePersistedEventsWithTransient(detail.events, currentEvents))
          } else {
            applyConversationDetailIfActive(conversationId, detail)
          }
          await syncConversationRuntimes(conversationId)
        } catch {
          // Fall back to loadError if persisting the error event also fails.
        }

        if (activeConversationIdRef.current === conversationId) {
          setPendingApprovalRuntimeId(runId)
          setPendingApprovalToken(approvalToken ?? null)
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
      pendingApprovalRuntimeId,
      activeConversationId,
      activeConversationIdRef,
      setLoadError,
      upsertConversationSummary,
      applyConversationDetailIfActive,
      setEvents,
      refreshConversationList,
      syncConversationRuntimes,
      events,
    ]
  )

  return {
    pendingApprovalRuntimeId,
    runAgent,
    approveRun: () => void submitApproval(true),
    rejectRun: () => void submitApproval(false),
  }
}
