import { useCallback, useEffect, useRef, useState } from 'react'
import {
  appendConversationEvents,
  createConversation as createConversationApi,
  deleteConversation as deleteConversationApi,
  getConversation,
  getConversations,
} from '../../api'
import type { ConversationSummary, EventItem } from '../../types/ops'
import { normalizePlanEvents, upsertConversationSummaryFromDetail } from './consoleShared'

export function useConversationState(selectedModel: string) {
  const [conversationSummaries, setConversationSummaries] = useState<ConversationSummary[]>([])
  const [activeConversationId, setActiveConversationId] = useState<string | null>(null)
  const [activeConversationTitle, setActiveConversationTitle] = useState('')
  const [events, setEvents] = useState<EventItem[]>([])
  
  const activeConversationIdRef = useRef<string | null>(null)

  useEffect(() => {
    activeConversationIdRef.current = activeConversationId
  }, [activeConversationId])

  const loadConversation = useCallback(async (conversationId: string) => {
    const detail = await getConversation(conversationId)
    setActiveConversationId(detail.id)
    setActiveConversationTitle(detail.title)
    setEvents(normalizePlanEvents(detail.events))
    return detail
  }, [])

  const refreshConversationList = useCallback(async () => {
    const items = await getConversations()
    setConversationSummaries(items)
    return items
  }, [])

  const applyConversationDetailIfActive = useCallback(
    (conversationId: string, detail: { title: string; events: EventItem[] }) => {
      if (activeConversationIdRef.current !== conversationId) {
        return
      }
      setActiveConversationTitle(detail.title)
      setEvents(normalizePlanEvents(detail.events))
    },
    []
  )

  const createConversation = useCallback(async () => {
    const created = await createConversationApi(selectedModel || null)
    setConversationSummaries((currentItems) => {
      const nextItems = currentItems.filter((item) => item.id !== created.conversation.id)
      return [created.conversation, ...nextItems]
    })
    setActiveConversationId(created.conversation.id)
    setActiveConversationTitle(created.conversation.title)
    setEvents(normalizePlanEvents(created.events))
    return created.conversation.id
  }, [selectedModel])

  const deleteConversation = useCallback(
    async (conversationId: string) => {
      await deleteConversationApi(conversationId)
      const remainingItems = await refreshConversationList()

      if (remainingItems.length === 0) {
        await createConversation()
        return
      }

      if (activeConversationIdRef.current !== conversationId) {
        return
      }

      await loadConversation(remainingItems[0].id)
    },
    [createConversation, loadConversation, refreshConversationList]
  )

  const setActiveConversationMeta = useCallback((id: string, title: string) => {
    setActiveConversationId(id)
    setActiveConversationTitle(title)
  }, [])

  const upsertConversationSummary = useCallback(
    (detail: {
      id: string
      title: string
      selectedModel: string | null
      createdAt: string
      updatedAt: string
      events: EventItem[]
    }) => {
      setConversationSummaries((currentItems) =>
        upsertConversationSummaryFromDetail(currentItems, detail)
      )
    },
    []
  )

  return {
    conversationSummaries,
    activeConversationId,
    activeConversationIdRef,
    activeConversationTitle,
    events,
    setEvents,
    loadConversation,
    refreshConversationList,
    createConversation,
    deleteConversation,
    applyConversationDetailIfActive,
    setActiveConversationMeta,
    upsertConversationSummary,
  }
}
