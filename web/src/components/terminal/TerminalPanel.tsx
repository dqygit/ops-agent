import { PanelCard } from '../layout/PanelCard'
import type { Asset } from '../../types/ops'
import { TerminalHeader } from './TerminalHeader'
import { TerminalOutput } from './TerminalOutput'

type TerminalPanelProps = {
  asset: Asset
  tabs: Asset[]
  activeAssetId: number
  output: string
  onInput: (data: string) => void
  onResize: (cols: number, rows: number) => void
  onSelectTab: (assetId: number) => void
}

export function TerminalPanel({ asset, tabs, activeAssetId, output, onInput, onResize, onSelectTab }: TerminalPanelProps) {
  return (
    <PanelCard className="h-full w-full">
      <TerminalHeader asset={asset} tabs={tabs} activeAssetId={activeAssetId} onSelectTab={onSelectTab} />
      <TerminalOutput sessionKey={String(activeAssetId)} output={output} onInput={onInput} onResize={onResize} />
    </PanelCard>
  )
}
