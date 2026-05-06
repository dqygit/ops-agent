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

const eventTitles: Record<Exclude<EventItem['kind'], 'plan'>, string> = {
  status: 'Agent',
  delta: 'Assistant',
  approval: 'Approval',
  output: 'Output',
  final: 'Conclusion',
  error: 'Error',
}

function getPlanStepStatusClass(status?: 'pending' | 'running' | 'completed') {
  if (status === 'completed') {
    return 'border-ops-green/20 bg-ops-green/5'
  }

  if (status === 'running') {
    return 'border-ops-cyan/30 bg-ops-cyan/10'
  }

  return 'border-ops-border/10 bg-black/20'
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
    <div className="flex-1 overflow-y-auto p-4 flex flex-col gap-4" aria-label="Assistant conversation">
      {events.map((event) => {
        if (event.kind === 'plan') {
          const latestVersion = event.planId
            ? Math.max(...events.filter(isPlanEvent).filter((item) => item.planId === event.planId).map((item) => item.version ?? 0))
            : event.version ?? 0
          const isSuperseded = event.planId ? (event.version ?? 0) < latestVersion : false

          return (
            <article key={event.id} className={`p-3 rounded-lg border text-ops-text text-sm shadow-sm ${isSuperseded ? 'bg-ops-panel/50 border-ops-border/10 opacity-75' : 'bg-ops-panel border-ops-border/20'}`}>
              <div className="flex items-center justify-between gap-3 mb-2">
                <h3 className="font-medium text-ops-green">{event.title?.trim() || 'Task Plan'}</h3>
                <div className="flex items-center gap-2 text-[10px] uppercase tracking-wider text-ops-muted">
                  {event.loading ? <span className="rounded-full border border-ops-cyan/20 px-1.5 py-0.5 text-ops-cyan">规划中</span> : null}
                  {typeof event.version === 'number' ? <span>v{event.version}</span> : null}
                  {(event.updated || isSuperseded) ? <span className="rounded-full border border-ops-border/20 px-1.5 py-0.5">已更新</span> : null}
                </div>
              </div>
              {event.loading && event.steps.length === 0 ? (
                <div className="rounded-md border border-ops-cyan/20 bg-ops-cyan/5 px-3 py-2 text-[11px] text-ops-cyan">Planner 正在整理任务计划…</div>
              ) : null}
              <ol className="flex flex-col gap-2 list-none m-0 p-0">
                {event.steps.map((step, index) => (
                  <li key={step.id ?? `${event.id}-${index}`} className={`rounded-md border px-3 py-2 flex flex-col gap-1 ${getPlanStepStatusClass(step.status)}`}>
                    <div className="flex items-start gap-2">
                      <span className={`mt-0.5 text-xs ${step.status === 'completed' ? 'text-ops-green' : step.status === 'running' ? 'text-ops-cyan' : 'text-ops-muted'}`}>
                        {step.status === 'completed' ? '✓' : step.status === 'running' ? '●' : '○'}
                      </span>
                      <div className="min-w-0 flex-1">
                        <div className={`text-xs font-semibold ${step.status === 'completed' ? 'line-through text-ops-muted/80' : 'text-ops-text'}`}>
                          {index + 1}. {step.title}
                        </div>
                        {step.summary ? <p className="m-0 mt-1 text-[11px] text-ops-muted">{step.summary}</p> : null}
                      </div>
                    </div>
                    {step.command ? <code className="px-2 py-1 rounded bg-black/40 text-ops-cyan border border-ops-border/10 whitespace-pre-wrap word-break shrink-0 font-mono text-[11px] block">{step.command}</code> : null}
                    {step.status === 'running' ? <span className="text-[10px] uppercase tracking-wider text-ops-cyan">进行中</span> : null}
                  </li>
                ))}
              </ol>
            </article>
          )
        }

        const colorClasses = {
          status: 'text-ops-muted border-ops-border/20 bg-ops-panel/50',
          delta: 'text-ops-text border-ops-cyan/20 bg-ops-cyan/5',
          approval: 'text-yellow-400 border-yellow-500/30 bg-yellow-500/10',
          output: 'text-ops-text border-ops-border/20 bg-black/40 font-mono text-[11px]',
          final: 'text-ops-green border-ops-green/30 bg-ops-green/10 font-medium',
          error: 'text-red-400 border-red-500/30 bg-red-500/10',
        }[event.kind]

        return (
          <article key={event.id} className={`p-3 rounded-lg border text-sm shadow-sm flex flex-col gap-1.5 ${colorClasses}`}>
            <h3 className="font-medium uppercase text-[10px] tracking-wider opacity-70">{eventTitles[event.kind]}</h3>
            {event.kind === 'output' ? <pre className="whitespace-pre-wrap word-break m-0 font-mono leading-tight">{event.text}</pre> : <p className="m-0">{event.text}</p>}
            {event.kind === 'approval' && onApprove && onReject ? (
              <div className="mt-2 flex items-center gap-2 self-start">
                <PrimaryButton className="min-w-[88px] px-3 py-1.5 text-xs" onClick={onApprove}>
                  Approve
                </PrimaryButton>
                <DangerButton className="min-w-[88px] px-3 py-1.5 text-xs" onClick={onReject}>
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
