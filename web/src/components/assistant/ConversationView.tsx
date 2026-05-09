import { useEffect, useMemo, useRef, useState } from 'react'
import ReactMarkdown from 'react-markdown'
import remarkGfm from 'remark-gfm'
import { EmptyState } from '../layout/EmptyState'
import type { EventItem, PlanEvent } from '../../types/ops'

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

type Group =
  | { type: 'event'; event: EventItem }
  | { type: 'thinking'; deltas: DeltaEvent[]; key: string }
  | {
      type: 'command'
      key: string
      startEvent: CommandStart
      chunkEvents: CommandChunk[]
      endEvent?: CommandEnd
    }

const STAGE_ORDER: Array<'planner' | 'executor' | 'review'> = ['planner', 'executor', 'review']
const STAGE_LABEL: Record<string, string> = {
  planner: '规划',
  executor: '精炼',
  review: '复核',
}
const STAGE_ICON_COLOR: Record<string, string> = {
  planner: 'text-violet-400',
  executor: 'text-ops-cyan',
  review: 'text-emerald-400',
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
  result = result.replace(/```\s*[\s\S]*?```/g, '')
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
  startEvent: CommandStart
  chunkEvents: CommandChunk[]
  endEvent?: CommandEnd
}

function CommandExecutionCard({ startEvent, chunkEvents, endEvent }: CommandExecutionCardProps) {
  const outputText = chunkEvents.map((event) => event.text).join('')
  const exitCode = endEvent?.exitCode
  const statusLabel = endEvent
    ? exitCode === null || exitCode === 0
      ? '已完成'
      : `失败（退出码 ${exitCode}）`
    : '执行中'

  return (
    <article className="rounded-lg border border-ops-border/40 bg-gradient-to-br from-[#0a1014] to-[#0e161c] p-4 shadow-sm">
      <div className="mb-3 flex items-center justify-between gap-3">
        <div>
          <div className="text-[10px] font-bold uppercase tracking-wider text-ops-cyan/90">命令执行</div>
          <div className="mt-1 text-sm font-semibold text-ops-text">{startEvent.title?.trim() || '终端命令'}</div>
        </div>
        <div className={`rounded px-2 py-1 text-[10px] font-bold ${endEvent ? (exitCode === null || exitCode === 0 ? 'bg-ops-green/15 text-ops-green' : 'bg-ops-danger/15 text-ops-red') : 'bg-ops-cyan/15 text-ops-cyan animate-pulse'}`}>
          {statusLabel}
        </div>
      </div>
      <code className="mb-3 block rounded-md border border-ops-border/20 bg-black/40 px-3 py-2 text-xs text-ops-text/90">
        {startEvent.command}
      </code>
      {outputText ? <OutputBlock text={outputText} label="流式输出" /> : null}
    </article>
  )
}

type CommandCardProps = {
  command: string
  showActions: boolean
  onApprove?: () => void
  onReject?: () => void
}

function CommandCard({ command, showActions, onApprove, onReject }: CommandCardProps) {
  return (
    <div className="group rounded-lg border border-amber-500/50 bg-gradient-to-br from-amber-500/15 to-amber-600/10 p-4 shadow-lg transition-all hover:shadow-xl">
      <div className="mb-2 flex items-center gap-2">
        <div className="flex h-5 w-5 items-center justify-center rounded bg-amber-500/30">
          <svg className="h-3 w-3 text-amber-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
          </svg>
        </div>
        <span className="text-[10px] font-bold uppercase tracking-wider text-amber-400/90">待审批命令</span>
      </div>
      <div className="flex items-center gap-3">
        {showActions ? (
          <button
            type="button"
            onClick={onApprove}
            className="flex h-9 w-9 shrink-0 items-center justify-center rounded-lg bg-ops-green/25 text-ops-green shadow-sm transition-all hover:bg-ops-green/35 hover:scale-105 active:scale-95"
            aria-label="批准执行"
          >
            <svg className="h-4 w-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2.5} d="M5 13l4 4L19 7" />
            </svg>
          </button>
        ) : null}
        <code className="flex-1 rounded-md border border-amber-500/30 bg-black/40 px-3.5 py-2.5 text-xs font-mono leading-relaxed text-ops-text shadow-inner" title={command}>
          {command}
        </code>
        {showActions ? (
          <button
            type="button"
            onClick={onReject}
            className="flex h-9 w-9 shrink-0 items-center justify-center rounded-lg bg-ops-red/25 text-ops-red shadow-sm transition-all hover:bg-ops-red/35 hover:scale-105 active:scale-95"
            aria-label="拒绝执行"
          >
            <svg className="h-4 w-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2.5} d="M6 18L18 6M6 6l12 12" />
            </svg>
          </button>
        ) : null}
      </div>
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
      const stage = d.stage || 'planner'
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

  const lastDeltaStage = (deltas[deltas.length - 1]?.stage || visibleStages[0] || 'planner') as string
  const [activeStage, setActiveStage] = useState<string>(lastDeltaStage)
  const [userInteracted, setUserInteracted] = useState(false)
  const [isExpanded, setIsExpanded] = useState<boolean>(isStreaming)

  // 流式过程中跟随最新 stage；用户主动切过则尊重用户
  useEffect(() => {
    if (isStreaming && !userInteracted) {
      setActiveStage(lastDeltaStage)
    }
  }, [isStreaming, lastDeltaStage, userInteracted])

  // 流式时自动展开
  useEffect(() => {
    if (isStreaming) {
      setIsExpanded(true)
    }
  }, [isStreaming])

  // 流式结束后默认收起一次（避免一次任务结束后还堆积一堆展开的卡）
  const wasStreamingRef = useRef(isStreaming)
  useEffect(() => {
    if (wasStreamingRef.current && !isStreaming) {
      setIsExpanded(false)
    }
    wasStreamingRef.current = isStreaming
  }, [isStreaming])

  if (visibleStages.length === 0) return null
  const activeKey = visibleStages.includes(activeStage as (typeof STAGE_ORDER)[number]) ? activeStage : visibleStages[0]
  const activeText = stageContent[activeKey] || ''

  return (
    <article className="rounded-lg border border-ops-border/35 bg-[linear-gradient(180deg,rgba(15,23,42,0.55),rgba(10,15,12,0.85))] shadow-sm">
      <header className="flex items-center justify-between gap-3 border-b border-ops-border/20 px-3 py-2">
        <div className="flex items-center gap-2 min-w-0">
          <div className={`h-1.5 w-1.5 rounded-full ${isStreaming ? 'bg-ops-cyan animate-pulse' : 'bg-ops-border/60'}`} />
          <span className="text-[10px] font-bold uppercase tracking-[0.18em] text-ops-muted">AI 思考链</span>
          <div className="ml-1 flex shrink-0 items-center gap-1">
            {visibleStages.map((stage) => {
              const isActive = stage === activeKey
              return (
                <button
                  key={stage}
                  type="button"
                  onClick={() => {
                    setUserInteracted(true)
                    setActiveStage(stage)
                    setIsExpanded(true)
                  }}
                  className={`inline-flex items-center gap-1 rounded-full px-2 py-0.5 text-[11px] transition-colors ${
                    isActive
                      ? 'bg-ops-cyan/15 text-ops-cyan border border-ops-cyan/35'
                      : 'border border-ops-border/30 bg-black/25 text-ops-muted hover:text-ops-text hover:border-ops-border/55'
                  }`}
                >
                  <span className={STAGE_ICON_COLOR[stage] || ''}>●</span>
                  {STAGE_LABEL[stage] || stage}
                </button>
              )
            })}
          </div>
        </div>
        <button
          type="button"
          onClick={() => setIsExpanded((prev) => !prev)}
          className="shrink-0 rounded p-1 text-ops-muted hover:bg-ops-border/15 hover:text-ops-text"
          aria-label={isExpanded ? '收起思考链' : '展开思考链'}
        >
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round" className={`transition-transform ${isExpanded ? 'rotate-180' : ''}`}>
            <path d="M6 9l6 6 6-6" />
          </svg>
        </button>
      </header>
      {isExpanded ? (
        <div className="px-4 py-3">
          <div className={PROSE_CLASS}>
            <ReactMarkdown remarkPlugins={[remarkGfm]}>{activeText}</ReactMarkdown>
            {isStreaming ? <span className="ml-1 inline-block h-3.5 w-1.5 animate-pulse align-[-2px] rounded-sm bg-ops-cyan/85" /> : null}
          </div>
        </div>
      ) : null}
    </article>
  )
}

type EventCardProps = {
  event: EventItem
  pendingApprovalRuntimeId: string | null
  onApprove?: () => void
  onReject?: () => void
}

function EventCard({ event, pendingApprovalRuntimeId, onApprove, onReject }: EventCardProps) {
  if (event.kind === 'status') {
    return <div className="text-xs italic text-ops-muted">{event.text}</div>
  }

  if (event.kind === 'error') {
    return (
      <article className="rounded-md border border-ops-danger/40 bg-ops-danger/10 p-3">
        <div className="mb-1 text-[10px] font-bold uppercase text-ops-red">系统错误</div>
        <p className="m-0 font-mono text-xs text-ops-text/90">{event.text}</p>
      </article>
    )
  }

  if (event.kind === 'output') {
    return <OutputBlock text={event.text} />
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

  if (event.kind === 'approval') {
    const showActions = pendingApprovalRuntimeId !== null && event.runtimeId === pendingApprovalRuntimeId
    return <CommandCard command={event.command} showActions={showActions} onApprove={onApprove} onReject={onReject} />
  }

  if (event.kind === 'final') {
    return (
      <article className="rounded-lg border border-ops-green/45 bg-gradient-to-br from-ops-green/12 to-emerald-500/8 p-4 shadow-sm">
        <div className="mb-2 flex items-center gap-2">
          <span className="flex h-5 w-5 items-center justify-center rounded-full bg-ops-green/25 text-ops-green">
            <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="3" strokeLinecap="round" strokeLinejoin="round"><path d="M5 13l4 4L19 7" /></svg>
          </span>
          <div className="text-[10px] font-bold uppercase tracking-wider text-ops-green/95">任务结论</div>
        </div>
        <div className={PROSE_CLASS}>
          <ReactMarkdown remarkPlugins={[remarkGfm]}>{stripJsonBlocks(event.text)}</ReactMarkdown>
        </div>
      </article>
    )
  }

  // 兜底（不应该走到这里 —— delta/plan/command_* 都已经被分组处理）
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
  let currentDeltaGroup: DeltaEvent[] = []
  let deltaGroupCounter = 0

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

    if (event.kind === 'command_start') {
      const group = { startEvent: event, chunkEvents: [] as CommandChunk[], endEvent: undefined as CommandEnd | undefined }
      groups.push({ type: 'command', key: `cmd-${event.commandId}`, ...group })
      commandGroupMap.set(event.commandId, { index: groups.length - 1 })
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

  // chain 是否流式：仅最后一个 group 是 thinking 时，结合 isStreamingNow 判断
  const lastGroupIndex = groups.length - 1

  return (
    <div className="flex flex-1 flex-col overflow-hidden" aria-label="助手会话">
      {showPlanCard && latestPlanEvent ? (
        <div className="border-b border-ops-border/30 bg-ops-bg/95 px-4 py-3 backdrop-blur-sm">
          <PlanSummaryCard event={latestPlanEvent} />
        </div>
      ) : null}

      <div ref={scrollContainerRef} className="flex flex-1 flex-col gap-3 overflow-y-auto px-4 py-4">
        {groups.map((entry, index) => {
          if (entry.type === 'command') {
            return (
              <CommandExecutionCard
                key={entry.key}
                startEvent={entry.startEvent}
                chunkEvents={entry.chunkEvents}
                endEvent={entry.endEvent}
              />
            )
          }
          if (entry.type === 'thinking') {
            const isLast = index === lastGroupIndex
            return <ThinkingChain key={entry.key} deltas={entry.deltas} isStreaming={isLast && isStreamingNow} />
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
      </div>
    </div>
  )
}
