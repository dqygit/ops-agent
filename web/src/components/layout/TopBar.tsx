import { SecondaryButton } from './Button'

type TopBarProps = {
  onOpenSettings?: () => void
}

export function TopBar({ onOpenSettings }: TopBarProps) {
  return (
    <header className="top-bar">
      <div>
        <h1 className="app-title">Ops Agent Console</h1>
      </div>
      <div className="top-status-row" aria-label="Console status">
        <SecondaryButton onClick={onOpenSettings}>Settings</SecondaryButton>
      </div>
    </header>
  )
}
