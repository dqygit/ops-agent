import { TopBar } from './TopBar'

type LoadingStateProps = {
  message: string
}

export function LoadingState({ message }: LoadingStateProps) {
  return (
    <div className="app-shell">
      <TopBar />
      <main className="layout-grid">
        <section className="panel-card panel-fill">
          <p className="status-line">{message}</p>
        </section>
      </main>
    </div>
  )
}
