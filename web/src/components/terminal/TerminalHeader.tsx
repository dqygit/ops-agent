import type { Asset } from '../../types/ops'

type TerminalHeaderProps = {
  asset: Asset
  tabs: Asset[]
  activeAssetId: number
  onSelectTab: (assetId: number) => void
}

export function TerminalHeader({ asset, tabs, activeAssetId, onSelectTab }: TerminalHeaderProps) {
  return (
    <header className="flex flex-col border-b border-ops-border/20 bg-ops-panel shrink-0">
      <div className="flex bg-ops-deep border-b border-ops-border/20 pt-2 px-2 overflow-x-auto overflow-y-hidden gap-1" aria-label="Terminal tabs">
        {tabs.map((tabAsset) => {
          const isActive = tabAsset.id === activeAssetId
          const label = tabAsset.name || tabAsset.host || 'Terminal'
          return (
            <button
              key={tabAsset.id}
              type="button"
              className={`px-4 py-2 text-sm max-w-[200px] truncate rounded-t-lg transition-colors border-t border-x ${isActive ? 'bg-ops-panel text-ops-text border-ops-border/20' : 'bg-transparent text-ops-muted border-transparent hover:bg-ops-panel/50'}`}
              onClick={() => onSelectTab(tabAsset.id)}
            >
              {label}
            </button>
          )
        })}
      </div>
      <div className="px-4 py-2 flex items-center justify-between text-sm">
        <div>
          <h2 className="font-medium text-ops-text">Terminal Session</h2>
          <p className="text-xs text-ops-muted mt-0.5">
            {asset.id === 0 ? asset.name : `${asset.name} · ${asset.host}:${asset.port} · ${asset.assetType}`}
          </p>
        </div>
        <span className="px-2 py-1 rounded bg-ops-cyan/10 text-ops-cyan border border-ops-cyan/20">Selected</span>
      </div>
    </header>
  )
}
