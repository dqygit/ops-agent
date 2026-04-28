import { PanelCard } from '../layout/PanelCard'
import type { Asset } from '../../types/ops'
import { TerminalActions } from './TerminalActions'
import { TerminalHeader } from './TerminalHeader'
import { TerminalOutput } from './TerminalOutput'

type TerminalPanelProps = {
  asset: Asset
  output: string
}

export function TerminalPanel({ asset, output }: TerminalPanelProps) {
  return (
    <PanelCard fill>
      <TerminalHeader />

      <p className="status-line">
        Target: {asset.name} @ {asset.host}:{asset.port}
      </p>

      <TerminalActions />

      <TerminalOutput output={output} />
    </PanelCard>
  )
}
