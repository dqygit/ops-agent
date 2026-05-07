import type { AssetPayload } from '../../api'
import { PanelCard } from '../layout/PanelCard'
import type { Asset, AssetGroup } from '../../types/ops'
import { AssetList } from './AssetList'

type AssetSidebarProps = {
  assets: Asset[]
  groups: AssetGroup[]
  selectedAssetId: number
  onSelectAsset: (assetId: number) => void
  onUpdateAsset: (assetId: number, payload: AssetPayload) => Promise<Asset>
  onDeleteAsset: (assetId: number) => Promise<void>
  onAddAsset: () => void
  onEditAsset?: (asset: Asset) => void
  onDeleteAssetConfirm?: (asset: Asset) => void
}

export function AssetSidebar({ assets, groups, selectedAssetId, onSelectAsset, onUpdateAsset, onDeleteAsset, onAddAsset, onEditAsset, onDeleteAssetConfirm }: AssetSidebarProps) {
  return (
    <PanelCard className="w-full h-full flex flex-col border-r border-ops-border/20 bg-ops-panel">
      <div className="flex items-center justify-between p-4 border-b border-ops-border/20">
        <div>
          <h2 className="text-sm font-medium text-ops-text">主机连接</h2>
        </div>
        <button type="button" className="w-6 h-6 flex items-center justify-center rounded hover:bg-ops-border/50 text-ops-muted hover:text-ops-text transition-colors" aria-label="添加主机连接" onClick={onAddAsset}>
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M12 5v14M5 12h14"></path></svg>
        </button>
      </div>

      <div className="flex-1 overflow-y-auto overflow-x-hidden">
        <AssetList
          assets={assets}
          groups={groups}
          selectedAssetId={selectedAssetId}
          onSelectAsset={onSelectAsset}
          onUpdateAsset={onUpdateAsset}
          onDeleteAsset={onDeleteAsset}
          onEditAsset={onEditAsset}
          onDeleteAssetConfirm={onDeleteAssetConfirm}
        />
      </div>
    </PanelCard>
  )
}
