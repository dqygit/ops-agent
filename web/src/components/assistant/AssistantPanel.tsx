import { useMemo } from 'react'
import { PanelCard } from '../layout/PanelCard'
import type { RunMode } from '../../types/api'
import type { Asset, ConversationSummary, EventItem, RuntimeSnapshot, RuntimeSummary } from '../../types/ops'
import { ConversationView } from './ConversationView'
import { PromptInput } from './PromptInput'

type AssistantPanelProps = {
  conversationSummaries: ConversationSummary[]
  activeConversationId: string | null
  activeConversationTitle: string
  events: EventItem[]
  pendingApprovalRuntimeId: string | null
  runtimeSummaries: RuntimeSummary[]
  activeRuntimeSnapshot: RuntimeSnapshot | null
  models: string[]
  selectedModel: string
  runMode: RunMode
  prompt: string
  selectedAsset: Asset
  loadError: string | null
  onModelChange: (model: string) => void
  onRunModeChange: (mode: RunMode) => void
  onPromptChange: (prompt: string) => void
  onCreateConversation: () => void
  onSelectConversation: (conversationId: string) => void
  onDeleteConversation: (conversationId: string) => void
  onRun: (prompt: string) => Promise<void>
  onApprove: (allowPrefix?: string) => void
  onReject: () => void
}

const headerTimeFormatter = new Intl.DateTimeFormat('en-US', {
  month: 'short',
  day: '2-digit',
  hour: '2-digit',
  minute: '2-digit',
  hour12: false,
})

function formatHeaderTime(value: string | null) {
  if (!value) {
    return 'JUST NOW'
  }
  const date = new Date(value)
  if (Number.isNaN(date.getTime())) {
    return value
  }
  return headerTimeFormatter.format(date)
}

export function AssistantPanel({
  conversationSummaries,
  activeConversationId,
  activeConversationTitle,
  events,
  pendingApprovalRuntimeId,
  runtimeSummaries,
  activeRuntimeSnapshot,
  models,
  selectedModel,
  runMode,
  prompt,
  selectedAsset,
  loadError,
  onModelChange,
  onRunModeChange,
  onPromptChange,
  onCreateConversation,
  onSelectConversation,
  onDeleteConversation,
  onRun,
  onApprove,
  onReject,
}: AssistantPanelProps) {
  const activeConversation = useMemo(
    () => conversationSummaries.find((item) => item.id === activeConversationId) ?? null,
    [activeConversationId, conversationSummaries],
  )

  return (
    <div className="flex h-full w-full flex-col overflow-hidden bg-ops-bg">
      <header className="relative z-10 flex shrink-0 items-center justify-between border-b border-ops-border/20 bg-ops-panel/80 backdrop-blur-xl px-6 py-4 shadow-2xl">
        <div className="min-w-0 flex-1">
          <h2 className="truncate text-[18px] font-black tracking-tight text-ops-text">
            {activeConversationTitle || 'Unclassified Mission'}
          </h2>
        </div>
        <div className="flex shrink-0 items-center gap-3">
          <button
            type="button"
            className="inline-flex items-center gap-2 rounded-xl border border-ops-cyan/30 bg-ops-cyan/10 px-4 py-2 text-[10px] font-bold tracking-[0.1em] text-ops-cyan shadow-glow transition-all duration-200 hover:bg-ops-cyan/20 active:scale-95"
            onClick={onCreateConversation}
          >
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="3" strokeLinecap="round" strokeLinejoin="round"><line x1="12" y1="5" x2="12" y2="19"></line><line x1="5" y1="12" x2="19" y2="12"></line></svg>
            New Session
          </button>
        </div>
      </header>

      <div className="min-h-0 flex flex-1 overflow-hidden">
        <div className="min-w-0 flex flex-1 flex-col overflow-hidden bg-ops-bg relative">
          <div className="absolute inset-0 bg-[radial-gradient(circle_at_50%_0%,rgba(6,182,212,0.05),transparent_50%)] pointer-events-none" />
          {loadError ? (
            <div className="mx-4 mt-4 rounded-md border border-ops-danger/40 bg-ops-danger/10 px-3 py-2 text-sm text-ops-text" role="alert">
              {loadError}
            </div>
          ) : null}

          <ConversationView events={events} pendingApprovalRuntimeId={pendingApprovalRuntimeId} onApprove={onApprove} onReject={onReject} />

          <PromptInput
            prompt={prompt}
            models={models}
            selectedModel={selectedModel}
            runMode={runMode}
            selectedAsset={selectedAsset}
            onPromptChange={onPromptChange}
            onModelChange={onModelChange}
            onRunModeChange={onRunModeChange}
            onRun={onRun}
          />
        </div>
      </div>
    </div>
  )
}
