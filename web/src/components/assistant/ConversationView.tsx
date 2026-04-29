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
      <div className="conversation-view" aria-label="Assistant conversation">
        <EmptyState
          title="No assistant output"
          description="Choose a model and run an agent task to populate plans, approvals, and results here."
        />
      </div>
    )
  }

  return (
    <div className="conversation-view" aria-label="Assistant conversation">
      {events.map((event) => {
        if (event.kind === 'plan') {
          return (
            <article key={event.id} className="event-card event-plan">
              <h3 className="event-title">Command</h3>
              <ol className="plan-list">
                {event.steps.map((step, index) => (
                  <li key={`${event.id}-${index}`}>
                    <span>{step.title}</span>
                    <code>{step.command}</code>
                  </li>
                ))}
              </ol>
            </article>
          )
        }

        return (
          <article key={event.id} className={`event-card event-${event.kind}`}>
            <h3 className="event-title">{eventTitles[event.kind]}</h3>
            {event.kind === 'output' ? <pre>{event.text}</pre> : <p>{event.text}</p>}
          </article>
        )
      })}
    </div>
  )
}
