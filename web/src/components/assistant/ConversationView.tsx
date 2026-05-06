import { EmptyState } from '../layout/EmptyState'
import type { EventItem } from '../../types/ops'

type ConversationViewProps = {
  events: EventItem[]
}

const eventTitles: Record<Exclude<EventItem['kind'], 'plan'>, string> = {
  status: 'Agent',
  approval: 'Approval',
  output: 'Output',
  final: 'Conclusion',
  error: 'Error',
}

export function ConversationView({ events }: ConversationViewProps) {
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
          return (
            <article key={event.id} className="p-3 rounded-lg bg-ops-panel border border-ops-border/20 text-ops-text text-sm shadow-sm">
              <h3 className="font-medium text-ops-green mb-2">Command Plan</h3>
              <ol className="flex flex-col gap-2 list-none m-0 p-0">
                {event.steps.map((step, index) => (
                  <li key={`${event.id}-${index}`} className="flex flex-col gap-1">
                    <span className="text-ops-muted text-xs font-semibold">{index + 1}. {step.title}</span>
                    <code className="px-2 py-1 rounded bg-black/40 text-ops-cyan border border-ops-border/10 whitespace-pre-wrap word-break shrink-0 font-mono text-[11px] block">{step.command}</code>
                  </li>
                ))}
              </ol>
            </article>
          )
        }

        const colorClasses = {
          status: 'text-ops-muted border-ops-border/20 bg-ops-panel/50',
          approval: 'text-yellow-400 border-yellow-500/30 bg-yellow-500/10',
          output: 'text-ops-text border-ops-border/20 bg-black/40 font-mono text-[11px]',
          final: 'text-ops-green border-ops-green/30 bg-ops-green/10 font-medium',
          error: 'text-red-400 border-red-500/30 bg-red-500/10',
        }[event.kind]

        return (
          <article key={event.id} className={`p-3 rounded-lg border text-sm shadow-sm flex flex-col gap-1.5 ${colorClasses}`}>
            <h3 className="font-medium uppercase text-[10px] tracking-wider opacity-70">{eventTitles[event.kind]}</h3>
            {event.kind === 'output' ? <pre className="whitespace-pre-wrap word-break m-0 font-mono leading-tight">{event.text}</pre> : <p className="m-0">{event.text}</p>}
          </article>
        )
      })}
    </div>
  )
}
