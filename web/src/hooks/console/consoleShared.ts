import type { AgentMessage, Asset, ConversationSummary, EventItem, PlanStepStatus } from '../../types/ops'

export const LOCAL_TERMINAL_ASSET_ID = 0
export const PENDING_ASSISTANT_MESSAGE_ID = '__pending_assistant__'

const terminalAutonomyKinds = new Set([
  'terminal_session_request',
  'terminal_session_opened',
  'terminal_session_rejected',
  'terminal_authorization_revoked',
  'terminal_command_submitted',
])

export function isTerminalAutonomyEvent(event: { kind?: string }): boolean {
  return Boolean(event.kind && terminalAutonomyKinds.has(event.kind))
}

function getEventId(event: EventItem): string | undefined {
  return 'eventId' in event && typeof event.eventId === 'string' ? event.eventId : undefined
}

function getTerminalRequestId(event: EventItem): string | undefined {
  return event.kind === 'terminal_session_request' && typeof event.requestId === 'string' ? event.requestId : undefined
}

function isSameTerminalAutonomyEvent(left: EventItem, right: EventItem): boolean {
  const leftRequestId = getTerminalRequestId(left)
  const rightRequestId = getTerminalRequestId(right)
  if (leftRequestId && rightRequestId) {
    return left.kind === right.kind && leftRequestId === rightRequestId
  }

  const leftEventId = getEventId(left)
  const rightEventId = getEventId(right)
  return Boolean(
    (leftEventId && (right.id === leftEventId || rightEventId === leftEventId))
    || (rightEventId && left.id === rightEventId)
    || left.id === right.id
  )
}

function getApprovalToken(event: EventItem): string | null | undefined {
  if ('toolCall' in event) return event.toolCall?.approvalToken
  if (event.kind === 'terminal_session_request') return event.approvalToken
  return undefined
}

function getEventSequence(event: EventItem): number | undefined {
  return 'sequence' in event && typeof event.sequence === 'number' ? event.sequence : undefined
}

export function mergeEventsBySequence(events: EventItem[]): EventItem[] {
  return events
    .map((event, index) => ({ event, index }))
    .sort((left, right) => {
      const leftSequence = getEventSequence(left.event)
      const rightSequence = getEventSequence(right.event)
      if (leftSequence !== undefined && rightSequence !== undefined && leftSequence !== rightSequence) {
        return leftSequence - rightSequence
      }
      return left.index - right.index
    })
    .map(({ event }) => event)
}

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

export function buildTerminalWebSocketUrl(terminalSessionId: string, runtimeApiBaseUrl?: string | null): string {
  const apiBaseUrl = runtimeApiBaseUrl ?? import.meta.env.VITE_API_BASE_URL

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
  // Deduplicate persisted events: for AgentMessages (kind === 'message'), keep only the latest per ID
  const deduped: EventItem[] = []
  const seenMessageIds = new Map<string, number>()
  
  for (let i = 0; i < persistedEvents.length; i++) {
    const event = persistedEvents[i]
    if ('type' in event && (event.type === 'say' || event.type === 'ask') && event.kind === 'message') {
      const prevIndex = seenMessageIds.get(event.id)
      if (prevIndex !== undefined) {
        // Replace the earlier snapshot with this later one
        deduped[prevIndex] = event
      } else {
        seenMessageIds.set(event.id, deduped.length)
        deduped.push(event)
      }
    } else {
      deduped.push(event)
    }
  }

  const hasTerminalError = deduped.some((event) => event.kind === 'error')
  const pendingAssistantEvent = hasTerminalError
    ? undefined
    : currentEvents.find((event) => event.id === PENDING_ASSISTANT_MESSAGE_ID)
  const transientEvents = currentEvents.filter((event) => (
    event.kind === 'delta'
    || event.kind === 'terminal_session_request'
    || 'type' in event
  ) && event.id !== PENDING_ASSISTANT_MESSAGE_ID)
  const hasAssistantDelta = hasTerminalError || deduped.some((event) => event.kind === 'delta' || 'type' in event) || transientEvents.length > 0
  const nextEvents = [...deduped]

  if (pendingAssistantEvent && !hasAssistantDelta) {
    nextEvents.push(pendingAssistantEvent)
  }

  if (transientEvents.length === 0) {
    return normalizePlanEvents(nextEvents)
  }

  const persistedIds = new Set(nextEvents.map((event) => event.id))
  const persistedTerminalRequestIds = new Map<string, number>()
  nextEvents.forEach((event, index) => {
    const requestId = getTerminalRequestId(event)
    if (requestId) {
      persistedTerminalRequestIds.set(requestId, index)
    }
  })

  for (const event of transientEvents) {
    const requestId = getTerminalRequestId(event)
    const existingIndex = persistedIds.has(event.id)
      ? nextEvents.findIndex((nextEvent) => nextEvent.id === event.id)
      : (requestId ? persistedTerminalRequestIds.get(requestId) ?? -1 : -1)

    if (existingIndex >= 0) {
      const approvalToken = getApprovalToken(event)
      if (approvalToken) {
        nextEvents[existingIndex] = {
          ...nextEvents[existingIndex],
          ...(nextEvents[existingIndex].kind === 'terminal_session_request' ? { approvalToken } : {}),
          ...('toolCall' in nextEvents[existingIndex] ? {
            toolCall: {
              ...nextEvents[existingIndex].toolCall,
              approvalToken,
            },
          } : {}),
        } as EventItem
      }
      continue
    }
    nextEvents.push(event)
  }

  return normalizePlanEvents(nextEvents)
}

export function upsertStreamEvent(
  currentEvents: EventItem[],
  event: EventItem
): EventItem[] {
  if (event.kind === 'error') {
    return normalizePlanEvents([
      ...currentEvents.filter((currentEvent) => currentEvent.id !== PENDING_ASSISTANT_MESSAGE_ID),
      event,
    ])
  }

  if (isTerminalAutonomyEvent(event)) {
    const nextEvents = currentEvents.map((currentEvent) => {
      if (isSameTerminalAutonomyEvent(currentEvent, event)) {
        return event
      }
      return currentEvent
    })
    const hasExistingEvent = currentEvents.some((currentEvent) => isSameTerminalAutonomyEvent(currentEvent, event))
    return normalizePlanEvents(hasExistingEvent ? nextEvents : [...currentEvents, event])
  }

  if (event.kind !== 'plan') {
    return normalizePlanEvents([...currentEvents, event])
  }

  const incomingPlanId = event.planId ?? event.id
  const nextEvents = currentEvents.map((currentEvent) => {
    if (currentEvent.kind !== 'plan') {
      return currentEvent
    }

    const currentPlanId = currentEvent.planId ?? currentEvent.id
    return currentPlanId === incomingPlanId ? event : currentEvent
  })

  const hasExistingPlan = currentEvents.some((currentEvent) => {
    if (currentEvent.kind !== 'plan') {
      return false
    }
    const currentPlanId = currentEvent.planId ?? currentEvent.id
    return currentPlanId === incomingPlanId
  })

  return normalizePlanEvents(hasExistingPlan ? nextEvents : [...currentEvents, event])
}

/**
 * 更新或插入 AgentMessage 到事件列表
 */
export function upsertMessageEvent(
  currentEvents: EventItem[],
  message: AgentMessage
): EventItem[] {
  const existingIndex = currentEvents.findIndex((e) => e.id === message.id)
  if (existingIndex !== -1) {
    const newEvents = [...currentEvents]
    newEvents[existingIndex] = message
    return normalizePlanEvents(newEvents)
  }
  
  // If not found, filter out deltas and append
  const filteredEvents = currentEvents.filter((e) => e.kind !== 'delta' && e.id !== PENDING_ASSISTANT_MESSAGE_ID)
  return normalizePlanEvents([...filteredEvents, message])
}
