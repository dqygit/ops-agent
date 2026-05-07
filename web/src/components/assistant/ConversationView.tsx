import { useState } from 'react'
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
  onApprove?: () => void
  onReject?: () => void
}

function getPlanStepStatusClass(status?: 'pending' | 'running' | 'completed') {
  if (status === 'completed') {
    return 'border-ops-green/20 bg-ops-green/5'
  }
  if (status === 'running') {
    return 'border-ops-cyan/30 bg-ops-cyan/10 animate-pulse'
  }
  return 'border-ops-border/10 bg-black/20'
}

function stripAnsi(text: string) {
  return text.replace(/[\u001b\u009b][[[()#;?]*(?:[0-9]{1,4}(?:;[0-9]{0,4})*)?[0-9A-ORZcf-nqry=><]/g, '')
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

export function ConversationView({ events, onApprove, onReject }: ConversationViewProps) {
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

  return (
    <div className="flex-1 overflow-y-auto p-4 flex flex-col gap-6" aria-label="Assistant conversation">
      {events.map((event) => {
        if (event.kind === 'plan') {
          const latestVersion = event.planId
            ? Math.max(...events.filter(isPlanEvent).filter((item) => item.planId === event.planId).map((item) => item.version ?? 0))
            : event.version ?? 0
          const isSuperseded = event.planId ? (event.version ?? 0) < latestVersion : false

          return (
            <article key={event.id} className={`p-4 rounded-xl border text-ops-text text-sm shadow-glass transition-opacity ${isSuperseded ? 'bg-ops-panel/40 border-ops-border/5 opacity-60' : 'bg-ops-panel/80 border-ops-border/30'}`}>
              <div className="flex items-center justify-between gap-3 mb-4">
                <div className="flex items-center gap-2">
                  <div className="w-1.5 h-4 bg-ops-green rounded-full" />
                  <h3 className="font-bold text-ops-text tracking-wide">{event.title?.trim() || 'Task Plan'}</h3>
                </div>
                <div className="flex items-center gap-2 text-[10px] uppercase tracking-wider text-ops-muted">
                  {event.loading ? <span className="text-ops-cyan animate-pulse">● Planning...</span> : null}
                  {typeof event.version === 'number' ? <span className="bg-ops-border/20 px-1.5 py-0.5 rounded">v{event.version}</span> : null}
                </div>
              </div>
              
              <ol className="flex flex-col gap-3 list-none m-0 p-0">
                {event.steps.map((step, index) => (
                  <li key={step.id ?? `${event.id}-${index}`} className={`rounded-lg border px-3 py-2.5 flex flex-col gap-2 transition-colors ${getPlanStepStatusClass(step.status)}`}>
                    <div className="flex items-start gap-3">
                      <div className={`mt-0.5 flex-shrink-0 w-5 h-5 rounded-full flex items-center justify-center text-[10px] font-bold border ${
                        step.status === 'completed' ? 'bg-ops-green border-ops-green text-ops-bg' : 
                        step.status === 'running' ? 'bg-ops-cyan border-ops-cyan text-ops-bg' : 
                        'bg-transparent border-ops-border/30 text-ops-muted'
                      }`}>
                        {step.status === 'completed' ? '✓' : index + 1}
                      </div>
                      <div className="min-w-0 flex-1">
                        <div className={`text-xs font-bold tracking-tight ${step.status === 'completed' ? 'text-ops-muted italic' : 'text-ops-text'}`}>
                          {step.title}
                        </div>
                        {step.summary && !isSuperseded && (
                          <p className="m-0 mt-1 text-[11px] text-ops-muted leading-relaxed">{step.summary}</p>
                        )}
                      </div>
                    </div>
                  </li>
                ))}
              </ol>
            </article>
          )
        }

        if (event.kind === 'status') {
          return <div key={event.id} className="chat-bubble-status">{event.text}</div>
        }

        if (event.kind === 'error') {
          return (
            <article key={event.id} className="chat-bubble chat-bubble-error">
              <div className="font-bold uppercase text-[10px] mb-1">System Error</div>
              <p className="m-0 text-xs font-mono">{event.text}</p>
            </article>
          )
        }

        if (event.kind === 'output') {
          return <OutputBlock key={event.id} text={event.text} />
        }

        const isLastEvent = events[events.length - 1].id === event.id
        const hasSubsequentActivity = events.slice(events.findIndex(e => e.id === event.id) + 1).some(e => e.kind === 'output' || e.kind === 'status' || e.kind === 'final')
        
        const isAssistant = event.kind === 'delta' || event.kind === 'final' || event.kind === 'approval'

        return (
          <article 
            key={event.id} 
            className={`chat-bubble ${isAssistant ? 'chat-bubble-assistant' : 'chat-bubble-agent'} flex flex-col gap-2`}
          >
            <div className="flex items-center justify-between border-b border-ops-border/10 pb-1 mb-1">
              <span className="font-black uppercase text-[9px] tracking-[0.2em] opacity-40">
                {event.kind === 'delta' ? 'Assistant' : event.kind === 'final' ? 'Conclusion' : 'Approval'}
              </span>
            </div>
            
            <div className="prose prose-invert prose-sm max-w-none text-ops-text leading-relaxed">
              <ReactMarkdown remarkPlugins={[remarkGfm]}>
                {event.text}
              </ReactMarkdown>
            </div>

            {event.kind === 'approval' && onApprove && onReject && isLastEvent && !hasSubsequentActivity ? (
              <div className="mt-3 pt-3 border-t border-ops-border/10 flex items-center gap-3">
                <PrimaryButton className="flex-1 shadow-glow" onClick={onApprove}>
                  Approve Execution
                </PrimaryButton>
                <DangerButton className="px-6" onClick={onReject}>
                  Reject
                </DangerButton>
              </div>
            ) : null}
          </article>
        )
      })}
    </div>
  )
}
