import { useEffect, useRef } from 'react'
import { EmptyState } from '../layout/EmptyState'
import type { EventItem, AgentMessage, PlanStep } from '../../types/ops'
import { CommandExecutionCard } from './conversation/CommandExecutionCard'
import { PlanSummaryCard } from './conversation/PlanSummaryCard'
import { AssistantMessageContent } from './conversation/AssistantMessageContent'
import { EventCard } from './conversation/EventCard'
import { Group, CommandChunk, CommandEnd, DeltaEvent } from './conversation/types'
import { sortAssistantGroups } from './conversation/utils'

type ConversationViewProps = {
  events: EventItem[]
  pendingApprovalRuntimeId: string | null
  onApprove?: (allowPrefix?: string) => void
  onReject?: () => void
  onTerminalRequestDecision?: (input: { runtimeId: string; requestId: string; approvalToken: string; approved: boolean }) => Promise<void>
  onSavePlan?: (runtimeId: string, steps: PlanStep[]) => Promise<void>
  onApprovePlan?: (runtimeId: string) => Promise<void>
}

export function ConversationView({ events, pendingApprovalRuntimeId, onApprove, onReject, onTerminalRequestDecision, onSavePlan, onApprovePlan }: ConversationViewProps) {
  const scrollContainerRef = useRef<HTMLDivElement | null>(null)
  const shouldAutoScrollRef = useRef(true)

  const lastEvent = events[events.length - 1]
  const isStreamingNow = lastEvent?.kind === 'delta'
  const latestPlanEvent = [...events].reverse().find((event) => event.kind === 'plan')
  const settledTerminalRequestIds = new Set<string>()
  for (const event of events) {
    if ((event.kind === 'terminal_session_opened' || event.kind === 'terminal_session_rejected') && event.requestId) {
      settledTerminalRequestIds.add(event.requestId)
    }
  }

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
          chunkEvents: [] as CommandChunk[] 
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

  type TurnData = { id: string; userEvent?: EventItem; assistantGroups: Group[] }
  const turns: TurnData[] = []
  let currentTurn: TurnData = { id: 'turn-0', assistantGroups: [] }
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

  useEffect(() => {
    const el = scrollContainerRef.current
    if (!el) return
    const handleScroll = () => {
      const threshold = 24
      const distanceToBottom = el.scrollHeight - el.scrollTop - el.clientHeight
      shouldAutoScrollRef.current = distanceToBottom <= threshold
    }
    handleScroll()
    el.addEventListener('scroll', handleScroll)
    return () => el.removeEventListener('scroll', handleScroll)
  }, [])

  useEffect(() => {
    const el = scrollContainerRef.current
    if (!el || !shouldAutoScrollRef.current) return
    el.scrollTop = el.scrollHeight
  }, [events])

  if (events.length === 0) {
    return (
      <div className="flex-1 overflow-y-auto p-4" aria-label="Assistant Conversation">
        <EmptyState title="Ready to Start" description="Enter a task and execution logs, approval requests, and results will appear here." />
      </div>
    )
  }

  return (
    <div className="relative flex flex-1 flex-col overflow-hidden" aria-label="Assistant Conversation">
      {latestPlanEvent?.mode === 'plan' ? (
        <div className="absolute right-4 top-3 z-30 w-[min(380px,calc(100%-2rem))]">
          <PlanSummaryCard event={latestPlanEvent} onSave={onSavePlan} onApprove={onApprovePlan} />
        </div>
      ) : null}
      <div ref={scrollContainerRef} className={`flex flex-1 flex-col gap-5 overflow-y-auto px-4 py-4 ${latestPlanEvent?.mode === 'plan' ? 'pt-20' : ''}`}>
        {turns.map((turn, turnIndex) => {
          const isLastTurn = turnIndex === turns.length - 1
          const orderedAssistantGroups = sortAssistantGroups(turn.assistantGroups)

          return (
            <div key={turn.id} className="flex flex-col gap-4">
              {turn.userEvent ? (
                <EventCard
                  event={turn.userEvent}
                  pendingApprovalRuntimeId={pendingApprovalRuntimeId}
                  onApprove={onApprove}
                  onReject={onReject}
                  onTerminalRequestDecision={onTerminalRequestDecision}
                  settledTerminalRequestIds={settledTerminalRequestIds}
                />
              ) : null}

              {orderedAssistantGroups.length > 0 ? (
                <div className="flex flex-col gap-4 w-full">
                  {orderedAssistantGroups.map((entry, index) => {
                    const isLastGroupInTurn = index === orderedAssistantGroups.length - 1
                    
                    if (entry.type === 'command') {
                      return (
                        <CommandExecutionCard
                          key={entry.key}
                          approvalEvent={entry.approvalEvent}
                          startEvent={entry.startEvent}
                          chunkEvents={entry.chunkEvents}
                          endEvent={entry.endEvent}
                          pendingApprovalRuntimeId={pendingApprovalRuntimeId}
                          onApprove={onApprove}
                          onReject={onReject}
                        />
                      )
                    }
                    
                    if (entry.type === 'thinking') {
                      const content = entry.deltas ? entry.deltas.map(d => d.text).join('') : undefined
                      return (
                        <div key={entry.key} className="flex justify-start w-full">
                          <AssistantMessageContent 
                            content={content} 
                            message={entry.message}
                            isStreaming={isLastTurn && isLastGroupInTurn && (isStreamingNow || entry.message?.partial)} 
                            onApprove={onApprove}
                            onReject={onReject}
                            pendingApprovalRuntimeId={pendingApprovalRuntimeId}
                          />
                        </div>
                      )
                    }
                    
                    if (entry.type === 'event') {
                      if (entry.event.kind === 'plan') {
                        if (entry.event !== latestPlanEvent || entry.event.mode === 'plan') {
                          return null
                        }

                        return <div key={entry.event.id} className="max-w-[560px]"><PlanSummaryCard event={entry.event} onSave={onSavePlan} onApprove={onApprovePlan} /></div>
                      }
                      
                      return (
                        <EventCard
                          key={entry.event.id}
                          event={entry.event}
                          pendingApprovalRuntimeId={pendingApprovalRuntimeId}
                          onApprove={onApprove}
                          onReject={onReject}
                          onTerminalRequestDecision={onTerminalRequestDecision}
                  settledTerminalRequestIds={settledTerminalRequestIds}
                        />
                      )
                    }
                    
                    return null
                  })}
                </div>
              ) : null}
            </div>
          )
        })}
      </div>
    </div>
  )
}
