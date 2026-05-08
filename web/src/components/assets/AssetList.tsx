import { useState } from 'react'
import { ListItemCard } from '../layout/ListItemCard'
import type { Asset, AssetGroup } from '../../types/ops'

type AssetListProps = {
  assets: Asset[]
  groups: AssetGroup[]
  selectedAssetId: number
  onSelectAsset: (assetId: number) => void
  onUpdateAsset?: (assetId: number, payload: any) => Promise<any>
  onDeleteAsset?: (assetId: number) => Promise<void>
  onEditAsset?: (asset: Asset) => void
  onDeleteAssetConfirm?: (asset: Asset) => void
}

type AssetListGroup = {
  id: number | null
  label: string
}

function getAssetMeta(asset: Asset): string {
  return asset.assetType === 'local_terminal' ? '本地终端' : `${asset.host}:${asset.port}`
}

export function AssetList({ assets, groups, selectedAssetId, onSelectAsset, onEditAsset, onDeleteAssetConfirm }: AssetListProps) {
  const [menuAssetId, setMenuAssetId] = useState<number | null>(null)
  const visibleAssets = assets.filter((asset) => asset.assetType !== 'local_terminal')
  
  const assetGroups: AssetListGroup[] = [
    ...groups.map((group) => ({ id: group.id, label: group.name })),
    { id: null, label: '未分组' },
  ]
  
  const groupedAssets = visibleAssets.reduce<Record<string, Asset[]>>(
    (grouped, asset) => {
      const key = String(asset.groupId)
      grouped[key] = [...(grouped[key] ?? []), asset]
      return grouped
    },
    {},
  )

  return (
    <div className="flex h-full flex-col bg-[#070b09]" aria-label="主机连接列表" onMouseLeave={() => setMenuAssetId(null)}>
      {visibleAssets.length === 0 ? <p className="text-center py-10 text-ops-muted text-sm">空</p> : null}
      {assetGroups.map((group) => {
        const groupKey = String(group.id)
        const groupAssets = groupedAssets[groupKey] ?? []
        if (groupAssets.length === 0) {
          return null
        }

        return (
          <section key={groupKey} className="mb-2" aria-label={group.label}>
            <h3 className="border-y border-ops-border/25 bg-[#0a0f0c] px-4 py-1.5 text-[10px] font-semibold uppercase tracking-[0.22em] text-ops-muted/80">{group.label}</h3>
            <ul className="flex flex-col list-none m-0 p-0">
              {groupAssets.map((asset) => {
                const selected = asset.id === selectedAssetId
                const menuOpen = asset.id === menuAssetId

                return (
                  <li key={asset.id} className="relative group">
                    <div className={`relative flex items-center transition-colors ${selected ? 'bg-ops-green/6' : 'hover:bg-ops-panel/50'} ${menuOpen ? 'bg-ops-panel' : ''}`}>
                      <ListItemCard
                        title={asset.name}
                        meta={getAssetMeta(asset)}
                        active={selected}
                        onClick={() => onSelectAsset(asset.id)}
                        onContextMenu={(event) => {
                          event.preventDefault()
                          setMenuAssetId(asset.id)
                        }}
                      />

                      <button
                        type="button"
                        className={`absolute right-2 p-1.5 rounded transition-all z-10 ${
                          menuOpen ? 'opacity-100 bg-ops-border/20 text-ops-cyan' : 'opacity-0 group-hover:opacity-100 text-ops-muted hover:text-ops-text hover:bg-ops-border/10'
                        }`}
                        aria-label={`${asset.name} 操作`}
                        onClick={(event) => {
                          event.stopPropagation()
                          setMenuAssetId((current) => (current === asset.id ? null : asset.id))
                        }}
                      >
                        <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
                          <circle cx="12" cy="12" r="1"></circle>
                          <circle cx="12" cy="5" r="1"></circle>
                          <circle cx="12" cy="19" r="1"></circle>
                        </svg>
                      </button>
                    </div>

                    {menuOpen ? (
                      <div className="absolute right-2 top-9 z-20 w-32 overflow-hidden rounded-md border border-ops-border/50 bg-[#0c110e] shadow-[0_8px_24px_rgba(0,0,0,0.35)]" role="menu" aria-label={`${asset.name} 操作`}>
                        <button
                          type="button"
                          className="w-full text-left px-3 py-1.5 text-xs text-ops-text hover:bg-ops-cyan hover:text-ops-bg transition-colors flex items-center gap-2"
                          role="menuitem"
                          onClick={() => {
                            onEditAsset?.(asset)
                            setMenuAssetId(null)
                          }}
                        >
                          <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><path d="M11 4H4a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2v-7"></path><path d="M18.5 2.5a2.121 2.121 0 0 1 3 3L12 15l-4 1 1-4 9.5-9.5z"></path></svg>
                          编辑信息
                        </button>
                        <button
                          type="button"
                          className="w-full text-left px-3 py-1.5 text-xs text-ops-danger hover:bg-ops-danger hover:text-white transition-colors flex items-center gap-2"
                          role="menuitem"
                          onClick={() => {
                            onDeleteAssetConfirm?.(asset)
                            setMenuAssetId(null)
                          }}
                        >
                          <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><polyline points="3 6 5 6 21 6"></polyline><path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"></path><line x1="10" y1="11" x2="10" y2="17"></line><line x1="14" y1="11" x2="14" y2="17"></line></svg>
                          删除资产
                        </button>
                      </div>
                    ) : null}
                  </li>
                )
              })}
            </ul>
          </section>
        )
      })}
    </div>
  )
}
