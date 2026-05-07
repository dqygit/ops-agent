import { useEffect, useRef, useState } from 'react'
import ReactMarkdown from 'react-markdown'
import remarkGfm from 'remark-gfm'
import { EmptyState } from '../layout/EmptyState'
import { DangerButton, PrimaryButton } from '../layout/Button'
import type { EventItem } from '../../types/ops'

function isPlanEvent(event: EventItem): event is Extract<EventItem, { kind: 'plan' }> {
  return event.kind === 'plan'
}

type ConversationViewProps = {
  events: EventItem[]
  pendingApprovalRunId: string | null
  onApprove?: () => void
  onReject?: () => void
}

function stripAnsi(text: string) {
  return text.replace(/[\u001b\u009b][[()#;?]*(?:[0-9]{1,4}(?:;[0-9]{0,4})*)?[0-9A-ORZcf-nqry=><]/g, '')
}

function stripJsonBlocks(text: string) {
  let result = text

  // If model emits explicit split marker, keep only natural language before marker
  const markerIndex = result.indexOf('<FINAL_JSON>')
  if (markerIndex >= 0) {
    result = result.slice(0, markerIndex)
  }

  // Remove fenced code blocks
  result = result.replace(/```json\s*[\s\S]*?```/gi, '')
  result = result.replace(/```\s*[\s\S]*?```/g, '')

  // Remove obvious one-line JSON payloads
  result = result.replace(/\{\s*"(?:steps|decision|summary|title|reason|risk_level|expected_output|command)"[\s\S]*?\}/g, '')

  // Trim off trailing JSON fragments often produced during streaming
  const jsonTailPatterns = [
    /\n\s*\{\s*"(?:steps|decision|summary|title|reason|risk_level|expected_output|command)"[\s\S]*$/,
    /\n\s*\[\s*\{[\s\S]*$/,
    /\n\s*"(?:title|reason|risk_level|expected_output|command|decision|summary)"\s*:[\s\S]*$/,
  ]
  for (const pattern of jsonTailPatterns) {
    result = result.replace(pattern, '')
  }

  // Remove standalone JSON-looking lines
  result = result
    .split('\n')
    .filter((line) => {
      const trimmed = line.trim()
      if (!trimmed) return true
      if (/^[\[{].*[\]}]$/.test(trimmed)) return false
      if (/^"(?:title|reason|risk_level|expected_output|command|decision|summary)"\s*:/.test(trimmed)) return false
      if (/^[\]}],?$/.test(trimmed)) return false
      return true
    })
    .join('\n')

  // Clean punctuation artifacts left by streaming/json truncation
  result = result
    .replace(/[，,、。；;:：\-\s]+$/g, '')
    .replace(/([，,、]){2,}/g, '$1')
    .replace(/\n{3,}/g, '\n\n')

  return result.trim()
}

type OutputBlockProps = {
  text: string
}

function OutputBlock({ text }: OutputBlockProps) {
  const [isExpanded, setIsExpanded] = useState(false)
  const cleanText = stripAnsi(text)
  const lines = cleanText.split('\n')
  const shouldTruncate = lines.length > 8

  return (
    <div className="flex flex-col gap-1 w-full overflow-hidden">
      <div className="flex items-center justify-between px-2 py-1 bg-black/40 rounded-t border-t border-x border-ops-border/10">
        <span className="text-[10px] font-bold text-ops-muted uppercase tracking-widest">Command Output</span>
        {shouldTruncate && (
          <button 
            type="button" 
            onClick={() => setIsExpanded(!isExpanded)}
            className="text-[10px] text-ops-cyan hover:underline"
          >
            {isExpanded ? 'Collapse' : `Expand (${lines.length} lines)`}
          </button>
        )}
      </div>
      <pre 
        className={`whitespace-pre-wrap word-break m-0 font-mono leading-tight p-3 bg-black/60 rounded-b border-b border-x border-ops-border/10 text-[11px] text-ops-text/90 transition-all ${
          !isExpanded && shouldTruncate ? 'max-h-[160px] overflow-hidden relative' : 'max-h-none'
        }`}
      >
        {cleanText}
        {!isExpanded && shouldTruncate && (
          <div className="absolute inset-x-0 bottom-0 h-12 bg-gradient-to-t from-black/80 to-transparent pointer-events-none" />
        )}
      </pre>
    </div>
  )
}

type CommandCardProps = {
  command: string
  showActions: boolean
  onApprove?: () => void
  onReject?: () => void
}

function CommandCard({ command, showActions, onApprove, onReject }: CommandCardProps) {
  return (
    <div className="flex items-center gap-2 p-3 bg-ops-panel/60 border border-ops-border/30 rounded-lg">
      {showActions ? (
        <button
          type="button"
          onClick={onApprove}
          className="flex-shrink-0 w-8 h-8 flex items-center justify-center rounded-full bg-ops-green/20 text-ops-green hover:bg-ops-green/30 transition-colors"
          title="Approve"
        >
          <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
          </svg>
        </button>
      ) : null}
      <code
        className="flex-1 px-3 py-1.5 bg-black/40 rounded text-xs font-mono text-ops-text/90 truncate cursor-help"
        title={command}
      >
        {command}
      </code>
      {showActions ? (
        <button
          type="button"
          onClick={onReject}
          className="flex-shrink-0 w-8 h-8 flex items-center justify-center rounded-full bg-ops-red/20 text-ops-red hover:bg-ops-red/30 transition-colors"
          title="Reject"
        >
          <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
          </svg>
        </button>
      ) : null}
    </div>
  )
}

function getStageLabel(stage?: string) {
  if (stage === 'planner') return 'Planner'
  if (stage === 'executor') return 'Executor'
  if (stage === 'review') return 'Review'
  return 'Assistant'
}

export function ConversationView({ events, pendingApprovalRunId, onApprove, onReject }: ConversationViewProps) {
  const scrollContainerRef = useRef<HTMLDivElement | null>(null)
  const shouldAutoScrollRef = useRef(true)

  useEffect(() => {
    const el = scrollContainerRef.current
    if (!el) {
      return
    }
    const handleScroll = () => {
      const threshold = 24
      const distanceToBottom = el.scrollHeight - el.scrollTop - el.clientHeight
      shouldAutoScrollRef.current = distanceToBottom <= threshold
    }
    handleScroll()
    el.addEventListener('scroll', handleScroll)
    return () => {
      el.removeEventListener('scroll', handleScroll)
    }
  }, [])

  useEffect(() => {
    const el = scrollContainerRef.current
    if (!el || !shouldAutoScrollRef.current) {
      return
    }
    el.scrollTop = el.scrollHeight
  }, [events])

  if (events.length === 0) {
    return (
      <div className="flex-1 overflow-y-auto p-4" aria-label="Assistant conversation">
        <EmptyState
          title="No assistant output"
          description="Choose a model and run an agent task to populate plans, approvals, and results here."
        />
      </div>
    )
  }

  // Filter out empty plan events (loading placeholders with no steps)
  const visibleEvents = events.filter((event) => {
    if (event.kind === 'plan' && (!event.steps || event.steps.length === 0) && event.loading !== true) {
      return false
    }
    return true
  })

  if (visibleEvents.length === 0) {
    return (
      <div className="flex-1 overflow-y-auto p-4" aria-label="Assistant conversation">
        <EmptyState
          title="No assistant output"
          description="Choose a model and run an agent task to populate plans, approvals, and results here."
        />
      </div>
    )
  }

  // Find the latest plan event
  const latestPlanEvent = visibleEvents.filter(isPlanEvent).pop()

  // Filter non-plan events for the conversation area
  const rawConversationEvents = visibleEvents.filter(event => event.kind !== 'plan')
  const latestPendingApprovalEventId = pendingApprovalRunId
    ? [...rawConversationEvents]
        .reverse()
        .find((event) => event.kind === 'approval' && event.runId === pendingApprovalRunId)?.id ?? null
    : null
  const conversationEvents = rawConversationEvents

  return (
    <div className="flex-1 overflow-hidden flex flex-col" aria-label="Assistant conversation">
      {/* Task Plan Card - Fixed at top */}
      {latestPlanEvent && (
        <div className="flex-shrink-0 px-4 pt-4 pb-2">
          <div className="p-3 rounded-lg border bg-ops-panel/80 border-ops-border/30 shadow-glass">
            <div className="flex items-center justify-between gap-3 mb-2">
              <div className="flex items-center gap-2">
                <div className="w-1.5 h-3 bg-ops-green rounded-full" />
                <h3 className="font-bold text-ops-text text-sm tracking-wide">{latestPlanEvent.title?.trim() || 'Task Plan'}</h3>
              </div>
              <div className="flex items-center gap-2 text-[10px] uppercase tracking-wider text-ops-muted">
                {latestPlanEvent.loading ? <span className="text-ops-cyan animate-pulse">● Planning...</span> : null}
                {typeof latestPlanEvent.version === 'number' ? <span className="bg-ops-border/20 px-1.5 py-0.5 rounded">v{latestPlanEvent.version}</span> : null}
              </div>
            </div>
            
            <div className="flex flex-wrap gap-1.5">
              {latestPlanEvent.steps.map((step, index) => (
                <div
                  key={step.id ?? `step-${index}`}
                  className={`inline-flex items-center gap-1.5 px-2 py-1 rounded text-[11px] cursor-help ${
                    step.status === 'completed'
                      ? 'bg-ops-green/10 text-ops-green border border-ops-green/20'
                      : step.status === 'running'
                      ? 'bg-ops-cyan/10 text-ops-cyan border border-ops-cyan/20 animate-pulse'
                      : 'bg-black/20 text-ops-muted border border-ops-border/10'
                  }`}
                  title={step.title}
                >
                  <span className="font-bold">{index + 1}</span>
                  <span className="truncate max-w-[120px]">{step.title}</span>
                  {step.status === 'completed' && <span>✓</span>}
                </div>
              ))}
            </div>
          </div>
        </div>
      )}

      {/* Conversation Area - Scrollable */}
      <div ref={scrollContainerRef} className="flex-1 overflow-y-auto px-4 pb-4 flex flex-col gap-3">
        {conversationEvents.map((event) => {
          if (event.kind === 'status') {
            return <div key={event.id} className="text-xs text-ops-muted italic">{event.text}</div>
          }

          if (event.kind === 'error') {
            return (
              <article key={event.id} className="p-3 rounded-lg bg-ops-red/10 border border-ops-red/30">
                <div className="font-bold uppercase text-[10px] mb-1 text-ops-red">System Error</div>
                <p className="m-0 text-xs font-mono text-ops-text/90">{event.text}</p>
              </article>
            )
          }

          if (event.kind === 'output') {
            return <OutputBlock key={event.id} text={event.text} />
          }

          if (event.kind === 'user') {
            return (
              <article key={event.id} className="p-3 rounded-lg bg-ops-cyan/10 border border-ops-cyan/20 ml-8">
                <div className="font-bold uppercase text-[9px] mb-1 text-ops-cyan tracking-wider">User</div>
                <p className="m-0 text-sm text-ops-text">{event.text}</p>
              </article>
            )
          }

          if (event.kind === 'approval') {
            const showActions = latestPendingApprovalEventId !== null && event.id === latestPendingApprovalEventId
            return (
              <CommandCard
                key={event.id}
                command={event.command}
                showActions={showActions}
                onApprove={onApprove}
                onReject={onReject}
              />
            )
          }

          const isLastEvent = events[events.length - 1].id === event.id

          if (event.kind === 'delta') {
            const cleanText = stripJsonBlocks(event.text)
            if (!cleanText) return null
            return (
              <article
                key={event.id}
                className="p-3 rounded-lg bg-ops-panel/60 border border-ops-border/20"
              >
                <div className="font-bold uppercase text-[9px] mb-1 opacity-50 tracking-wider">
                  {getStageLabel(event.stage)}
                </div>
                <div className="prose prose-invert prose-sm max-w-none text-ops-text/90 leading-relaxed">
                  <ReactMarkdown remarkPlugins={[remarkGfm]}>
                    {cleanText}
                  </ReactMarkdown>
                  {isLastEvent ? <span className="inline-block w-1.5 h-4 ml-1 align-[-2px] bg-ops-cyan/90 animate-pulse" /> : null}
                </div>
              </article>
            )
          }

          const cleanText = stripJsonBlocks(event.text)
          if (!cleanText) return null
          return (
            <article
              key={event.id}
              className="p-3 rounded-lg bg-ops-panel/60 border border-ops-border/20"
            >
              <div className="font-bold uppercase text-[9px] mb-1 opacity-40 tracking-wider">
                {event.kind === 'final' ? 'Conclusion' : 'Assistant'}
              </div>
              <div className="prose prose-invert prose-sm max-w-none text-ops-text/90 leading-relaxed">
                <ReactMarkdown remarkPlugins={[remarkGfm]}>
                  {cleanText}
                </ReactMarkdown>
              </div>
            </article>
          )
        })}
      </div>
    </div>
  )
}
