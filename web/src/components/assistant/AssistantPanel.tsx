import { PanelCard } from '../layout/PanelCard'
import { SectionHeader } from '../layout/SectionHeader'
import type { Asset, EventItem } from '../../types/ops'
import { AssistantActions } from './AssistantActions'
import { ConversationView } from './ConversationView'
import { PromptInput } from './PromptInput'

type AssistantPanelProps = {
  events: EventItem[]
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
  const hasApprovalRequest = events.some((event) => event.kind === 'approval')

  return (
    <PanelCard fill>
      <SectionHeader
        title="Agent"
        description="Agent reasoning, command suggestions, and execution output"
      />

      <ConversationView events={events} />

      <PromptInput
        prompt={prompt}
        models={models}
        selectedModel={selectedModel}
        selectedAsset={selectedAsset}
        onPromptChange={onPromptChange}
        onModelChange={onModelChange}
        onRun={onRun}
      />

      {hasApprovalRequest && <AssistantActions onApprove={onApprove} onReject={onReject} />}
    </PanelCard>
  )
}
