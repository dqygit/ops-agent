import { EmptyState } from '../layout/EmptyState'
import type { EventItem } from '../../types/ops'

type ConversationViewProps = {
  events: EventItem[]
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
            <article key={event.id} className="event-card">
              <h3 className="event-title">Plan</h3>
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
            <p>{event.text}</p>
          </article>
        )
      })}
    </div>
  )
}
