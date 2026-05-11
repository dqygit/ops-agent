import type { Asset, ConversationSummary, EventItem, PlanStepStatus } from '../../types/ops'

export const LOCAL_TERMINAL_ASSET_ID = 0
export const PENDING_ASSISTANT_MESSAGE_ID = '__pending_assistant__'

export const defaultLocalTerminalAsset: Asset = {
  id: LOCAL_TERMINAL_ASSET_ID,
  groupId: null,
  name: 'Local Terminal',
  assetType: 'local_terminal',
  host: '',
  port: 0,
  username: '',
  authType: '',
  tags: [],
  vendor: '',
  description: 'Default local terminal',
  sshKeyId: null,
}

export function normalizePlanEvents(rawEvents: EventItem[]): EventItem[] {
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

export function buildTerminalWebSocketUrl(terminalSessionId: string): string {
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

export function upsertConversationSummaryFromDetail(
  currentItems: ConversationSummary[],
  detail: {
    id: string
    title: string
    selectedModel: string | null
    createdAt: string
    updatedAt: string
    events: EventItem[]
  }
): ConversationSummary[] {
  const lastEvent = detail.events[detail.events.length - 1]
  const summary: ConversationSummary = {
    id: detail.id,
    title: detail.title,
    selectedModel: detail.selectedModel,
    createdAt: detail.createdAt,
    updatedAt: detail.updatedAt,
    eventCount: detail.events.length,
    lastEventKind: lastEvent?.kind ?? null,
  }

  const nextItems = currentItems.filter((item) => item.id !== detail.id)
  return [summary, ...nextItems]
}

/**
 * 合并 delta 事件到现有事件列表
 */
export function mergeDeltaEvent(
  currentEvents: EventItem[],
  messageId: string,
  deltaText: string,
  stage?: string
): EventItem[] {
  const filteredEvents = currentEvents.filter((event) => event.id !== PENDING_ASSISTANT_MESSAGE_ID)
  const existingIndex = filteredEvents.findIndex((e) => e.id === messageId)
  
  const mergedEvent: EventItem = {
    id: messageId,
    kind: 'delta',
    messageId,
    text: deltaText,
    stage,
  }

  if (existingIndex >= 0) {
    const updated = [...filteredEvents]
    updated[existingIndex] = mergedEvent
    return normalizePlanEvents(updated)
  }
  
  return normalizePlanEvents([...filteredEvents, mergedEvent])
}

/**
 * 将 delta 缓冲区转换为最终事件列表
 */
export function flushDeltaBuffer(
  deltaBuffer: Map<string, string>,
  existingEvents: EventItem[]
): EventItem[] {
  const finalEvents: EventItem[] = []
  
  for (const [messageId, text] of deltaBuffer.entries()) {
    const existingEvent = existingEvents.find((e) => e.id === messageId)
    const finalEvent: EventItem = {
      id: messageId,
      kind: 'delta',
      messageId,
      text,
      stage: existingEvent && 'stage' in existingEvent ? existingEvent.stage : undefined,
    }
    finalEvents.push(finalEvent)
  }
  
  return finalEvents
}

export function mergePersistedEventsWithTransient(
  persistedEvents: EventItem[],
  currentEvents: EventItem[]
): EventItem[] {
  const pendingAssistantEvent = currentEvents.find((event) => event.id === PENDING_ASSISTANT_MESSAGE_ID)
  const transientEvents = currentEvents.filter((event) => event.kind === 'delta' && event.id !== PENDING_ASSISTANT_MESSAGE_ID)
  const hasAssistantDelta = persistedEvents.some((event) => event.kind === 'delta') || transientEvents.length > 0
  const nextEvents = [...persistedEvents]

  if (pendingAssistantEvent && !hasAssistantDelta) {
    nextEvents.push(pendingAssistantEvent)
  }

  if (transientEvents.length === 0) {
    return normalizePlanEvents(nextEvents)
  }

  const persistedIds = new Set(nextEvents.map((event) => event.id))

  for (const event of transientEvents) {
    if (!persistedIds.has(event.id)) {
      nextEvents.push(event)
    }
  }

  return normalizePlanEvents(nextEvents)
}
