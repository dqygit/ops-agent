import { useMemo } from 'react'
import { PanelCard } from '../layout/PanelCard'
import type { Asset, ConversationSummary, EventItem } from '../../types/ops'
import { ConversationView } from './ConversationView'
import { PromptInput } from './PromptInput'

type AssistantPanelProps = {
  conversationSummaries: ConversationSummary[]
  activeConversationId: string | null
  activeConversationTitle: string
  events: EventItem[]
  pendingApprovalRunId: string | null
  models: string[]
  selectedModel: string
  prompt: string
  selectedAsset: Asset
  loadError: string | null
  onModelChange: (model: string) => void
  onPromptChange: (prompt: string) => void
  onCreateConversation: () => void
  onSelectConversation: (conversationId: string) => void
  onDeleteConversation: (conversationId: string) => void
  onRun: (prompt: string) => Promise<void>
  onApprove: () => void
  onReject: () => void
}

const headerTimeFormatter = new Intl.DateTimeFormat('zh-CN', {
  month: '2-digit',
  day: '2-digit',
  hour: '2-digit',
  minute: '2-digit',
})

function formatHeaderTime(value: string | null) {
  if (!value) {
    return '刚刚'
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
  pendingApprovalRunId,
  models,
  selectedModel,
  prompt,
  selectedAsset,
  loadError,
  onModelChange,
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
    <PanelCard className="w-full h-full border-l border-ops-border/20 flex flex-col overflow-hidden bg-[radial-gradient(circle_at_top,rgba(34,211,238,0.08),transparent_28%),linear-gradient(180deg,rgba(15,23,42,0.28),rgba(15,23,42,0))]">
      <header className="relative flex shrink-0 flex-col gap-3 border-b border-ops-border/40 bg-[#0a0f0c] px-4 py-4">
        <div className="flex items-start justify-between gap-4">
          <div className="min-w-0">
            <div className="text-[10px] uppercase tracking-[0.24em] text-ops-muted">AI 作战台</div>
            <div className="mt-1 truncate text-base font-semibold text-ops-text">{activeConversationTitle || '新会话'}</div>
            <div className="mt-2 flex flex-wrap items-center gap-2 text-[11px] text-ops-muted">
              <span className="inline-flex items-center gap-2 rounded-md border border-ops-green/30 bg-ops-green/10 px-2 py-1 text-ops-green">
                <span className="h-1.5 w-1.5 rounded-full bg-ops-green" />
                {selectedAsset.name}
              </span>
              <span>{selectedAsset.host}</span>
              <span className="text-ops-border/70">•</span>
              <span>{selectedModel || '未选择模型'}</span>
              <span className="text-ops-border/70">•</span>
              <span>{activeConversation?.eventCount ?? events.length} 条事件</span>
            </div>
          </div>
          <div className="flex items-center gap-2">
            <button
              type="button"
              className="button button-primary px-3 py-1.5 text-xs"
              onClick={onCreateConversation}
            >
              新建会话
            </button>
          </div>
        </div>
        <div className="grid grid-cols-3 gap-2 text-[11px] text-ops-muted">
          <div className="rounded-md border border-ops-border/40 bg-ops-panel px-3 py-2">状态：{pendingApprovalRunId ? '待审批' : events.length > 0 ? '处理中 / 已执行' : '空闲'}</div>
          <div className="rounded-md border border-ops-border/40 bg-ops-panel px-3 py-2">更新于 {formatHeaderTime(activeConversation?.updatedAt ?? null)}</div>
          <div className="rounded-md border border-ops-border/40 bg-ops-panel px-3 py-2">模型：{selectedModel || '未选择模型'}</div>
        </div>
      </header>

      <div className="min-h-0 flex flex-1 overflow-hidden">
        <div className="min-w-0 flex flex-1 flex-col overflow-hidden bg-ops-panel">
          {loadError ? (
            <div className="mx-4 mt-4 rounded-md border border-ops-danger/40 bg-ops-danger/10 px-3 py-2 text-sm text-ops-text" role="alert">
              {loadError}
            </div>
          ) : null}

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
        </div>
      </div>
    </PanelCard>
  )
}
