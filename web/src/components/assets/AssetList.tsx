import { ListItemCard } from '../layout/ListItemCard'
import type { Asset } from '../../types/ops'

type AssetListProps = {
  assets: Asset[]
  selectedAssetId: number
  onSelectAsset: (assetId: number) => void
}

export function AssetList({ assets, selectedAssetId, onSelectAsset }: AssetListProps) {
  return (
    <ul className="list-panel" aria-label="Assets">
      {assets.map((asset) => {
        const selected = asset.id === selectedAssetId
        return (
          <li key={asset.id}>
            <ListItemCard
              title={asset.name}
              meta={`${asset.assetType.toUpperCase()}  ${asset.host}:${asset.port}`}
              active={selected}
              onClick={() => onSelectAsset(asset.id)}
            />
          </li>
        )
      })}
    </ul>
  )
}
