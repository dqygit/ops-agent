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
}

export function AssetSidebar({ assets, groups, selectedAssetId, onSelectAsset, onUpdateAsset, onDeleteAsset, onAddAsset }: AssetSidebarProps) {
  return (
    <PanelCard>
      <div className="asset-sidebar-header">
        <div>
          <h2 className="section-title">主机连接</h2>
        </div>
        <button type="button" className="asset-add-button" aria-label="添加主机连接" onClick={onAddAsset}>+</button>
      </div>

      <AssetList assets={assets} groups={groups} selectedAssetId={selectedAssetId} onSelectAsset={onSelectAsset} onUpdateAsset={onUpdateAsset} onDeleteAsset={onDeleteAsset} />
    </PanelCard>
  )
}
