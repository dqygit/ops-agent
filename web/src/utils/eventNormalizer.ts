import type { EventItem, PlanStepStatus } from '../types/ops'

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
