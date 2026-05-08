import { useEffect, useRef, useState } from 'react'
import ReactMarkdown from 'react-markdown'
import remarkGfm from 'remark-gfm'
import { EmptyState } from '../layout/EmptyState'
import type { EventItem } from '../../types/ops'

type ConversationViewProps = {
  events: EventItem[]
  pendingApprovalRunId: string | null
  onApprove?: () => void
  onReject?: () => void
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

type OutputBlockProps = {
  text: string
}

function OutputBlock({ text }: OutputBlockProps) {
  const [isExpanded, setIsExpanded] = useState(false)
  const cleanText = stripAnsi(text)
  const lines = cleanText.split('\n')
  const shouldTruncate = lines.length > 8

  return (
    <div className="flex w-full flex-col gap-1 overflow-hidden">
      <div className="flex items-center justify-between rounded-t border-x border-t border-ops-border/10 bg-black/40 px-2 py-1">
        <span className="text-[10px] font-bold uppercase tracking-widest text-ops-muted">命令输出</span>
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
            className="flex h-9 w-9 shrink-0 items-center justify-center rounded-lg bg-ops-green/25 text-ops-green shadow-sm transition-over:bg-ops-green/35 hover:scale-105 active:scale-95"
            aria-label="批准执行"
          >
            <svg className="h-4.5 w-4.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
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
            <svg className="h-4.5 w-4.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2.5} d="M6 18L18 6M6 6l12 12" />
            </svg>
          </button>
        ) : null}
      </div>
    </div>
  )
}

type PlanSummaryCardProps = {
  event: Extract<EventItem, { kind: 'plan' }>
}

function PlanSummaryCard({ event }: PlanSummaryCardProps) {
  return (
    <div className="rounded-md border border-ops-border/40 bg-[#0a0f0c] p-3">
      <div className="mb-2 flex items-center justify-between gap-3">
        <div className="flex items-center gap-2">
          <div className="h-3 w-1.5 rounded-full bg-ops-green" />
          <h3 className="text-sm font-bold tracking-wide text-ops-text">{event.title?.trim() || '任务计划'}</h3>
        </div>
        <div className="flex items-center gap-2 text-[10px] uppercase tracking-wider text-ops-muted">
          {event.loading ? <span className="animate-pulse text-ops-cyan">● 规划中...</span> : null}
          {typeof event.version === 'number' ? <span className="rounded bg-ops-border/20 px-1.5 py-0.5">v{event.version}</span> : null}
        </div>
      </div>
      <div className="flex flex-wrap gap-1.5">
        {event.steps.map((step, index) => (
          <div
            key={step.id ?? `step-${index}`}
            className={`inline-flex cursor-help items-center gap-1.5 rounded px-2 py-1 text-[11px] ${
              step.status === 'completed'
                ? 'border border-ops-green/20 bg-ops-green/10 text-ops-green'
                : step.status === 'running'
                  ? 'animate-pulse border border-ops-cyan/20 bg-ops-cyan/10 text-ops-cyan'
                  : 'border border-ops-border/10 bg-black/20 text-ops-muted'
            }`}
            title={step.title}
          >
            <span className="font-bold">{index + 1}</span>
            <span className="max-w-[120px] truncate">{step.title}</span>
            {step.status === 'completed' ? <span>✓</span> : null}
          </div>
        ))}
      </div>
    </div>
  )
}

type EventCardProps = {
  event: EventItem
  isLastEvent: boolean
  pendingApprovalRunId: string | null
  onApprove?: () => void
  onReject?: () => void
}

function EventCard({ event, isLastEvent, pendingApprovalRunId, onApprove, onReject }: EventCardProps) {
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
      <article className="ml-8 rounded-md border border-ops-green/35 bg-ops-green/8 p-3">
        <div className="mb-1 text-[9px] font-bold uppercase tracking-wider text-ops-cyan">用户</div>
        <p className="m-0 text-sm text-ops-text">{event.text}</p>
      </article>
    )
  }

  if (event.kind === 'approval') {
    const showActions = pendingApprovalRunId !== null && event.runId === pendingApprovalRunId
    return <CommandCard command={event.command} showActions={showActions} onApprove={onApprove} onReject={onReject} />
  }

  if (event.kind === 'plan') {
    return <PlanSummaryCard event={event} />
  }

  if (event.kind === 'delta') {
    return (
      <article className="group rounded-lg border border-ops-border/40 bg-gradient-to-br from-ops-panel/95 to-ops-panel/80 p-5 shadow-sm transition-all hover:border-ops-border/60 hover:shadow-md">
        <div className="mb-3 flex items-center gap-2">
          <div className="h-1.5 w-1.5 rounded-full bg-ops-cyan animate-pulse" />
          <div className="text-[10px] font-bold uppercase tracking-wider text-ops-cyan/90">
            {getStageLabel(event.stage)}
          </div>
        </div>
        <div className="prose prose-invert prose-base max-w-none text-[15px] leading-relaxed text-ops-text/95 [&>*:first-child]:mt-0 [&>*:last-child]:mb-0 [&>h1]:text-xl [&>h1]:font-bold [&>h1]:text-ops-text [&>h1]:mb-3 [&>h1]:mt-4 [&>h2]:text-lg [&>h2]:font-bold [&>h2]:text-ops-text [&>h2]:mb-2.5 [&>h2]:mt-3.5 [&>h3]:text-base [&>h3]:font-semibold [&>h3]:text-ops-text/95 [&>h3]:mb-2 [&>h3]:mt-3 [&>p]:my-2.5 [&>p]:leading-7 [&>ul]:my-2.5 [&>ul]:space-y-1.5 [&>ol]:my-2.5 [&>ol]:space-y-1.5 [&>li]:leading-6 [&>li]:text-ops-text/90 [&>code]:bg-black/40 [&>code]:px-1.5 [&>code]:py-0.5 [&>code]:rounded [&>code]:text-ops-cyan [&>code]:text-sm [&>code]:font-mono [&>pre]:bg-black/60 [&>pre]:p-4 [&>pre]:rounded-lg [&>pre]:border [&>pre]:border-ops-border/20 [&>pre]:my-3 [&>pre>code]:bg-transparent [&>pre>code]:p-0 [&>pre>code]:text-ops-text/90 [&>blockquote]:border-l-4 [&>blockquote]:border-ops-cyan/40 [&>blockquote]:pl-4 [&>blockquote]:italic [&>blockquote]:text-ops-text/80 [&>strong]:font-bold [&>strong]:text-ops-text [&>em]:italic [&>a]:text-ops-cyan [&>a]:underline [&>a]:hover:text-ops-cyan/80">
          <ReactMarkdown remarkPlugins={[remarkGfm]}>{stripJsonBlocks(event.text)}</ReactMarkdown>
          {isLastEvent ? <span className="ml-1 inline-block h-4 w-1.5 animate-pulse align-[-2px] bg-ops-cyan/90 rounded-sm" /> : null}
        </div>
      </article>
    )
  }

  return (
    <article className="group rounded-lg border border-ops-border/40 bg-gradient-to-br from-ops-panel/95 to-ops-panel/80 p-5 shadow-sm transition-all hover:border-ops-border/60 hover:shadow-md">
      <div className="mb-3 flex items-center gap-2">
        <div className="h-1.5 w-1.5 rounded-full bg-ops-green/80" />
        <div className="text-[10px] font-bold uppercase tracking-wider text-ops-green/90">
          {event.kind === 'final' ? '✓ 结论' : '助手回复'}
        </div>
      </div>
      <div className="prose prose-invert prose-base max-w-none text-[15px] leading-relaxed text-ops-text/95 [&>*:first-child]:mt-0 [&>*:last-child]:mb-0 [&>h1]:text-xl [&>h1]:font-bold [&>h1]:text-ops-text [&>h1]:mb-3 [&>h1]:mt-4 [&>h2]:text-lg [&>h2]:font-bold [&>h2]:text-ops-text [&>h2]:mb-2.5 [&>h2]:mt-3.5 [&>h3]:text-base [&>h3]:font-semibold [&>h3]:text-ops-text/95 [&>h3]:mb-2 [&>h3]:mt-3 [&>p]:my-2.5 [&>p]:leading-7 [&>ul]:my-2.5 [&>ul]:space-y-1.5 [&>ol]:my-2.5 [&>ol]:space-y-1.5 [&>li]:leading-6 [&>li]:text-ops-text/90 [&>code]:bg-black/40 [&>code]:px-1.5 [&>code]:py-0.5 [&>code]:rounded [&>code]:text-ops-cyan [&>code]:text-sm [&>code]:font-mono [&>pre]:bg-black/60 [&>pre]:p-4 [&>pre]:rounded-lg [&>pre]:border [&>pre]:border-ops-border/:bg-transparent [&>pre>code]:p-0 [&>pre>code]:text-ops-text/90 [&>blockquote]:border-l-4 [&>blockquote]:border-ops-cyan/40 [&>blockquote]:pl-4 [&>blockquote]:italic [&>blockquote]:text-ops-text/80 [&>strong]:font-bold [&>strong]:text-ops-text [&>em]:italic [&>a]:text-ops-cyan [&>a]:underline [&>a]:hover:text-ops-cyan/80">
        <ReactMarkdown remarkPlugins={[remarkGfm]}>{stripJsonBlocks(event.text)}</ReactMarkdown>
      </div>
    </article>
  )
}

function getStageLabel(stage?: string) {
  if (stage === 'planner') return '规划'
  if (stage === 'executor') return '执行'
  if (stage === 'review') return '复核'
  return '助手'
}

export function ConversationView({ events, pendingApprovalRunId, onApprove, onReject }: ConversationViewProps) {
  const scrollContainerRef = useRef<HTMLDivElement | null>(null)
  const shouldAutoScrollRef = useRef(true)

  // 找到最新的 plan 事件
  const latestPlanEvent = events.filter(e => e.kind === 'plan').pop() as Extract<EventItem, { kind: 'plan' }> | undefined
  
  // 过滤掉所有 plan 事件,只保留其他事件
  const nonPlanEvents = events.filter(e => e.kind !== 'plan')

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

  return (
    <div className="flex flex-1 flex-col overflow-hidden" aria-label="助手会话">
      {/* 固定在顶部的任务计划 */}
      {latestPlanEvent ? (
        <div className="border-b border-ops-border/30 bg-ops-bg/95 px-4 py-3 backdrop-blur-sm">
          <PlanSummaryCard event={latestPlanEvent} />
        </div>
      ) : null}
      
      {/* 滚动区域 */}
      <div ref={scrollContainerRef} className="flex flex-1 flex-col gap-3 overflow-y-auto px-4 py-4">
        {nonPlanEvents.map((event) => (
          <EventCard
            key={event.id}
            event={event}
            isLastEvent={events[events.length - 1].id === event.id}
            pendingApprovalRunId={pendingApprovalRunId}
            onApprove={onApprove}
            onReject={onReject}
          />
        ))}
      </div>
    </div>
  )
}
