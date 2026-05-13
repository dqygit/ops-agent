import logoUrl from '../../public/logo.png'

type TopBarProps = {
  onOpenSettings?: () => void
}

export function TopBar({ onOpenSettings }: TopBarProps) {
  return (
    <header className="flex h-[60px] shrink-0 items-center justify-between border-b border-ops-border/20 bg-ops-panel/90 backdrop-blur-xl px-6 shadow-2xl z-50">
      <div className="flex items-center gap-5">
        <img
          src={logoUrl}
          alt="Ops Agent"
          className="h-10 w-10 rounded-xl border border-ops-cyan/40 bg-ops-cyan/10 object-cover shadow-glow"
        />
        <div className="hidden sm:block">
          <h1 className="text-[14px] font-black  tracking-[0.05em] text-ops-text leading-tight">Tactical Dashboard</h1>
          <p className="text-[9px]  tracking-[0.2em] text-ops-muted/50 font-bold">Autonomous Agent Orchestrator</p>
        </div>
      </div>
      <div className="flex items-center gap-6" aria-label="System status">
        <button type="button" onClick={onOpenSettings} className="button h-8 px-4 text-[10px] font-bold  tracking-widest active:scale-95">Configuration</button>
      </div>
    </header>
  )
}
