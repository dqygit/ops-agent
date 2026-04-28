import { SecondaryButton } from './Button'

export function TopBar() {
  return (
    <header className="top-bar">
      <div>
        <h1 className="app-title">Ops Agent Console</h1>
        <p className="app-subtitle">Assets, terminal sessions, and assistant workflows</p>
      </div>
      <SecondaryButton>Settings</SecondaryButton>
    </header>
  )
}
