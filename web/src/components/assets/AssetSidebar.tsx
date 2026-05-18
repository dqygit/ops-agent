import { useState } from 'react'
import type { AssetPayload } from '../../api'
import { PanelCard } from '../layout/PanelCard'
import type { Asset, AssetGroup, ConversationSummary } from '../../types/ops'
import { ConversationList } from '../assistant/ConversationList'
import { AssetList } from './AssetList'
import { useAppearance } from '../../hooks/useAppearance'

type AssetSidebarProps = {
  assets: Asset[]
  groups: AssetGroup[]
  conversationSummaries: ConversationSummary[]
  activeConversationId: string | null
  selectedAssetId: number
  collapsed: boolean
  onToggleCollapse: () => void
  onSelectAsset: (assetId: number) => void
  onSelectConversation: (conversationId: string) => void
  onDeleteConversation: (conversationId: string) => void
  onUpdateAsset: (assetId: number, payload: AssetPayload) => Promise<Asset>
  onDeleteAsset: (assetId: number) => Promise<void>
  onAddAsset: () => void
  onEditAsset?: (asset: Asset) => void
  onDeleteAssetConfirm?: (asset: Asset) => void
}

export function AssetSidebar({ assets, groups, conversationSummaries, activeConversationId, selectedAssetId, collapsed, onToggleCollapse, onSelectAsset, onSelectConversation, onDeleteConversation, onUpdateAsset, onDeleteAsset, onAddAsset, onEditAsset, onDeleteAssetConfirm }: AssetSidebarProps) {
  const { t } = useAppearance()
  const [activeTab, setActiveTab] = useState<'assets' | 'conversations'>('assets')

  return (
    <div className={`h-full flex flex-col border-r border-ops-border/30 bg-slate-50/70 backdrop-blur-sm transition-[width] duration-300 ease-in-out dark:border-ops-border/40 dark:bg-ops-panel/50 ${collapsed ? 'w-[72px]' : 'w-[300px]'}`}>
      <div className={`relative h-[66px] flex items-center border-b border-ops-border/15 bg-ops-deep px-4 py-4 dark:border-ops-border/30 dark:bg-transparent ${collapsed ? 'justify-center' : 'justify-between'}`}>
        {collapsed ? (
          <button
            type="button"
            className="absolute -right-3.5 top-5 inline-flex h-7 w-7 items-center justify-center rounded-full border border-ops-cyan/40 bg-ops-bg text-ops-cyan shadow-glow transition-all duration-200 hover:scale-110 active:scale-95"
            aria-label={t('assets.expandNavigation')}
            onClick={onToggleCollapse}
          >
            <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="3" strokeLinecap="round" strokeLinejoin="round"><path d="M9 18l6-6-6-6"></path></svg>
          </button>
        ) : (
          <>
            <div>
              <h2 className="text-[12px] font-bold tracking-[0.15em] text-ops-cyan/90">{t('assets.navigationTitle')}</h2>
            </div>
            <div className="flex items-center gap-2">
              <button type="button" className="inline-flex h-8 w-8 items-center justify-center rounded-lg border border-ops-border/50 bg-ops-deep/50 text-ops-muted transition-all duration-200 hover:border-ops-cyan/50 hover:text-ops-cyan active:scale-90" aria-label={t('assets.collapseNavigation')} onClick={onToggleCollapse}>
                <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round"><path d="M15 18l-6-6 6-6"></path></svg>
              </button>
              <button type="button" className="inline-flex h-8 w-8 items-center justify-center rounded-lg border border-ops-border/50 bg-ops-deep/50 text-ops-muted transition-all duration-200 hover:border-ops-cyan/50 hover:text-ops-cyan active:scale-90" aria-label={t('assets.addNodeConnection')} onClick={onAddAsset}>
                <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round"><path d="M12 5v14M5 12h14"></path></svg>
              </button>
            </div>
          </>
        )}
      </div>

      <div className={`border-b border-ops-border/15 bg-ops-deep dark:border-ops-border/20 dark:bg-ops-bg/40 ${collapsed ? 'flex flex-col items-center gap-3 px-2 py-4' : 'grid grid-cols-2 gap-2 px-3 py-2.5'}`}>
        <button
          type="button"
          className={`rounded-lg border transition-all duration-200 active:scale-95 ${collapsed ? 'inline-flex h-10 w-10 items-center justify-center' : 'px-3 py-2 text-[11px] font-bold  tracking-wider'} ${activeTab === 'assets' ? 'border-ops-cyan/40 bg-ops-cyan/10 text-ops-cyan shadow-[inset_0_1px_0_rgba(255,255,255,0.05)]' : 'border-transparent text-ops-muted hover:bg-ops-panel/60 hover:text-ops-text'}`}
          onClick={() => setActiveTab('assets')}
          aria-label={t('assets.nodeAssets')}
          title={t('assets.nodeAssets')}
        >
          {collapsed ? (
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true"><rect x="3" y="4" width="18" height="6" rx="1.5"></rect><rect x="3" y="14" width="18" height="6" rx="1.5"></rect><path d="M7 7h.01M7 17h.01"></path></svg>
          ) : t('assets.nodes')}
        </button>
        <button
          type="button"
          className={`rounded-lg border transition-all duration-200 active:scale-95 ${collapsed ? 'inline-flex h-10 w-10 items-center justify-center' : 'px-3 py-2 text-[11px] font-bold  tracking-wider'} ${activeTab === 'conversations' ? 'border-ops-cyan/40 bg-ops-cyan/10 text-ops-cyan shadow-[inset_0_1px_0_rgba(255,255,255,0.05)]' : 'border-transparent text-ops-muted hover:bg-ops-panel/60 hover:text-ops-text'}`}
          onClick={() => setActiveTab('conversations')}
          aria-label={t('assets.history')}
          title={t('assets.history')}
        >
          {collapsed ? (
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true"><path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"></path></svg>
          ) : t('assets.history')}
        </button>
      </div>

      <div className="min-h-0 flex-1 overflow-hidden">
        {collapsed ? (
          <div className="h-full overflow-y-auto overflow-x-hidden px-2 py-4">
            {activeTab === 'assets' ? (
              <div className="flex flex-col gap-3">
                {assets.map((asset) => (
                  <button
                    key={asset.id}
                    type="button"
                    className={`group relative flex w-full flex-col items-center rounded-xl border p-2 transition-all duration-200 active:scale-90 ${asset.id === selectedAssetId
                        ? 'border-ops-cyan/50 bg-ops-cyan/10 shadow-glow'
                        : 'border-ops-border/20 bg-ops-bg/40 hover:border-ops-cyan/30 hover:bg-ops-cyan/5'
                      }`}
                    onClick={() => onSelectAsset(asset.id)}
                    title={asset.name}
                  >
                    <svg
                      width="20"
                      height="20"
                      viewBox="0 0 24 24"
                      fill="none"
                      stroke="currentColor"
                      strokeWidth="2"
                      strokeLinecap="round"
                      strokeLinejoin="round"
                      className={asset.id === selectedAssetId ? 'text-ops-cyan' : 'text-ops-muted group-hover:text-ops-cyan'}
                    >
                      <rect x="3" y="4" width="18" height="6" rx="1.5"></rect>
                      <rect x="3" y="14" width="18" height="6" rx="1.5"></rect>
                      <path d="M7 7h.01M7 17h.01"></path>
                    </svg>
                    <div className={`mt-2 w-full truncate text-center text-[10px] font-bold tracking-tighter ${asset.id === selectedAssetId ? 'text-ops-cyan' : 'text-ops-text/70 group-hover:text-ops-cyan'
                      }`}>
                      {asset.name}
                    </div>
                  </button>
                ))}
              </div>
            ) : (
              <div className="flex flex-col gap-3">
                {conversationSummaries.map((conversation) => (
                  <button
                    key={conversation.id}
                    type="button"
                    className={`group relative flex w-full flex-col items-center rounded-xl border p-2 transition-all duration-200 active:scale-90 ${conversation.id === activeConversationId
                        ? 'border-ops-cyan/50 bg-ops-cyan/10 shadow-glow'
                        : 'border-ops-border/20 bg-ops-bg/40 hover:border-ops-cyan/30 hover:bg-ops-cyan/5'
                      }`}
                    onClick={() => onSelectConversation(conversation.id)}
                    title={conversation.title}
                  >
                    <svg
                      width="20"
                      height="20"
                      viewBox="0 0 24 24"
                      fill="none"
                      stroke="currentColor"
                      strokeWidth="2"
                      strokeLinecap="round"
                      strokeLinejoin="round"
                      className={conversation.id === activeConversationId ? 'text-ops-cyan' : 'text-ops-muted group-hover:text-ops-cyan'}
                    >
                      <path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"></path>
                    </svg>
                    <div className={`mt-2 w-full truncate text-center text-[10px] font-bold tracking-tighter ${conversation.id === activeConversationId ? 'text-ops-cyan' : 'text-ops-text/70 group-hover:text-ops-cyan'
                      }`}>
                      {conversation.title}
                    </div>
                  </button>
                ))}
              </div>
            )}
          </div>
        ) : activeTab === 'assets' ? (
          <div className="h-full overflow-y-auto overflow-x-hidden">
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
        ) : (
          <div className="h-full overflow-hidden">
            <ConversationList
              items={conversationSummaries}
              activeConversationId={activeConversationId}
              onSelect={onSelectConversation}
              onDelete={onDeleteConversation}
            />
          </div>
        )}
      </div>
    </div>
  )
}
