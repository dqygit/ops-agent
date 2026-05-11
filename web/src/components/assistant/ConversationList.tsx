import type { ConversationSummary, EventItem } from '../../types/ops'

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

type StatusMeta = { label: string; color: string }

type EventKind = EventItem['kind']
type KnownEventKind = EventKind | 'approval' | 'output' | 'status'

const KNOWN_EVENT_KIND_SET: ReadonlySet<KnownEventKind> = new Set<KnownEventKind>([
  'delta',
  'plan',
  'approval_required',
  'approval_decision',
  'command_start',
  'command_chunk',
  'command_end',
  'terminal_status',
  'final',
  'error',
  'user',
  'approval',
  'output',
  'status',
])

function normalizeStatusKind(kind: string | null): KnownEventKind | null {
  if (!kind) {
    return null
  }
  return KNOWN_EVENT_KIND_SET.has(kind as KnownEventKind) ? (kind as KnownEventKind) : null
}

function getStatusMeta(kind: KnownEventKind | null): StatusMeta {
  switch (kind) {
    case 'approval_required':
      return { label: '待审批', color: 'text-amber-400 border-amber-400/40 bg-amber-400/10' }
    case 'approval_decision':
      return { label: '已决策', color: 'text-ops-cyan border-ops-cyan/30 bg-ops-cyan/10' }
    case 'error':
      return { label: '错误', color: 'text-ops-red border-ops-danger/45 bg-ops-danger/10' }
    case 'final':
      return { label: '完成', color: 'text-ops-green border-ops-green/40 bg-ops-green/10' }
    case 'plan':
      return { label: '规划中', color: 'text-ops-cyan border-ops-cyan/40 bg-ops-cyan/10' }
    case 'command_start':
    case 'command_chunk':
      return { label: '执行中', color: 'text-ops-cyan border-ops-cyan/30 bg-ops-cyan/10' }
    case 'command_end':
      return { label: '命令结束', color: 'text-ops-text/80 border-ops-border/30 bg-black/20' }
    case 'terminal_status':
      return { label: '终端状态', color: 'text-ops-text/80 border-ops-border/30 bg-black/20' }
    case 'user':
      return { label: '已发起', color: 'text-ops-text/80 border-ops-border/30 bg-black/20' }
    case 'delta':
      return { label: '处理中', color: 'text-ops-cyan border-ops-cyan/30 bg-ops-cyan/10' }
    case 'approval':
      return { label: '待审批', color: 'text-amber-400 border-amber-400/40 bg-amber-400/10' }
    case 'output':
      return { label: '已执行', color: 'text-ops-text/80 border-ops-border/30 bg-black/20' }
    case 'status':
      return { label: '处理中', color: 'text-ops-cyan border-ops-cyan/30 bg-ops-cyan/10' }
    default:
      return { label: '空会话', color: 'text-ops-muted border-ops-border/30 bg-black/15' }
  }
}

function getInitial(title: string) {
  const trimmed = (title || '').trim()
  if (!trimmed) return '·'
  // 优先使用第一个汉字 / 字母 / 数字
  const ch = Array.from(trimmed)[0]
  return ch || '·'
}

export function ConversationList({ items, activeConversationId, onSelect, onDelete }: ConversationListProps) {
  return (
    <div className="flex h-full flex-col bg-[#070b09]" aria-label="会话列表">
      <div className="flex-1 overflow-y-auto p-2.5">
        {items.length > 0 ? (
          <ul className="flex flex-col gap-1.5" role="list">
            {items.map((item) => {
              const isActive = item.id === activeConversationId
              const status = getStatusMeta(normalizeStatusKind(item.lastEventKind))
              const isUntitled = !item.title || item.title.trim() === '' || item.title.trim() === 'New'
              const displayTitle = isUntitled ? '未命名会话' : item.title

              return (
                <li key={item.id} className="group relative">
                  <button
                    type="button"
                    className={`relative flex w-full items-start gap-2.5 overflow-hidden rounded-lg border px-3 py-3 text-left transition-all ${
                      isActive
                        ? 'border-ops-green/55 bg-gradient-to-br from-ops-green/12 via-ops-green/6 to-transparent shadow-[0_0_0_1px_rgba(34,197,94,0.18)]'
                        : 'border-transparent bg-transparent hover:border-ops-border/40 hover:bg-ops-panel/55'
                    }`}
                    onClick={() => onSelect(item.id)}
                    title={displayTitle}
                  >
                    {isActive ? (
                      <span
                        className="absolute inset-y-2 left-0 w-[3px] rounded-r-full bg-gradient-to-b from-ops-green via-ops-cyan to-ops-green/40"
                        aria-hidden="true"
                      />
                    ) : null}

                    {/* 圆形首字图标 */}
                    <div
                      className={`mt-0.5 flex h-9 w-9 shrink-0 items-center justify-center rounded-md text-sm font-semibold tracking-tight ${
                        isActive
                          ? 'border border-ops-green/45 bg-ops-green/15 text-ops-green'
                          : 'border border-ops-border/40 bg-black/30 text-ops-text/80 group-hover:border-ops-border/60'
                      }`}
                      aria-hidden="true"
                    >
                      {getInitial(displayTitle)}
                    </div>

                    <div className="min-w-0 flex-1">
                      <div className="flex items-start justify-between gap-2">
                        <h3
                          className={`truncate text-[13.5px] font-semibold leading-snug tracking-[-0.005em] ${
                            isActive ? 'text-ops-text' : 'text-ops-text/95'
                          } ${isUntitled ? 'italic text-ops-text/55' : ''}`}
                        >
                          {displayTitle}
                        </h3>
                      </div>

                      <div className="mt-1 flex items-center gap-1.5 text-[11px] leading-tight text-ops-muted">
                        <span
                          className={`inline-flex shrink-0 items-center rounded-full border px-1.5 py-[1px] text-[10px] font-medium uppercase tracking-[0.06em] ${status.color}`}
                        >
                          {status.label}
                        </span>
                        <span className="text-ops-border/60" aria-hidden="true">·</span>
                        <span className="shrink-0">{formatUpdatedTime(item.updatedAt)}</span>
                        <span className="text-ops-border/60" aria-hidden="true">·</span>
                        <span className="shrink-0 tabular-nums text-ops-muted/85">{item.eventCount} 条</span>
                      </div>
                    </div>
                  </button>
                  <button
                    type="button"
                    className="absolute right-2 top-2 rounded-md p-1 text-ops-muted opacity-0 transition-all hover:bg-ops-danger/15 hover:text-ops-danger group-hover:opacity-100 focus:opacity-100"
                    onClick={(event) => {
                      event.stopPropagation()
                      onDelete(item.id)
                    }}
                    aria-label={`删除会话 ${displayTitle}`}
                  >
                    <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M18 6L6 18M6 6l12 12" /></svg>
                  </button>
                </li>
              )
            })}
          </ul>
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
