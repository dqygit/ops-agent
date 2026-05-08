import type { ConversationSummary } from '../../types/ops'

type ConversationListProps = {
  items: ConversationSummary[]
  activeConversationId: string | null
  onSelect: (conversationId: string) => void
  onDelete: (conversationId: string) => void
}

const timeFormatter = new Intl.DateTimeFormat('zh-CN', {
  month: '2-digit',
  day: '2-digit',
  hour: '2-digit',
  minute: '2-digit',
})

function formatUpdatedTime(value: string) {
  const date = new Date(value)
  if (Number.isNaN(date.getTime())) {
    return value
  }
  return timeFormatter.format(date)
}

function getEventKindLabel(kind: string | null) {
  if (kind === 'approval') return '待审批'
  if (kind === 'error') return '错误'
  if (kind === 'final') return '完成'
  if (kind === 'plan') return '计划'
  if (kind === 'output') return '输出'
  if (kind === 'user') return '提问'
  if (kind === 'delta') return '处理中'
  return '空会话'
}

export function ConversationList({ items, activeConversationId, onSelect, onDelete }: ConversationListProps) {
  return (
    <div className="flex h-full flex-col bg-[#070b09]" aria-label="会话列表">

      <div className="flex-1 overflow-y-auto p-2.5">
        {items.length > 0 ? (
          <div className="flex flex-col gap-2">
            {items.map((item) => {
              const isActive = item.id === activeConversationId
              return (
                <div key={item.id} className="group relative">
                  <button
                    type="button"
                    className={`relative w-full overflow-hidden border-l-2 px-3 py-3 text-left transition-colors ${
                      isActive
                        ? 'border-l-ops-green bg-ops-green/8'
                        : 'border-l-transparent bg-transparent hover:bg-ops-panel/70'
                    }`}
                    onClick={() => onSelect(item.id)}
                    title={item.title}
                  >
                    {isActive ? <span className="absolute inset-y-3 left-0 w-0.5 rounded-full bg-ops-cyan shadow-[0_0_12px_rgba(34,211,238,0.7)]" aria-hidden="true" /> : null}
                    <div className="flex items-start justify-between gap-3">
                      <div className="min-w-0 flex-1">

                        <div className="truncate text-sm font-medium tracking-[0.01em] text-ops-text">{item.title}</div>
                        <div className="mt-1 flex items-center gap-2 text-[11px] text-ops-muted">
                          <span>{formatUpdatedTime(item.updatedAt)}</span>
                          <span className="text-ops-border/60">•</span>
                          <span>{item.eventCount} 条事件</span>
                        </div>
                        
                      </div>
                    
                    </div>
                    <div className="mt-2 flex items-center justify-between gap-2">
                      <div className="inline-flex rounded-lg border border-ops-border/10 bg-black/15 px-2 py-1 text-[10px] uppercase tracking-[0.12em] text-ops-text/65">
                        {getEventKindLabel(item.lastEventKind)}
                      </div>
                      <div className="h-px flex-1 bg-gradient-to-r from-ops-border/10 to-transparent" aria-hidden="true" />
                    </div>
                  </button>
                  <button
                    type="button"
                    className="absolute right-2 top-2 rounded-md p-1 text-ops-muted opacity-0 transition-all hover:bg-ops-danger/10 hover:text-ops-danger group-hover:opacity-100"
                    onClick={() => onDelete(item.id)}
                    aria-label={`删除会话 ${item.title}`}
                  >
                    ×
                  </button>
                </div>
              )
            })}
          </div>
        ) : (
          <div className="rounded-2xl border border-dashed border-ops-border/20 bg-[linear-gradient(180deg,rgba(34,211,238,0.06),rgba(15,23,42,0.16))] px-3 py-5 text-xs text-ops-muted">
            <div className="flex flex-col gap-2">
              <div className="inline-flex h-8 w-8 items-center justify-center rounded-xl border border-ops-cyan/15 bg-ops-cyan/10 text-ops-cyan">+</div>
              <div className="text-sm font-medium text-ops-text">还没有会话</div>
              <div className="leading-5 text-ops-muted">先新建一个会话，把当前排障或执行任务单独收进去，后面切换会更清楚。</div>
            </div>
          </div>
        )}
      </div>
    </div>
  )
}
