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
  assistant: 'AI Output',
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
  'prose prose-invert prose-sm max-w-none text-[14px] leading-relaxed text-ops-text/90 ' +
  '[&>*:first-child]:mt-0 [&>*:last-child]:mb-0 ' +
  '[&_h1]:text-[16px] [&_h1]:font-bold [&_h1]: [&_h1]:tracking-wider [&_h1]:text-ops-cyan [&_h1]:mb-3 [&_h1]:mt-4 ' +
  '[&_h2]:text-[15px] [&_h2]:font-bold [&_h2]:text-ops-text [&_h2]:mb-2 [&_h2]:mt-3 ' +
  '[&_h3]:text-[14px] [&_h3]:font-bold [&_h3]:text-ops-text/90 [&_h3]:mb-1.5 [&_h3]:mt-2.5 ' +
  '[&_p]:my-3 [&_ul]:my-3 [&_ul]:space-y-1.5 [&_ol]:my-3 [&_ol]:space-y-1.5 ' +
  '[&_li]:leading-relaxed [&_li]:text-ops-text/85 ' +
  '[&_code]:bg-ops-deep [&_code]:px-1.5 [&_code]:py-0.5 [&_code]:rounded-md [&_code]:text-ops-cyan [&_code]:text-[12px] [&_code]:font-mono [&_code]:border [&_code]:border-ops-border/20 ' +
  '[&_pre]:bg-ops-deep [&_pre]:p-4 [&_pre]:rounded-xl [&_pre]:border [&_pre]:border-ops-border/30 [&_pre]:my-4 [&_pre]:shadow-inner ' +
  '[&_pre>code]:bg-transparent [&_pre>code]:p-0 [&_pre>code]:text-ops-text/80 [&_pre>code]:border-none ' +
  '[&_blockquote]:border-l-4 [&_blockquote]:border-ops-cyan/40 [&_blockquote]:pl-4 [&_blockquote]:italic [&_blockquote]:text-ops-text/60 [&_blockquote]:bg-ops-cyan/5 [&_blockquote]:py-2 [&_blockquote]:rounded-r-lg ' +
  '[&_strong]:font-bold [&_strong]:text-ops-text [&_em]:italic ' +
  '[&_a]:text-ops-cyan [&_a]:underline hover:[&_a]:text-ops-cyan/80'

type OutputBlockProps = {
  text: string
  label?: string
}

function OutputBlock({ text, label = 'Terminal Output' }: OutputBlockProps) {
  const [isExpanded, setIsExpanded] = useState(false)
  const cleanText = stripAnsi(text)
  const lines = cleanText.split('\n')
  const shouldTruncate = lines.length > 10

  return (
    <div className="flex w-full flex-col gap-0 overflow-hidden rounded-xl border border-ops-border/20 shadow-sm">
      <div className="flex items-center justify-between bg-ops-deep/80 px-4 py-2 border-b border-ops-border/10">
        <span className="text-[10px] font-bold  tracking-[0.2em] text-ops-muted/70">{label}</span>
        {shouldTruncate ? (
          <button
            type="button"
            onClick={() => setIsExpanded(!isExpanded)}
            className="text-[10px] font-bold  tracking-widest text-ops-cyan hover:text-ops-cyan/80 transition-colors"
          >
            {isExpanded ? 'Collapse' : `Expand (${lines.length} Lines)`}
          </button>
        ) : null}
      </div>
      <pre
        className={`m-0 whitespace-pre-wrap bg-ops-deep/40 p-4 font-mono text-[11px] leading-normal text-ops-text/80 transition-all ${!isExpanded && shouldTruncate ? 'relative max-h-[200px] overflow-hidden' : 'max-h-none'
          }`}
      >
        {cleanText}
        {!isExpanded && shouldTruncate ? <div className="pointer-events-none absolute inset-x-0 bottom-0 h-16 bg-gradient-to-t from-ops-deep to-transparent" /> : null}
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
  const title = startEvent?.title?.trim() || (approvalEvent ? 'Security Clearance' : 'Remote Instruction')
  const approvalStatus = approvalEvent?.status ?? (approvalEvent ? 'pending' : undefined)
  const showApprovalActions = approvalStatus === 'pending' && approvalEvent?.runtimeId !== undefined && pendingApprovalRuntimeId !== null && approvalEvent.runtimeId === pendingApprovalRuntimeId

  return (
    <div className="my-3 rounded-2xl border border-ops-border/40 bg-ops-deep/40 p-5 shadow-sm overflow-hidden">
      <div className="mb-4 flex items-center justify-between gap-4">
        <div className="flex items-center gap-3">
          <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-ops-cyan/10 border border-ops-cyan/20 text-ops-cyan shadow-glow">
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="3" strokeLinecap="round" strokeLinejoin="round"><polyline points="4 17 10 11 4 5"></polyline><line x1="12" y1="19" x2="20" y2="19"></line></svg>
          </div>
          <div>
            <div className="text-[10px] font-bold  tracking-[0.25em] text-ops-muted/60">Execution Unit</div>
            <div className="text-[13px] font-bold text-ops-text tracking-tight">{title}</div>
          </div>
        </div>

        {endEvent ? (
          <div className={`rounded-lg border px-2.5 py-1 text-[9px] font-bold  tracking-[0.15em] ${exitCode === null || exitCode === 0 ? 'text-ops-emerald border-ops-emerald/30 bg-ops-emerald/10 shadow-glow' : 'text-ops-danger border-ops-danger/30 bg-ops-danger/10'}`}>
            {exitCode === null || exitCode === 0 ? 'Success' : `Failed (${exitCode})`}
          </div>
        ) : approvalStatus ? (
          <div className={`flex items-center gap-2 rounded-lg border px-3 py-1.5 text-[10px] font-bold  tracking-[0.15em] ${approvalStatus === 'approved' ? 'border-ops-emerald/30 bg-ops-emerald/10 text-ops-emerald shadow-glow' : approvalStatus === 'rejected' ? 'border-ops-danger/30 bg-ops-danger/10 text-ops-danger shadow-glow' : 'border-ops-warning/30 bg-ops-warning/10 text-ops-warning shadow-glow'}`}>
            <span className={`h-1.5 w-1.5 rounded-full ${approvalStatus === 'approved' ? 'bg-ops-emerald shadow-glow' : approvalStatus === 'rejected' ? 'bg-ops-danger shadow-glow' : 'bg-ops-warning shadow-glow animate-pulse'}`} />
            {approvalStatus === 'approved' ? 'Authorized' : approvalStatus === 'rejected' ? 'Access Denied' : 'Pending Approval'}
          </div>
        ) : (
          <div className="rounded-lg border border-ops-cyan/30 bg-ops-cyan/10 px-2.5 py-1 text-[9px] font-bold  tracking-[0.15em] text-ops-cyan shadow-glow animate-pulse">
            Executing
          </div>
        )}
      </div>
      {command ? (
        <div className="mb-4 relative">
          <code className="block rounded-xl border border-ops-border/20 bg-ops-deep px-4 py-3 text-[12px] text-ops-text/90 font-mono shadow-inner border-l-4 border-l-ops-cyan/60">
            {command}
          </code>
        </div>
      ) : null}
      {approvalEvent && approvalStatus === 'pending' ? (
        <div className="mb-4 rounded-xl border border-ops-warning/30 bg-ops-warning/5 p-4">
          <div className="mb-2 flex items-center justify-between gap-2">
            <span className="text-[10px] font-bold  tracking-widest text-ops-warning shadow-glow">
              Requires Authorization
            </span>
          </div>
          {approvalEvent.reason ? <div className="mb-4 text-[12px] leading-relaxed text-ops-text/80 italic border-l-2 border-ops-warning/30 pl-3">{approvalEvent.reason}</div> : null}

          {showApprovalActions ? (
            <div className="flex items-center justify-end gap-3">
              <button type="button" onClick={onReject} className="button button-danger h-9 px-6 text-[10px]">
                Reject
              </button>
              <button type="button" onClick={onApprove} className="button button-primary h-9 px-6 text-[10px] shadow-glow">
                Authorize
              </button>
            </div>
          ) : null}
        </div>
      ) : null}
      {outputText ? <OutputBlock text={outputText} label="Realtime Trace" /> : null}
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
          <h3 className="text-[13.5px] font-bold tracking-wide text-ops-text">{event.title?.trim() || 'Task Plan'}</h3>
          {isPlanMode && event.lockedPlan ? (
            <span className="inline-flex items-center gap-1 rounded-md border border-ops-cyan/35 bg-ops-cyan/10 px-1.5 py-0.5 text-[10px] font-medium text-ops-cyan">
              <svg width="10" height="10" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.4" strokeLinecap="round" strokeLinejoin="round"><rect x="3" y="11" width="18" height="11" rx="2"></rect><path d="M7 11V7a5 5 0 0110 0v4"></path></svg>
              Locked
            </span>
          ) : null}
        </div>
        <div className="flex items-center gap-2 text-[10px]  tracking-wider text-ops-muted">
          {event.loading ? <span className="animate-pulse text-ops-cyan">● Planning</span> : null}
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
              className={`flex items-start gap-2.5 rounded-md border px-2.5 py-1.5 text-[12px] transition-colors ${step.status === 'completed'
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
              {isRunning ? <span className="shrink-0 text-[10px]  tracking-wider text-ops-cyan/80 animate-pulse">Executing</span> : null}
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
        <div className="mb-1 text-[10px] font-bold  text-ops-red">System Error</div>
        <p className="m-0 font-mono text-xs text-ops-text/90">{event.text}</p>
      </div>
    )
  }

  if (event.kind === 'user') {
    return (
      <div className="flex justify-end my-2">
        <article className="max-w-[80%] rounded-2xl border border-ops-cyan/30 bg-ops-cyan/10 px-5 py-4 shadow-sm backdrop-blur-md relative overflow-hidden group">
          <div className="absolute top-0 left-0 w-1 h-full bg-ops-cyan shadow-glow" />
          <div className="mb-2 flex items-center justify-between border-b border-ops-cyan/10 pb-2">
            <span className="text-[10px] font-bold  tracking-[0.2em] text-ops-cyan shadow-glow">Operator Command</span>
            <span className="text-[9px] font-bold text-ops-muted/50  tracking-widest">Authorized</span>
          </div>
          <p className="m-0 whitespace-pre-wrap text-[14px] leading-relaxed text-ops-text font-medium">{event.text}</p>
        </article>
      </div>
    )
  }

  if ((event.kind === 'approval_required' || event.kind === 'approval_decision') && event.status === 'rejected') {
    return (
      <div className="my-2 rounded-2xl border border-ops-danger/40 bg-ops-danger/10 p-5 shadow-sm">
        <div className="mb-2 flex items-center gap-2 text-ops-danger">
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="3"><circle cx="12" cy="12" r="10" /><line x1="15" y1="9" x2="9" y2="15" /><line x1="9" y1="9" x2="15" y2="15" /></svg>
          <span className="text-[10px] font-bold  tracking-[0.2em]">Access Denied</span>
        </div>
        <p className="m-0 whitespace-pre-wrap font-mono text-[12px] leading-relaxed text-ops-text/80 border-l-2 border-ops-danger/30 pl-4">{event.command || event.text}</p>
      </div>
    )
  }

  if (event.kind === 'final') {
    return (
      <div className="mt-4 pt-4 border-t border-ops-border/10">
        <div className={PROSE_CLASS}>
          <ReactMarkdown remarkPlugins={[remarkGfm]}>{stripJsonBlocks(event.text)}</ReactMarkdown>
        </div>
      </div>
    )
  }

  return null
}

export function ConversationView({ events, pendingApprovalRuntimeId, onApprove, onReject }: ConversationViewProps) {
  const scrollContainerRef = useRef<HTMLDivElement | null>(null)
  const shouldAutoScrollRef = useRef(true)

  const planEvents = events.filter((e): e is PlanEvent => e.kind === 'plan')
  const latestPlanEvent = planEvents[planEvents.length - 1]
  const isPlanMode = latestPlanEvent?.mode === 'plan'

  const lastEvent = events[events.length - 1]
  const isStreamingNow = lastEvent?.kind === 'delta'

  const groups: Group[] = []
  const commandGroupMap = new Map<string, { index: number }>()
  const approvalGroupMap = new Map<string, { index: number }>()
  let currentDeltaGroup: DeltaEvent[] = []
  let deltaGroupCounter = 0

  const flushDeltaGroup = () => {
    if (currentDeltaGroup.length === 0) return
    groups.push({ type: 'thinking', deltas: currentDeltaGroup, key: `chain-${deltaGroupCounter++}` })
    currentDeltaGroup = []
  }

  for (const event of events) {
    if (event.kind === 'plan') continue
    if (event.kind === 'terminal_status') continue

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
    if (!el) return
    const handleScroll = () => {
      const threshold = 24
      const distanceToBottom = el.scrollHeight - el.scrollTop - el.clientHeight
      shouldAutoScrollRef.current = distanceToBottom <= threshold
    }
    handleScroll()
    el.addEventListener('scroll', handleScroll)
    return () => el.removeEventListener('scroll', handleScroll)
  }, [])

  useEffect(() => {
    const el = scrollContainerRef.current
    if (!el || !shouldAutoScrollRef.current) return
    el.scrollTop = el.scrollHeight
  }, [events])

  if (events.length === 0) {
    return (
      <div className="flex-1 overflow-y-auto p-4" aria-label="Assistant Conversation">
        <EmptyState title="Ready to Start" description="Enter a task and execution logs, approval requests, and results will appear here." />
      </div>
    )
  }

  return (
    <div className="flex flex-1 flex-col overflow-hidden" aria-label="Assistant Conversation">
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
                  <article className="flex w-full max-w-[95%] flex-col gap-4 rounded-3xl border border-ops-border/40 bg-ops-panel/60 px-6 py-5 shadow-2xl backdrop-blur-xl relative overflow-hidden group">
                    <div className="absolute top-0 right-0 p-4 opacity-10 pointer-events-none group-hover:opacity-20 transition-opacity">
                      <svg width="48" height="48" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1" strokeLinecap="round" strokeLinejoin="round" className="text-ops-cyan"><path d="M12 2v20M17 5H9.5a3.5 3.5 0 0 0 0 7h5a3.5 3.5 0 0 1 0 7H6"></path></svg>
                    </div>
                    <div className="flex items-center gap-3 border-b border-ops-border/20 bg-ops-deep/40 px-4 py-3">
                      <div className="flex items-center gap-2">
                        <div className="h-5 w-5 rounded border border-ops-cyan/30 bg-ops-cyan/10 flex items-center justify-center text-ops-cyan">
                          <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="3"><path d="M12 2v4m0 12v4M4.93 4.93l2.83 2.83m8.48 8.48l2.83 2.83M2 12h4m12 0h4M4.93 19.07l2.83-2.83m8.48-8.48l2.83-2.83" /></svg>
                        </div>
                        <span className="text-[10px] font-bold  tracking-[0.15em] text-ops-cyan">Neural Thinking Process</span>
                      </div>
                      {isLastTurn && isStreamingNow && <span className="ml-2 h-1.5 w-1.5 rounded-full bg-ops-cyan animate-ping" />}
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
