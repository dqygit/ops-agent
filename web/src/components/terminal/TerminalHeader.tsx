import type { Asset } from '../../types/ops'

type TerminalHeaderProps = {
  asset: Asset
  tabs: Asset[]
  activeAssetId: number
  onSelectTab: (assetId: number) => void
}

export function TerminalHeader({ asset, tabs, activeAssetId, onSelectTab }: TerminalHeaderProps) {
  return (
    <header className="terminal-header">
      <div className="terminal-tabs" aria-label="Terminal tabs">
        {tabs.map((tabAsset) => {
          const isActive = tabAsset.id === activeAssetId
          const label = tabAsset.name || tabAsset.host || 'Terminal'
          return (
            <button
              key={tabAsset.id}
              type="button"
              className={isActive ? 'terminal-tab terminal-tab-active' : 'terminal-tab terminal-tab-muted'}
              onClick={() => onSelectTab(tabAsset.id)}
            >
              {label}
            </button>
          )
        })}
      </div>
      <div className="terminal-session-meta">
        <div>
          <h2 className="section-title">Terminal Session</h2>
          <p className="section-meta">
            {asset.id === 0 ? asset.name : `${asset.name} · ${asset.host}:${asset.port} · ${asset.assetType}`}
          </p>
        </div>
        <span className="terminal-target">Selected</span>
      </div>
    </header>
  )
}
