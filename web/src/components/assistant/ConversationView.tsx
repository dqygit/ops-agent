import { useEffect, useRef } from 'react'
import { EmptyState } from '../layout/EmptyState'
import type { EventItem, PlanStep } from '../../types/ops'
import { CommandExecutionCard } from './conversation/CommandExecutionCard'
import { PlanSummaryCard } from './conversation/PlanSummaryCard'
import { AssistantMessageContent } from './conversation/AssistantMessageContent'
import { EventCard } from './conversation/EventCard'
import { sortAssistantGroups } from './conversation/utils'
import { buildConversationGroups, buildConversationTurns, collectSettledTerminalRequestIds } from './conversation/conversationModel'

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
  const settledTerminalRequestIds = collectSettledTerminalRequestIds(events)
  const turns = buildConversationTurns(buildConversationGroups(events))

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
