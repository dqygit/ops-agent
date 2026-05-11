import { SecondaryButton } from './Button'

type TopBarProps = {
  onOpenSettings?: () => void
}

export function TopBar({ onOpenSettings }: TopBarProps) {
  return (
    <header className="flex h-[60px] shrink-0 items-center justify-between border-b border-ops-border/20 bg-ops-panel/90 backdrop-blur-xl px-6 shadow-2xl z-50">
      <div className="flex items-center gap-5">
        <div className="inline-flex h-8 items-center justify-center border border-ops-cyan/50 bg-ops-cyan/10 px-3 text-[12px] font-black  tracking-[0.2em] text-ops-cyan shadow-glow rounded-md">
          Core Ops
        </div>
        <div className="hidden sm:block">
          <h1 className="text-[14px] font-black  tracking-[0.05em] text-ops-text leading-tight">Tactical Dashboard</h1>
          <p className="text-[9px]  tracking-[0.2em] text-ops-muted/50 font-bold">Autonomous Agent Orchestrator</p>
        </div>
      </div>
      <div className="flex items-center gap-6" aria-label="System status">
        <div className="flex items-center gap-6 pr-6 border-r border-ops-border/10">
          <span className="inline-flex items-center gap-2 text-[9px] font-bold  tracking-[0.15em] text-ops-emerald/80">
            <span className="h-1.5 w-1.5 rounded-full bg-ops-emerald shadow-glow animate-pulse" />
            Core: Linked
          </span>
          <span className="hidden lg:inline-flex items-center gap-2 text-[9px] font-bold  tracking-[0.15em] text-ops-cyan/80">
            <span className="h-1.5 w-1.5 rounded-full bg-ops-cyan shadow-glow animate-pulse" />
            Neural: Active
          </span>
        </div>
        <button type="button" onClick={onOpenSettings} className="button h-8 px-4 text-[10px] font-bold  tracking-widest active:scale-95">Configuration</button>
      </div>
    </header>
  )
}
