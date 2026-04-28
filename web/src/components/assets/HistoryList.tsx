import { EmptyState } from '../layout/EmptyState'
import { ListItemCard } from '../layout/ListItemCard'
import type { SessionRecord } from '../../types/ops'

type HistoryListProps = {
  history: SessionRecord[]
}

export function HistoryList({ history }: HistoryListProps) {
  if (history.length === 0) {
    return (
      <div className="list-panel" aria-label="Session history">
        <EmptyState
          title="No session history"
          description="Select another asset or run a new assistant task to create session records."
        />
      </div>
    )
  }

  return (
    <ul className="list-panel" aria-label="Session history">
      {history.map((session) => (
        <li key={session.id}>
          <ListItemCard title={session.title} meta={`Model: ${session.model}`} />
        </li>
      ))}
    </ul>
  )
}
