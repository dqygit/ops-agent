import { SecondaryButton } from './Button'

type TopBarProps = {
  onOpenSettings?: () => void
}

export function TopBar({ onOpenSettings }: TopBarProps) {
  return (
    <header className="h-[50px] border-b border-ops-border/20 bg-ops-strong flex items-center justify-between px-4 shrink-0">
      <div>
        <h1 className="text-sm font-medium text-ops-text">Ops Agent Console</h1>
      </div>
      <div className="flex items-center" aria-label="Console status">
        <SecondaryButton onClick={onOpenSettings}>Settings</SecondaryButton>
      </div>
    </header>
  )
}
