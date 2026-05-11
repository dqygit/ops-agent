import { useEffect, useMemo, useRef, useState } from 'react'
import ReactMarkdown from 'react-markdown'
import remarkGfm from 'remark-gfm'
import { EmptyState } from '../layout/EmptyState'
import type { ApprovalEvent, EventItem, PlanEvent } from '../../types/ops'

type ConversationViewProps = {
  events: EventItem[]
  pendingApprovalRuntimeId: string | null
  onApprove?: () => void
  onReject?: () => void
}

type DeltaEvent = Extract<EventItem, { kind: 'delta' }>
type CommandStart = Extract<EventItem, { kind: 'command_start' }>
type CommandChunk = Extract<EventItem, { kind: 'command_chunk' }>
type CommandEnd = Extract<EventItem, { kind: 'command_end' }>
type Approval = Extract<EventItem, { kind: 'approval_required' | 'approval_decision' }>

type Group =
  | { type: 'event'; event: EventItem }
  | { type: 'thinking'; deltas: DeltaEvent[]; key: string }
  | {
      type: 'command'
      key: string
      approvalEvent?: Approval
      startEvent?: CommandStart
      chunkEvents: CommandChunk[]
      endEvent?: CommandEnd
    }

function sortAssistantGroups(groups: Group[]): Group[] {
  const thinkingGroups = groups.filter((group) => group.type === 'thinking')
  const commandGroups = groups.filter((group) => group.type === 'command')
  const eventGroups = groups.filter((group) => group.type === 'event')
  return [...thinkingGroups, ...commandGroups, ...eventGroups]
}

const STAGE_ORDER = ['assistant'] as const
const STAGE_LABEL: Record<string, string> = {
  assistant: 'AI 输出',
}
const STAGE_ICON_COLOR: Record<string, string> = {
  assistant: 'text-ops-cyan',
}

function stripAnsi(text: string) {
  return text.replace(/[\u001b\u009b][[()#;?]*(?:[0-9]{1,4}(?:;[0-9]{0,4})*)?[0-9A-ORZcf-nqry=><]/g, '')
}

function stripJsonBlocks(text: string) {
  let result = text

  const markerIndex = result.indexOf('<FINAL_JSON>')
  if (markerIndex >= 0) {
    result = result.slice(0, markerIndex)
  }

  result = result.replace(/```json\s*[\s\S]*?```/gi, '')
  result = result.replace(/\{\s*"(?:steps|decision|summary|title|reason|risk_level|expected_output|command)"[\s\S]*?\}/g, '')

  const jsonTailPatterns = [
    /\n\s*\{\s*"(?:steps|decision|summary|title|reason|risk_level|expected_output|command)"[\s\S]*$/,
    /\n\s*\[\s*\{[\s\S]*$/,
    /\n\s*"(?:title|reason|risk_level|expected_output|command|decision|summary)"\s*:[\s\S]*$/,
  ]

  for (const pattern of jsonTailPatterns) {
    result = result.replace(pattern, '')
  }

  result = result
    .split('\n')
    .filter((line) => {
      const trimmed = line.trim()
      if (!trimmed) return true
      if (/^[\[{].*[\]}]$/.test(trimmed)) return false
      if (/^"(?:title|reason|risk_level|expected_output|command|decision|summary)"\s*:/.test(trimmed)) return false
      if (/^[\]}],?$/.test(trimmed)) return false
      return true
    })
    .join('\n')

  result = result
    .replace(/[，,、。；;:：\-\s]+$/g, '')
    .replace(/([，,、]){2,}/g, '$1')
    .replace(/\n{3,}/g, '\n\n')

  return result.trim()
}

const PROSE_CLASS =
  'prose prose-invert prose-sm max-w-none text-[14px] leading-7 text-ops-text/95 ' +
  '[&>*:first-child]:mt-0 [&>*:last-child]:mb-0 ' +
  '[&_h1]:text-lg [&_h1]:font-bold [&_h1]:text-ops-text [&_h1]:mb-2 [&_h1]:mt-3 ' +
  '[&_h2]:text-base [&_h2]:font-bold [&_h2]:text-ops-text [&_h2]:mb-2 [&_h2]:mt-3 ' +
  '[&_h3]:text-sm [&_h3]:font-semibold [&_h3]:text-ops-text/95 [&_h3]:mb-1.5 [&_h3]:mt-2.5 ' +
  '[&_p]:my-2 [&_ul]:my-2 [&_ul]:space-y-1 [&_ol]:my-2 [&_ol]:space-y-1 ' +
  '[&_li]:leading-6 [&_li]:text-ops-text/90 ' +
  '[&_code]:bg-black/40 [&_code]:px-1.5 [&_code]:py-0.5 [&_code]:rounded [&_code]:text-ops-cyan [&_code]:text-[13px] [&_code]:font-mono ' +
  '[&_pre]:bg-black/60 [&_pre]:p-3 [&_pre]:rounded-md [&_pre]:border [&_pre]:border-ops-border/20 [&_pre]:my-2.5 ' +
  '[&_pre>code]:bg-transparent [&_pre>code]:p-0 [&_pre>code]:text-ops-text/90 ' +
  '[&_blockquote]:border-l-4 [&_blockquote]:border-ops-cyan/40 [&_blockquote]:pl-3 [&_blockquote]:italic [&_blockquote]:text-ops-text/80 ' +
  '[&_strong]:font-bold [&_strong]:text-ops-text [&_em]:italic ' +
  '[&_a]:text-ops-cyan [&_a]:underline hover:[&_a]:text-ops-cyan/80'

type OutputBlockProps = {
  text: string
  label?: string
}

function OutputBlock({ text, label = '命令输出' }: OutputBlockProps) {
  const [isExpanded, setIsExpanded] = useState(false)
  const cleanText = stripAnsi(text)
  const lines = cleanText.split('\n')
  const shouldTruncate = lines.length > 8

  return (
    <div className="flex w-full flex-col gap-1 overflow-hidden">
      <div className="flex items-center justify-between rounded-t border-x border-t border-ops-border/10 bg-black/40 px-2 py-1">
        <span className="text-[10px] font-bold uppercase tracking-widest text-ops-muted">{label}</span>
        {shouldTruncate ? (
          <button
            type="button"
            onClick={() => setIsExpanded(!isExpanded)}
            className="text-[10px] text-ops-cyan hover:underline"
          >
            {isExpanded ? '收起' : `展开（${lines.length} 行）`}
          </button>
        ) : null}
      </div>
      <pre
        className={`m-0 whitespace-pre-wrap rounded-b border-x border-b border-ops-border/10 bg-black/60 p-3 font-mono text-[11px] leading-tight text-ops-text/90 transition-all ${
          !isExpanded && shouldTruncate ? 'relative max-h-[160px] overflow-hidden' : 'max-h-none'
        }`}
      >
        {cleanText}
        {!isExpanded && shouldTruncate ? <div className="pointer-events-none absolute inset-x-0 bottom-0 h-12 bg-gradient-to-t from-black/80 to-transparent" /> : null}
      </pre>
    </div>
  )
}

type CommandExecutionCardProps = {
  approvalEvent?: Approval
  startEvent?: CommandStart
  chunkEvents: CommandChunk[]
  endEvent?: CommandEnd
  pendingApprovalRuntimeId: string | null
  onApprove?: () => void
  onReject?: () => void
}

function CommandExecutionCard({ approvalEvent, startEvent, chunkEvents, endEvent, pendingApprovalRuntimeId, onApprove, onReject }: CommandExecutionCardProps) {
  const outputText = chunkEvents.map((event) => event.text).join('')
  const exitCode = endEvent?.exitCode
  const command = startEvent?.command || approvalEvent?.command || ''
  const title = startEvent?.title?.trim() || (approvalEvent ? '命令审批' : '终端命令')
  const approvalStatus = approvalEvent?.status ?? (approvalEvent ? 'pending' : undefined)
  const showApprovalActions = approvalStatus === 'pending' && approvalEvent?.runtimeId !== undefined && pendingApprovalRuntimeId !== null && approvalEvent.runtimeId === pendingApprovalRuntimeId
  const statusLabel = endEvent
    ? exitCode === null || exitCode === 0
      ? '已完成'
      : `失败（退出码 ${exitCode}）`
    : approvalStatus === 'rejected'
      ? '已拒绝'
      : approvalStatus === 'approved'
        ? '已批准'
        : approvalStatus === 'pending'
          ? '待审批'
          : '执行中'
  const statusClass = endEvent
    ? exitCode === null || exitCode === 0
      ? 'bg-ops-green/15 text-ops-green'
      : 'bg-ops-danger/15 text-ops-red'
    : approvalStatus === 'rejected'
      ? 'bg-ops-danger/15 text-ops-red'
      : approvalStatus === 'approved'
        ? 'bg-ops-green/15 text-ops-green'
        : approvalStatus === 'pending'
          ? 'bg-amber-500/15 text-amber-300'
          : 'bg-ops-cyan/15 text-ops-cyan animate-pulse'

  return (
    <div className="my-1 rounded-md border border-ops-border/20 bg-black/20 p-3 shadow-inner">
      <div className="mb-3 flex items-center justify-between gap-3">
        <div>
          <div className="flex items-center gap-1.5 text-[10px] font-bold uppercase tracking-wider text-ops-cyan/90">
            <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round"><polyline points="4 17 10 11 4 5"></polyline><line x1="12" y1="19" x2="20" y2="19"></line></svg>
            命令执行
          </div>
          <div className="mt-1 text-sm font-semibold text-ops-text">{title}</div>
        </div>
        <div className={`rounded px-2 py-1 text-[10px] font-bold ${statusClass}`}>
          {statusLabel}
        </div>
      </div>
      {command ? (
        <code className="mb-3 block rounded-md border border-ops-border/20 bg-black/40 px-3 py-2 text-xs text-ops-text/90">
          {command}
        </code>
      ) : null}
      {approvalEvent ? (
        <div className="mb-3 rounded-md border border-amber-500/30 bg-amber-500/10 px-3 py-2 text-xs text-ops-text/85">
          <div className="mb-1 flex items-center justify-between gap-2">
            <span className="text-[10px] uppercase tracking-wider text-amber-200/80">
              {approvalStatus === 'approved' ? '已批准' : approvalStatus === 'rejected' ? '已拒绝' : '待处理'}
            </span>
          </div>
          {approvalEvent.reason ? <div className="mb-2 text-ops-text/70">{approvalEvent.reason}</div> : null}
          
          {showApprovalActions ? (
            <div className="flex items-center justify-between gap-3">
              <button type="button" onClick={onApprove} className="rounded-md bg-ops-green/25 px-3 py-1.5 text-[11px] font-semibold text-ops-green transition hover:bg-ops-green/35">
                批准
              </button>

              <button type="button" onClick={onReject} className="rounded-md bg-ops-red/25 px-3 py-1.5 text-[11px] font-semibold text-ops-red transition hover:bg-ops-red/35">
                拒绝
              </button>
            </div>
          ) : null}
        </div>
      ) : null}
      {outputText ? <OutputBlock text={outputText} label="流式输出" /> : null}
    </div>
  )
}

type PlanSummaryCardProps = {
  event: PlanEvent
}

function PlanSummaryCard({ event }: PlanSummaryCardProps) {
  const isPlanMode = event.mode === 'plan'
  const totalSteps = event.steps.length
  const completedSteps = event.steps.filter((step) => step.status === 'completed').length
  const runningStep = event.steps.find((step) => step.status === 'running')
  const progress = totalSteps > 0 ? Math.round((completedSteps / totalSteps) * 100) : 0

  return (
    <div className="rounded-lg border border-ops-border/40 bg-gradient-to-br from-[#0a0f0c] to-[#0d1410] p-3 shadow-sm">
      <div className="mb-2.5 flex items-center justify-between gap-3">
        <div className="flex items-center gap-2">
          <div className={`h-3.5 w-1.5 rounded-full ${isPlanMode ? 'bg-ops-cyan' : 'bg-ops-green'}`} />
          <h3 className="text-[13.5px] font-bold tracking-wide text-ops-text">{event.title?.trim() || '任务计划'}</h3>
          {isPlanMode && event.lockedPlan ? (
            <span className="inline-flex items-center gap-1 rounded-md border border-ops-cyan/35 bg-ops-cyan/10 px-1.5 py-0.5 text-[10px] font-medium text-ops-cyan">
              <svg width="10" height="10" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.4" strokeLinecap="round" strokeLinejoin="round"><rect x="3" y="11" width="18" height="11" rx="2"></rect><path d="M7 11V7a5 5 0 0110 0v4"></path></svg>
              已锁定
            </span>
          ) : null}
        </div>
        <div className="flex items-center gap-2 text-[10px] uppercase tracking-wider text-ops-muted">
          {event.loading ? <span className="animate-pulse text-ops-cyan">● 规划中</span> : null}
          {totalSteps > 0 ? (
            <span className="tabular-nums">
              {completedSteps}/{totalSteps}
            </span>
          ) : null}
          {typeof event.version === 'number' && event.version > 0 ? (
            <span className="rounded bg-ops-border/20 px-1.5 py-0.5">v{event.version}</span>
          ) : null}
        </div>
      </div>

      {totalSteps > 0 ? (
        <div className="mb-2.5 h-1 overflow-hidden rounded-full bg-ops-border/15">
          <div
            className={`h-full rounded-full transition-all duration-500 ${isPlanMode ? 'bg-gradient-to-r from-ops-cyan via-ops-cyan/80 to-emerald-400' : 'bg-gradient-to-r from-ops-green to-emerald-400'}`}
            style={{ width: `${progress}%` }}
          />
        </div>
      ) : null}

      <ol className="flex flex-col gap-1">
        {event.steps.map((step, index) => {
          const isRunning = step.status === 'running' || (runningStep === undefined && index === completedSteps && step.status === 'pending')
          return (
            <li
              key={step.id ?? `step-${index}`}
              className={`flex items-start gap-2.5 rounded-md border px-2.5 py-1.5 text-[12px] transition-colors ${
                step.status === 'completed'
                  ? 'border-ops-green/25 bg-ops-green/5 text-ops-green'
                  : isRunning
                    ? 'border-ops-cyan/35 bg-ops-cyan/8 text-ops-cyan shadow-[0_0_0_1px_rgba(34,211,238,0.18)]'
                    : 'border-ops-border/20 bg-black/15 text-ops-muted'
              }`}
              title={step.title}
            >
              <span className="flex h-4 w-4 shrink-0 items-center justify-center rounded-full text-[10px] font-bold">
                {step.status === 'completed' ? '✓' : index + 1}
              </span>
              <span className="min-w-0 flex-1 truncate font-medium">{step.title}</span>
              {isRunning ? <span className="shrink-0 text-[10px] uppercase tracking-wider text-ops-cyan/80 animate-pulse">执行中</span> : null}
            </li>
          )
        })}
      </ol>
    </div>
  )
}

type ThinkingChainProps = {
  deltas: DeltaEvent[]
  isStreaming: boolean
}

function ThinkingChain({ deltas, isStreaming }: ThinkingChainProps) {
  const stageContent = useMemo(() => {
    const out: Record<string, string> = {}
    for (const d of deltas) {
      const stage = d.stage || 'assistant'
      if (out[stage]) {
        out[stage] += '\n\n'
      } else {
        out[stage] = ''
      }
      out[stage] += stripJsonBlocks(d.text || '')
    }
    return out
  }, [deltas])

  const visibleStages = STAGE_ORDER.filter((s) => (stageContent[s] || '').trim().length > 0)
  if (visibleStages.length === 0) return null
  
  // 对于流式的组合卡片我们只需要展示纯 markdown
  const activeText = visibleStages.map(stage => stageContent[stage]).join('\n\n')

  return (
    <div className={PROSE_CLASS}>
      <ReactMarkdown remarkPlugins={[remarkGfm]}>{activeText}</ReactMarkdown>
      {isStreaming ? <span className="ml-1 inline-block h-3.5 w-1.5 animate-pulse align-[-2px] rounded-sm bg-ops-cyan/85" /> : null}
    </div>
  )
}

type EventCardProps = {
  event: EventItem
  pendingApprovalRuntimeId: string | null
  onApprove?: () => void
  onReject?: () => void
}

function EventCard({ event, pendingApprovalRuntimeId, onApprove, onReject }: EventCardProps) {
  if (event.kind === 'error') {
    return (
      <div className="my-1 rounded-md border border-ops-danger/40 bg-ops-danger/10 p-3">
        <div className="mb-1 text-[10px] font-bold uppercase text-ops-red">系统错误</div>
        <p className="m-0 font-mono text-xs text-ops-text/90">{event.text}</p>
      </div>
    )
  }

  if (event.kind === 'user') {
    return (
      <div className="flex justify-end">
        <article className="max-w-[85%] rounded-lg border border-ops-cyan/40 bg-gradient-to-br from-ops-cyan/12 to-ops-cyan/6 px-3.5 py-2.5 shadow-sm">
          <div className="mb-0.5 text-[9.5px] font-bold uppercase tracking-[0.16em] text-ops-cyan/90">你</div>
          <p className="m-0 whitespace-pre-wrap text-[14px] leading-6 text-ops-text">{event.text}</p>
        </article>
      </div>
    )
  }

  if ((event.kind === 'approval_required' || event.kind === 'approval_decision') && event.status === 'rejected') {
    return (
      <div className="my-1 rounded-md border border-ops-danger/40 bg-ops-danger/10 p-3">
        <div className="mb-1 text-[10px] font-bold uppercase text-ops-red">审批已拒绝</div>
        <p className="m-0 whitespace-pre-wrap font-mono text-xs text-ops-text/90">{event.command || event.text}</p>
      </div>
    )
  }

  if (event.kind === 'final') {
    return (
      <div className="mt-2 text-ops-text/90">
        <div className={PROSE_CLASS}>
          <ReactMarkdown remarkPlugins={[remarkGfm]}>{stripJsonBlocks(event.text)}</ReactMarkdown>
        </div>
      </div>
    )
  }

  // 兜底（不应该走到这里 —— delta/plan/approval/command_* 都已经被分组处理）
  return null
}

export function ConversationView({ events, pendingApprovalRuntimeId, onApprove, onReject }: ConversationViewProps) {
  const scrollContainerRef = useRef<HTMLDivElement | null>(null)
  const shouldAutoScrollRef = useRef(true)

  const planEvents = events.filter((e): e is PlanEvent => e.kind === 'plan')
  const latestPlanEvent = planEvents[planEvents.length - 1]
  const isPlanMode = latestPlanEvent?.mode === 'plan'
  const showPlanCard = !!latestPlanEvent && isPlanMode

  // 是否正在流式（最后一个事件是 delta，说明 LLM 还在产出 token）
  const lastEvent = events[events.length - 1]
  const isStreamingNow = lastEvent?.kind === 'delta'

  const groups: Group[] = []
  const commandGroupMap = new Map<string, { index: number }>()
  const approvalGroupMap = new Map<string, { index: number }>()
  let currentDeltaGroup: DeltaEvent[] = []
  let deltaGroupCounter = 0

  const reindexGroupMaps = () => {
    commandGroupMap.clear()
    approvalGroupMap.clear()
    groups.forEach((entry, index) => {
      if (entry.type !== 'command') {
        return
      }
      if (entry.startEvent?.commandId) {
        commandGroupMap.set(entry.startEvent.commandId, { index })
      }
      const approvalKey = entry.approvalEvent?.stepId || (entry.approvalEvent ? `${entry.approvalEvent.runtimeId || 'runtime'}:${entry.approvalEvent.command}` : null)
      if (approvalKey) {
        approvalGroupMap.set(approvalKey, { index })
      }
    })
  }

  const flushDeltaGroup = () => {
    if (currentDeltaGroup.length === 0) return
    groups.push({ type: 'thinking', deltas: currentDeltaGroup, key: `chain-${deltaGroupCounter++}` })
    currentDeltaGroup = []
  }

  for (const event of events) {
    if (event.kind === 'plan') {
      // 计划事件已经被 PlanSummaryCard pinned 在顶部统一渲染（且 Agent 模式不展示）
      continue
    }
    if (event.kind === 'terminal_status') {
      continue
    }

    if (event.kind === 'delta') {
      currentDeltaGroup.push(event)
      continue
    }

    flushDeltaGroup()

    if (event.kind === 'approval_required' || event.kind === 'approval_decision') {
      const key = event.stepId || `${event.runtimeId || 'runtime'}:${event.command}`
      const existing = approvalGroupMap.get(key)
      if (existing) {
        const target = groups[existing.index]
        if (target.type === 'command') {
          target.approvalEvent = {
            ...(target.approvalEvent ?? event),
            ...event,
            command: event.command || target.approvalEvent?.command || target.startEvent?.command || '',
          }
        }
      } else {
        const commandGroup = { type: 'command' as const, key: `approval-${key}`, approvalEvent: event, chunkEvents: [] as CommandChunk[] }
        const insertIndex = groups.length
        groups.push(commandGroup)
        approvalGroupMap.set(key, { index: insertIndex })
      }
      continue
    }

    if (event.kind === 'command_start') {
      const approvalKey = event.stepId || `${event.runtimeId || 'runtime'}:${event.command}`
      const existingApproval = approvalGroupMap.get(approvalKey)
      if (existingApproval) {
        const target = groups[existingApproval.index]
        if (target.type === 'command') {
          target.startEvent = event
          commandGroupMap.set(event.commandId, { index: existingApproval.index })
        }
      } else {
        const group = { type: 'command' as const, key: `cmd-${event.commandId}`, startEvent: event, chunkEvents: [] as CommandChunk[], endEvent: undefined as CommandEnd | undefined }
        const insertIndex = groups.length
        groups.push(group)
        commandGroupMap.set(event.commandId, { index: insertIndex })
      }
      continue
    }
    if (event.kind === 'command_chunk') {
      const ref = commandGroupMap.get(event.commandId)
      if (ref) {
        const target = groups[ref.index]
        if (target.type === 'command') target.chunkEvents.push(event)
      }
      continue
    }
    if (event.kind === 'command_end') {
      const ref = commandGroupMap.get(event.commandId)
      if (ref) {
        const target = groups[ref.index]
        if (target.type === 'command') target.endEvent = event
      }
      continue
    }

    groups.push({ type: 'event', event })
  }

  flushDeltaGroup()

  // 按对话轮次分组
  type TurnData = { id: string; userEvent?: EventItem; assistantGroups: Group[] }
  const turns: TurnData[] = []
  let currentTurn: TurnData = { id: 'turn-0', assistantGroups: [] }
  let turnCounter = 0

  groups.forEach((entry) => {
    if (entry.type === 'event' && entry.event.kind === 'user') {
      if (currentTurn.userEvent || currentTurn.assistantGroups.length > 0) {
        turns.push(currentTurn)
        turnCounter++
      }
      currentTurn = { id: `turn-${turnCounter}`, userEvent: entry.event, assistantGroups: [] }
    } else {
      currentTurn.assistantGroups.push(entry)
    }
  })
  if (currentTurn.userEvent || currentTurn.assistantGroups.length > 0) {
    turns.push(currentTurn)
  }

  useEffect(() => {
    const el = scrollContainerRef.current
    if (!el) {
      return
    }
    const handleScroll = () => {
      const threshold = 24
      const distanceToBottom = el.scrollHeight - el.scrollTop - el.clientHeight
      shouldAutoScrollRef.current = distanceToBottom <= threshold
    }
    handleScroll()
    el.addEventListener('scroll', handleScroll)
    return () => {
      el.removeEventListener('scroll', handleScroll)
    }
  }, [])

  useEffect(() => {
    const el = scrollContainerRef.current
    if (!el || !shouldAutoScrollRef.current) {
      return
    }
    el.scrollTop = el.scrollHeight
  }, [events])

  if (events.length === 0) {
    return (
      <div className="flex-1 overflow-y-auto p-4" aria-label="助手会话">
        <EmptyState
          title="准备开始"
          description="输入任务后，执行记录、审批请求和结果会显示在这里。"
        />
      </div>
    )
  }

  // chain 是否流式：结合 isStreamingNow 判断

  return (
    <div className="flex flex-1 flex-col overflow-hidden" aria-label="助手会话">
      <div ref={scrollContainerRef} className="flex flex-1 flex-col gap-5 overflow-y-auto px-4 py-4">
        {turns.map((turn, turnIndex) => {
          const isLastTurn = turnIndex === turns.length - 1
          const orderedAssistantGroups = sortAssistantGroups(turn.assistantGroups)

          return (
            <div key={turn.id} className="flex flex-col gap-4">
              {turn.userEvent ? (
                <EventCard
                  event={turn.userEvent}
                  pendingApprovalRuntimeId={pendingApprovalRuntimeId}
                  onApprove={onApprove}
                  onReject={onReject}
                />
              ) : null}

              {orderedAssistantGroups.length > 0 ? (
                <div className="flex justify-start">
                  <article className="flex w-full max-w-[95%] flex-col gap-2 rounded-lg border border-ops-border/20 bg-[#0a0f12] p-4 shadow-sm">
                    <div className="mb-1 flex items-center gap-2">
                      <div className={`h-2 w-2 rounded-full ${isLastTurn && isStreamingNow ? 'bg-ops-cyan animate-pulse' : 'bg-ops-cyan/60'}`} />
                      <span className="text-[11px] font-bold uppercase tracking-wider text-ops-cyan/80">Agent</span>
                    </div>
                    {orderedAssistantGroups.map((entry, index) => {
                      const isLastGroupInTurn = index === orderedAssistantGroups.length - 1
                      if (entry.type === 'command') {
                        return (
                          <CommandExecutionCard
                            key={entry.key}
                            approvalEvent={entry.approvalEvent}
                            startEvent={entry.startEvent}
                            chunkEvents={entry.chunkEvents}
                            endEvent={entry.endEvent}
                            pendingApprovalRuntimeId={pendingApprovalRuntimeId}
                            onApprove={onApprove}
                            onReject={onReject}
                          />
                        )
                      }
                      if (entry.type === 'thinking') {
                        return <ThinkingChain key={entry.key} deltas={entry.deltas} isStreaming={isLastTurn && isLastGroupInTurn && isStreamingNow} />
                      }
                      return (
                        <EventCard
                          key={entry.event.id}
                          event={entry.event}
                          pendingApprovalRuntimeId={pendingApprovalRuntimeId}
                          onApprove={onApprove}
                          onReject={onReject}
                        />
                      )
                    })}
                  </article>
                </div>
              ) : null}
            </div>
          )
        })}
      </div>
    </div>
  )
}
