import type { EventItem, AgentMessage } from '../../../types/ops'
import type { CommandChunk, CommandEnd, DeltaEvent, Group } from './types'

export type ConversationTurn = {
  id: string
  userEvent?: EventItem
  assistantGroups: Group[]
}

export function collectSettledTerminalRequestIds(events: EventItem[]) {
  const settledTerminalRequestIds = new Set<string>()
  for (const event of events) {
    if ((event.kind === 'terminal_session_opened' || event.kind === 'terminal_session_rejected') && event.requestId) {
      settledTerminalRequestIds.add(event.requestId)
    }
  }
  return settledTerminalRequestIds
}

export function buildConversationGroups(events: EventItem[]): Group[] {
  const groups: Group[] = []
  const commandGroupMap = new Map<string, { index: number }>()
  const approvalGroupMap = new Map<string, { index: number }>()
  let currentDeltaGroup: DeltaEvent[] = []
  let deltaGroupCounter = 0

  const flushDeltaGroup = () => {
    if (currentDeltaGroup.length === 0) return
    groups.push({ type: 'thinking', deltas: currentDeltaGroup, key: `chain-${deltaGroupCounter++}` })
    currentDeltaGroup = []
  }

  for (const event of events) {
    if (event.kind === 'terminal_status') continue

    if (event.kind === 'delta') {
      currentDeltaGroup.push(event)
      continue
    }

    flushDeltaGroup()

    if (event.kind === 'approval_required' || event.kind === 'approval_decision' || event.kind === 'approval_granted' || event.kind === 'approval_rejected') {
      const key = event.stepId || `${event.runtimeId || 'runtime'}:${event.command}`
      const existing = approvalGroupMap.get(key)
      if (existing) {
        const target = groups[existing.index]
        if (target.type === 'command') {
          let updatedStatus = target.approvalEvent?.status
          if (event.kind === 'approval_granted') updatedStatus = 'approved'
          if (event.kind === 'approval_rejected') updatedStatus = 'rejected'
          if (event.status) updatedStatus = event.status

          target.approvalEvent = {
            ...(target.approvalEvent ?? event),
            ...event,
            status: updatedStatus,
            command: event.command || target.approvalEvent?.command || target.startEvent?.command || '',
          }
        }
      } else {
        let initStatus = event.status
        if (event.kind === 'approval_granted') initStatus = 'approved'
        if (event.kind === 'approval_rejected') initStatus = 'rejected'

        const commandGroup = {
          type: 'command' as const,
          key: `approval-${key}`,
          approvalEvent: { ...event, status: initStatus },
          chunkEvents: [] as CommandChunk[],
        }
        const insertIndex = groups.length
        groups.push(commandGroup)
        approvalGroupMap.set(key, { index: insertIndex })
      }
      continue
    }

    if (event.kind === 'command_start' || event.kind === 'execution_started') {
      const commandId = (event as any).commandId || (event as any).command_id
      const approvalKey = (event as any).stepId || `${(event as any).runtimeId || 'runtime'}:${(event as any).command}`
      const existingApproval = approvalGroupMap.get(approvalKey)
      if (existingApproval) {
        const target = groups[existingApproval.index]
        if (target.type === 'command') {
          target.startEvent = { ...event, commandId } as any
          commandGroupMap.set(commandId, { index: existingApproval.index })
        }
      } else {
        const group = { type: 'command' as const, key: `cmd-${commandId}`, startEvent: { ...event, commandId } as any, chunkEvents: [] as CommandChunk[], endEvent: undefined as CommandEnd | undefined }
        const insertIndex = groups.length
        groups.push(group)
        commandGroupMap.set(commandId, { index: insertIndex })
      }
      continue
    }

    if (event.kind === 'command_chunk' || event.kind === 'execution_output') {
      const commandId = (event as any).commandId || (event as any).command_id
      const ref = commandGroupMap.get(commandId)
      if (ref) {
        const target = groups[ref.index]
        if (target.type === 'command') target.chunkEvents.push({ ...event, commandId } as any)
      }
      continue
    }

    if (event.kind === 'command_end' || event.kind === 'execution_completed') {
      const commandId = (event as any).commandId || (event as any).command_id
      const ref = commandGroupMap.get(commandId)
      if (ref) {
        const target = groups[ref.index]
        if (target.type === 'command') target.endEvent = { ...event, commandId, exitCode: (event as any).exitCode ?? (event as any).exit_code } as any
      }
      continue
    }

    if ('type' in event && (event.type === 'say' || event.type === 'ask')) {
      groups.push({ type: 'thinking', message: event as AgentMessage, key: `msg-${event.id}` })
      continue
    }

    groups.push({ type: 'event', event })
  }

  flushDeltaGroup()
  return groups
}

export function buildConversationTurns(groups: Group[]): ConversationTurn[] {
  const turns: ConversationTurn[] = []
  let currentTurn: ConversationTurn = { id: 'turn-0', assistantGroups: [] }
  let turnCounter = 0

  groups.forEach((entry) => {
    if (entry.type === 'event' && entry.event.kind === 'user') {
      if (currentTurn.userEvent || currentTurn.assistantGroups.length > 0) {
        turns.push(currentTurn)
        turnCounter++
      }
      currentTurn = { id: `turn-${turnCounter}`, userEvent: entry.event, assistantGroups: [] }
    } else {
      currentTurn.assistantGroups.push(entry)
    }
  })

  if (currentTurn.userEvent || currentTurn.assistantGroups.length > 0) {
    turns.push(currentTurn)
  }

  return turns
}
