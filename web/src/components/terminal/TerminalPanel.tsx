import { PanelCard } from '../layout/PanelCard'
import type { Asset } from '../../types/ops'
import { TerminalHeader } from './TerminalHeader'
import { TerminalOutput } from './TerminalOutput'

type TerminalPanelProps = {
  asset: Asset
  tabs: Asset[]
  activeAssetId: number
  output: string
  busyCommand: string | null
  onInput: (data: string) => void
  onResize: (cols: number, rows: number) => void
  onSelectTab: (assetId: number) => void
  onCloseTab: (assetId: number) => void
  onClear: () => void
  onCopy: () => void
  onReconnect: () => void
}

export function TerminalPanel({
  asset,
  tabs,
  activeAssetId,
  output,
  busyCommand,
  onInput,
  onResize,
  onSelectTab,
  onCloseTab,
  onClear,
  onCopy,
  onReconnect,
}: TerminalPanelProps) {
  return (
    <div className="h-full w-full border-l border-ops-border/25 bg-slate-50/70 shadow-[inset_1px_0_0_rgb(255_255_255/0.65)] flex flex-col overflow-hidden dark:border-ops-border/40 dark:bg-ops-deep dark:shadow-inner">
      <TerminalHeader
        asset={asset}
        tabs={tabs}
        activeAssetId={activeAssetId}
        busyCommand={busyCommand}
        onSelectTab={onSelectTab}
        onCloseTab={onCloseTab}
        onClear={onClear}
        onCopy={onCopy}
        onReconnect={onReconnect}
      />
      <TerminalOutput sessionKey={String(activeAssetId)} output={output} onInput={onInput} onResize={onResize} />
    </div>
  )
}
