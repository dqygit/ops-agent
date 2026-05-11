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
              <span
                className={`inline-flex items-center gap-1 rounded-md border px-2 py-1 text-[10.5px] font-medium uppercase tracking-[0.06em] ${
                  runMode === 'plan'
                    ? 'border-ops-cyan/35 bg-ops-cyan/10 text-ops-cyan'
                    : 'border-ops-green/35 bg-ops-green/10 text-ops-green'
                }`}
                title={runMode === 'plan' ? '先生成任务步骤，再逐步交给 Agent 执行；每完成一步都会更新计划状态' : '由 Agent 按需调用命令直接执行，边执行边推进任务'}
              >
                {runMode === 'plan' ? (
                  <svg width="10" height="10" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.4" strokeLinecap="round" strokeLinejoin="round"><rect x="3" y="11" width="18" height="11" rx="2"></rect><path d="M7 11V7a5 5 0 0110 0v4"></path></svg>
                ) : (
                  <svg width="10" height="10" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.4" strokeLinecap="round" strokeLinejoin="round"><circle cx="12" cy="12" r="3" /><path d="M12 1v6M12 17v6M1 12h6M17 12h6" /></svg>
                )}
                {runMode === 'plan' ? 'Plan' : 'Agent'} 模式
              </span>
              <span>{selectedAsset.host}</span>
              <span className="text-ops-border/70">•</span>
              <span>{selectedModel || '未选择模型'}</span>
              <span className="text-ops-border/70">•</span>
              <span>{activeConversation?.eventCount ?? events.length} 条事件</span>
              <span className="text-ops-border/70">•</span>
              <span>{runtimeSummaries.length} 条 runtime</span>
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
          <div className="rounded-md border border-ops-border/40 bg-ops-panel px-3 py-2">状态：{activeRuntimeSnapshot?.status ?? (pendingApprovalRuntimeId ? '待审批' : events.length > 0 ? '处理中 / 已执行' : '空闲')}</div>
          <div className="rounded-md border border-ops-border/40 bg-ops-panel px-3 py-2">更新于 {formatHeaderTime(activeConversation?.updatedAt ?? null)}</div>
          <div className="rounded-md border border-ops-border/40 bg-ops-panel px-3 py-2">Runtime：{activeRuntimeSnapshot?.runtimeId ?? '未激活'}</div>
        </div>
      </header>

      <div className="min-h-0 flex flex-1 overflow-hidden">
        <div className="min-w-0 flex flex-1 flex-col overflow-hidden bg-ops-panel">
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
    </PanelCard>
  )
}
