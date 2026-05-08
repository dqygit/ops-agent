import { useState } from 'react'
import type { AssetPayload } from '../../api'
import { PanelCard } from '../layout/PanelCard'
import type { Asset, AssetGroup, ConversationSummary } from '../../types/ops'
import { ConversationList } from '../assistant/ConversationList'
import { AssetList } from './AssetList'

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
  const [activeTab, setActiveTab] = useState<'assets' | 'conversations'>('assets')

  return (
    <PanelCard className={`h-full flex flex-col border-r border-ops-border/20 bg-ops-panel transition-[width] duration-200 ${collapsed ? 'w-[72px]' : 'w-[320px]'}`}>
      <div className={`relative flex items-center border-b border-ops-border/40 px-3 py-3 ${collapsed ? 'justify-center' : 'justify-between'}`}>
        {collapsed ? (
          <button
            type="button"
            className="absolute -right-3 top-3 inline-flex h-7 w-7 items-center justify-center rounded-full border border-ops-green/30 bg-[#0d1410] text-ops-green shadow-[0_0_16px_rgba(132,204,22,0.18)] transition-colors hover:bg-ops-green/18"
            aria-label="展开导航抽屉"
            onClick={onToggleCollapse}
          >
            <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M9 18l6-6-6-6"></path></svg>
          </button>
        ) : (
          <>
            <div>
              <h2 className="text-sm font-semibold text-ops-text">主机与会话</h2>
            </div>
            <div className="flex items-center gap-2">
              <button type="button" className="inline-flex h-8 w-8 items-center justify-center rounded-md border border-ops-border/60 bg-ops-panel text-ops-muted transition-colors hover:border-ops-green/40 hover:text-ops-green" aria-label="收起导航抽屉" onClick={onToggleCollapse}>
                <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M15 18l-6-6 6-6"></path></svg>
              </button>
              <button type="button" className="inline-flex h-8 w-8 items-center justify-center rounded-md border border-ops-border/60 bg-ops-panel text-ops-muted transition-colors hover:border-ops-green/40 hover:text-ops-green" aria-label="添加主机连接" onClick={onAddAsset}>
                <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M12 5v14M5 12h14"></path></svg>
              </button>
            </div>
          </>
        )}
      </div>

      <div className={`border-b border-ops-border/30 bg-[#0a0f0c] ${collapsed ? 'flex flex-col items-center gap-2 px-2 py-3' : 'grid grid-cols-2 gap-2 px-3 py-2'}`}>
        <button
          type="button"
          className={`rounded-md border transition-colors ${collapsed ? 'inline-flex h-10 w-10 items-center justify-center px-0 py-0' : 'px-3 py-2 text-xs'} ${activeTab === 'assets' ? 'border-ops-green/30 bg-ops-green/12 text-ops-green' : 'border-transparent text-ops-muted hover:bg-ops-panel/70 hover:text-ops-text'}`}
          onClick={() => setActiveTab('assets')}
          aria-label="资产连接"
          title="资产连接"
        >
          {collapsed ? (
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true"><rect x="3" y="4" width="18" height="6" rx="1.5"></rect><rect x="3" y="14" width="18" height="6" rx="1.5"></rect><path d="M7 7h.01M7 17h.01"></path></svg>
          ) : '资产连接'}
        </button>
        <button
          type="button"
          className={`rounded-md border transition-colors ${collapsed ? 'inline-flex h-10 w-10 items-center justify-center px-0 py-0' : 'px-3 py-2 text-xs'} ${activeTab === 'conversations' ? 'border-ops-green/30 bg-ops-green/12 text-ops-green' : 'border-transparent text-ops-muted hover:bg-ops-panel/70 hover:text-ops-text'}`}
          onClick={() => setActiveTab('conversations')}
          aria-label="会话历史"
          title="会话历史"
        >
          {collapsed ? (
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true"><path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"></path></svg>
          ) : '会话历史'}
        </button>
      </div>

      <div className="min-h-0 flex-1 overflow-hidden">
        {collapsed ? (
          <div className="h-full overflow-y-auto overflow-x-hidden px-2 py-3">
            {activeTab === 'assets' ? (
              <div className="flex flex-col gap-2">
                {assets.map((asset) => (
                  <button
                    key={asset.id}
                    type="button"
                    className={`group relative flex w-full flex-col items-center rounded-lg border px-2 py-2.5 transition-all ${
                      asset.id === selectedAssetId
                        ? 'border-ops-green/40 bg-ops-green/12 shadow-[0_0_12px_rgba(132,204,22,0.15)]'
                        : 'border-ops-border/30 bg-[#0b110d] hover:border-ops-green/25 hover:bg-ops-green/8'
                    }`}
                    onClick={() => onSelectAsset(asset.id)}
                    title={asset.name}
                  >
                    <svg
                      width="18"
                      height="18"
                      viewBox="0 0 24 24"
                      fill="none"
                      stroke="currentColor"
                      strokeWidth="1.8"
                      strokeLinecap="round"
                      strokeLinejoin="round"
                      className={asset.id === selectedAssetId ? 'text-ops-green' : 'text-ops-muted group-hover:text-ops-green'}
                    >
                      <rect x="3" y="4" width="18" height="6" rx="1.5"></rect>
                      <rect x="3" y="14" width="18" height="6" rx="1.5"></rect>
                      <path d="M7 7h.01M7 17h.01"></path>
                    </svg>
                    <div className={`mt-1.5 w-full truncate text-center text-[10px] font-medium ${
                      asset.id === selectedAssetId ? 'text-ops-green' : 'text-ops-text group-hover:text-ops-green'
                    }`}>
                      {asset.name}
                    </div>
                  </button>
                ))}
              </div>
            ) : (
              <div className="flex flex-col gap-2">
                {conversationSummaries.map((conversation) => (
                  <button
                    key={conversation.id}
                    type="button"
                    className={`group relative flex w-full flex-col items-center rounded-lg border px-2 py-2.5 transition-all ${
                      conversation.id === activeConversationId
                        ? 'border-ops-green/40 bg-ops-green/12 shadow-[0_0_12px_rgba(132,204,22,0.15)]'
                        : 'border-ops-border/30 bg-[#0b110d] hover:border-ops-green/25 hover:bg-ops-green/8'
                    }`}
                    onClick={() => onSelectConversation(conversation.id)}
                    title={conversation.title}
                  >
                    <svg
                      width="18"
                      height="18"
                      viewBox="0 0 24 24"
                      fill="none"
                      stroke="currentColor"
                      strokeWidth="1.8"
                      strokeLinecap="round"
                      strokeLinejoin="round"
                      className={conversation.id === activeConversationId ? 'text-ops-green' : 'text-ops-muted group-hover:text-ops-green'}
                    >
                      <path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"></path>
                    </svg>
                    <div className={`mt-1.5 w-full truncate text-center text-[10px] font-medium ${
                      conversation.id === activeConversationId ? 'text-ops-green' : 'text-ops-text group-hover:text-ops-green'
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
    </PanelCard>
  )
}
