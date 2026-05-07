import { PanelCard } from '../layout/PanelCard'
import { SectionHeader } from '../layout/SectionHeader'
import type { Asset, EventItem } from '../../types/ops'
import { ConversationView } from './ConversationView'
import { PromptInput } from './PromptInput'

type AssistantPanelProps = {
  events: EventItem[]
  pendingApprovalRunId: string | null
  models: string[]
  selectedModel: string
  prompt: string
  selectedAsset: Asset
  onModelChange: (model: string) => void
  onPromptChange: (prompt: string) => void
  onRun: () => void
  onApprove: () => void
  onReject: () => void
}

export function AssistantPanel({
  events,
  pendingApprovalRunId,
  models,
  selectedModel,
  prompt,
  selectedAsset,
  onModelChange,
  onPromptChange,
  onRun,
  onApprove,
  onReject,
}: AssistantPanelProps) {
  return (
    <PanelCard className="w-full h-full border-l border-ops-border/20 flex flex-col">
      <SectionHeader
        title="Agent"
        description="Agent reasoning, command suggestions, and execution output"
      />

      <ConversationView events={events} pendingApprovalRunId={pendingApprovalRunId} onApprove={onApprove} onReject={onReject} />

      <PromptInput
        prompt={prompt}
        models={models}
        selectedModel={selectedModel}
        selectedAsset={selectedAsset}
        onPromptChange={onPromptChange}
        onModelChange={onModelChange}
        onRun={onRun}
      />
    </PanelCard>
  )
}
