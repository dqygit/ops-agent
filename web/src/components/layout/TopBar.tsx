import { SecondaryButton } from './Button'

type TopBarProps = {
  onOpenSettings?: () => void
}

export function TopBar({ onOpenSettings }: TopBarProps) {
  return (
    <header className="flex h-[52px] shrink-0 items-center justify-between border-b border-ops-border/50 bg-ops-deep px-4">
      <div className="flex items-center gap-3">
        <div className="inline-flex h-7 min-w-7 items-center justify-center border border-ops-green/35 bg-ops-green/10 px-2 text-[11px] font-semibold uppercase tracking-[0.24em] text-ops-green">
          OPS
        </div>
        <div>
          <h1 className="text-sm font-semibold tracking-[0.08em] text-ops-text">Ops Agent Console</h1>
          <p className="text-[10px] uppercase tracking-[0.18em] text-ops-muted">AI operations workspace</p>
        </div>
      </div>
      <div className="flex items-center gap-3" aria-label="Console status">
        <span className="inline-flex items-center gap-2 text-[11px] uppercase tracking-[0.18em] text-ops-muted">
          <span className="h-2 w-2 rounded-full bg-ops-green shadow-[0_0_10px_rgba(132,204,22,0.6)]" />
          online
        </span>
        <SecondaryButton onClick={onOpenSettings}>Settings</SecondaryButton>
      </div>
    </header>
  )
}
