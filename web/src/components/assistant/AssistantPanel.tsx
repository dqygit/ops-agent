import { PanelCard } from '../layout/PanelCard'
import { SectionHeader } from '../layout/SectionHeader'
import type { EventItem } from '../../types/ops'
import { AssistantActions } from './AssistantActions'
import { ConversationView } from './ConversationView'
import { ModelSelector } from './ModelSelector'
import { PromptInput } from './PromptInput'

type AssistantPanelProps = {
  events: EventItem[]
  models: string[]
  selectedModel: string
  prompt: string
  onModelChange: (model: string) => void
  onPromptChange: (prompt: string) => void
  onRun: () => void
}

export function AssistantPanel({
  events,
  models,
  selectedModel,
  prompt,
  onModelChange,
  onPromptChange,
  onRun,
}: AssistantPanelProps) {
  return (
    <PanelCard fill>
      <SectionHeader
        title="AI Workspace"
        description="Review plans, approvals, and final assistant output"
      />

      <ModelSelector models={models} selectedModel={selectedModel} onModelChange={onModelChange} />

      <ConversationView events={events} />

      <PromptInput prompt={prompt} onPromptChange={onPromptChange} />

      <AssistantActions onRun={onRun} />
    </PanelCard>
  )
}
