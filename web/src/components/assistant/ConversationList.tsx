import { useAppearance } from '../../hooks/useAppearance'
import type { ConversationSummary, EventItem } from '../../types/ops'

type ConversationListProps = {
  items: ConversationSummary[]
  activeConversationId: string | null
  onSelect: (conversationId: string) => void
  onDelete: (conversationId: string) => void
}

const timeFormatter = new Intl.DateTimeFormat('en-US', {
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
      return { label: 'Approving', color: 'text-ops-warning border-ops-warning/30 bg-ops-warning/10 shadow-glow' }
    case 'approval_decision':
      return { label: 'Decided', color: 'text-ops-cyan border-ops-cyan/30 bg-ops-cyan/10 shadow-glow' }
    case 'error':
      return { label: 'Error', color: 'text-ops-danger border-ops-danger/30 bg-ops-danger/10' }
    case 'final':
      return { label: 'Completed', color: 'text-ops-emerald border-ops-emerald/30 bg-ops-emerald/10 shadow-glow' }
    case 'plan':
      return { label: 'Planning', color: 'text-ops-cyan border-ops-cyan/30 bg-ops-cyan/10' }
    case 'command_start':
    case 'command_chunk':
      return { label: 'Running', color: 'text-ops-cyan border-ops-cyan/40 bg-ops-cyan/10 shadow-glow' }
    case 'command_end':
      return { label: 'Executed', color: 'text-ops-muted border-ops-border/30 bg-ops-panel/50' }
    case 'terminal_status':
      return { label: 'Terminal', color: 'text-ops-muted border-ops-border/30 bg-ops-panel/50' }
    case 'user':
      return { label: 'User', color: 'text-ops-muted border-ops-border/30 bg-ops-panel/50' }
    case 'delta':
      return { label: 'Processing', color: 'text-ops-cyan border-ops-cyan/30 bg-ops-cyan/10' }
    case 'approval':
      return { label: 'Approving', color: 'text-ops-warning border-ops-warning/30 bg-ops-warning/10 shadow-glow' }
    case 'output':
      return { label: 'Result', color: 'text-ops-muted border-ops-border/30 bg-ops-panel/50' }
    case 'status':
      return { label: 'Updating', color: 'text-ops-cyan border-ops-cyan/30 bg-ops-cyan/10' }
    default:
      return { label: 'Empty', color: 'text-ops-muted border-ops-border/30 bg-ops-panel/40' }
  }
}

function getInitial(title: string) {
  const trimmed = (title || '').trim()
  if (!trimmed) return '·'
  // Prioritize first character / letter / digit
  const ch = Array.from(trimmed)[0]
  return ch || '·'
}

export function ConversationList({ items, activeConversationId, onSelect, onDelete }: ConversationListProps) {
  const { t } = useAppearance()

  return (
    <div className="flex h-full flex-col bg-ops-bg" aria-label={t('conversation.list')}>
      <div className="flex-1 overflow-y-auto p-2.5">
        {items.length > 0 ? (
          <ul className="flex flex-col gap-1.5" role="list">
            {items.map((item) => {
              const isActive = item.id === activeConversationId
              const status = getStatusMeta(normalizeStatusKind(item.lastEventKind))
              const isUntitled = !item.title || item.title.trim() === '' || item.title.trim() === 'New'
              const displayTitle = isUntitled ? t('conversation.untitledSession') : item.title

              return (
                <li key={item.id} className="group relative">
                  <button
                    type="button"
                    className={`relative flex w-full items-start gap-3.5 overflow-hidden rounded-xl border px-4 py-4 text-left transition-all duration-300 active:scale-[0.98] ${isActive
                        ? 'border-ops-cyan/40 bg-gradient-to-br from-ops-cyan/15 via-ops-cyan/5 to-transparent shadow-glow'
                        : 'border-transparent bg-transparent hover:border-ops-border/30 hover:bg-ops-panel/40'
                      }`}
                    onClick={() => onSelect(item.id)}
                    title={displayTitle}
                  >
                    {isActive ? (
                      <span
                        className="absolute inset-y-3 left-0 w-[4px] rounded-r-full bg-gradient-to-b from-ops-cyan via-ops-cyan/40 to-ops-cyan shadow-glow"
                        aria-hidden="true"
                      />
                    ) : null}

                    {/* Circle Initial Icon */}
                    <div
                      className={`mt-0.5 flex h-10 w-10 shrink-0 items-center justify-center rounded-xl text-sm font-bold tracking-tight shadow-sm transition-all duration-200 ${isActive
                          ? 'border border-ops-cyan/50 bg-ops-cyan/20 text-ops-cyan shadow-glow'
                          : 'border border-ops-border/30 bg-ops-deep text-ops-muted group-hover:border-ops-cyan/40 group-hover:text-ops-text'
                        }`}
                      aria-hidden="true"
                    >
                      {getInitial(displayTitle)}
                    </div>

                    <div className="min-w-0 flex-1">
                      <div className="flex items-start justify-between gap-2">
                        <h3
                          className={`truncate text-[14px] font-bold leading-tight tracking-tight ${isActive ? 'text-ops-text shadow-sm' : 'text-ops-text/80'
                            } ${isUntitled ? 'italic text-ops-text/40 font-medium' : ''}`}
                        >
                          {displayTitle}
                        </h3>
                      </div>

                      <div className="mt-2 flex items-center gap-2 text-[10px] font-bold leading-none text-ops-muted">
                        <span className="text-ops-border/40" aria-hidden="true">/</span>
                        <span className="shrink-0 opacity-60">{formatUpdatedTime(item.updatedAt)}</span>
          
                      </div>
                    </div>
                  </button>
                  <button
                    type="button"
                    className="absolute right-3 top-3 rounded-lg p-1.5 text-ops-muted opacity-0 transition-all duration-200 hover:bg-ops-danger/20 hover:text-ops-danger group-hover:opacity-100 focus:opacity-100 active:scale-90"
                    onClick={(event) => {
                      event.stopPropagation()
                      onDelete(item.id)
                    }}
                    aria-label={t('conversation.deleteSession', { title: displayTitle })}
                  >
                    <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="3" strokeLinecap="round" strokeLinejoin="round"><path d="M18 6L6 18M6 6l12 12" /></svg>
                  </button>
                </li>
              )
            })}
          </ul>
        ) : (
          <div className="rounded-2xl border border-dashed border-ops-border/20 bg-[linear-gradient(180deg,rgba(34,211,238,0.06),rgba(15,23,42,0.16))] px-4 py-6 text-xs text-ops-muted">
            <div className="flex flex-col gap-3">
              <div className="inline-flex h-10 w-10 items-center justify-center rounded-xl border border-ops-cyan/15 bg-ops-cyan/10 text-ops-cyan text-lg font-black shadow-glow">+</div>
              <div className="text-sm font-bold text-ops-text  tracking-widest">{t('conversation.noSessions')}</div>
              <div className="leading-relaxed text-ops-muted font-medium">{t('conversation.noSessionsDescription')}</div>
            </div>
          </div>
        )}
      </div>
    </div>
  )
}
