import type { Asset } from '../../types/ops'

type TerminalHeaderProps = {
  asset: Asset
  tabs: Asset[]
  activeAssetId: number
  onSelectTab: (assetId: number) => void
}

export function TerminalHeader({ asset, tabs, activeAssetId, onSelectTab }: TerminalHeaderProps) {
  return (
    <header className="flex shrink-0 flex-col border-b border-ops-border/40 bg-[#090d0b]">
      <div className="flex gap-1 overflow-x-auto overflow-y-hidden border-b border-ops-border/30 px-2 pt-2" aria-label="终端标签页">
        {tabs.map((tabAsset) => {
          const isActive = tabAsset.id === activeAssetId
          const label = tabAsset.name || tabAsset.host || 'Terminal'
          return (
            <button
              key={tabAsset.id}
              type="button"
              className={`max-w-[160px] truncate rounded-none border border-b-0 px-3 py-1.5 text-xs transition-colors ${isActive ? 'border-ops-green/40 bg-[#0d1410] font-medium text-ops-green' : 'border-transparent bg-transparent text-ops-muted hover:bg-ops-panel/70'}`}
              onClick={() => onSelectTab(tabAsset.id)}
            >
              {label}
            </button>
          )
        })}
      </div>
      <div className="flex items-center justify-between px-4 py-3 text-sm">
        <div>
          <div className="text-[10px] uppercase tracking-[0.24em] text-ops-muted">执行终端</div>
          <h2 className="mt-1 text-sm font-semibold text-ops-text">{asset.name}</h2>
          <p className="mt-1 text-[11px] text-ops-muted">{asset.id === 0 ? asset.name : `${asset.host}:${asset.port} · ${asset.assetType}`}</p>
        </div>
        <span className="inline-flex items-center gap-2 rounded-md border border-ops-green/35 bg-ops-green/10 px-2 py-1 text-[11px] uppercase tracking-[0.12em] text-ops-green">
          <span className="h-1.5 w-1.5 rounded-full bg-ops-green" />
          attached
        </span>
      </div>
    </header>
  )
}
