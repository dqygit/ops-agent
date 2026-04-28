import { ActionRow } from '../layout/ActionRow'
import { DangerButton, SecondaryButton } from '../layout/Button'
import { PanelCard } from '../layout/PanelCard'
import { SectionHeader } from '../layout/SectionHeader'
import type { Asset, SessionRecord } from '../../types/ops'
import { AssetList } from './AssetList'
import { AssetTabs } from './AssetTabs'
import { HistoryList } from './HistoryList'

type AssetSidebarProps = {
  assets: Asset[]
  history: SessionRecord[]
  selectedAssetId: number
  tab: 'assets' | 'history'
  onSelectAsset: (assetId: number) => void
  onTabChange: (tab: 'assets' | 'history') => void
}

export function AssetSidebar({
  assets,
  history,
  selectedAssetId,
  tab,
  onSelectAsset,
  onTabChange,
}: AssetSidebarProps) {
  return (
    <PanelCard>
      <SectionHeader
        title="Resource Explorer"
        description="Manage assets and reopen previous assistant sessions"
      />

      <AssetTabs tab={tab} onTabChange={onTabChange} />

      <ActionRow>
        <SecondaryButton>Add</SecondaryButton>
        <SecondaryButton>Edit</SecondaryButton>
        <DangerButton>Delete</DangerButton>
      </ActionRow>

      {tab === 'assets' ? (
        <AssetList assets={assets} selectedAssetId={selectedAssetId} onSelectAsset={onSelectAsset} />
      ) : (
        <HistoryList history={history} />
      )}
    </PanelCard>
  )
}
