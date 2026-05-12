import type { EventItem, CommandStartEvent, CommandChunkEvent, CommandEndEvent, ApprovalEvent, ExecutionStartedEvent, ExecutionOutputEvent, ExecutionCompletedEvent } from '../../../types/ops'

export type DeltaEvent = Extract<EventItem, { kind: 'delta' }>
export type CommandStart = CommandStartEvent | ExecutionStartedEvent
export type CommandChunk = CommandChunkEvent | ExecutionOutputEvent
export type CommandEnd = CommandEndEvent | ExecutionCompletedEvent
export type Approval = ApprovalEvent

export type Group =
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

export const STAGE_ORDER = ['assistant'] as const
export const STAGE_LABEL: Record<string, string> = {
  assistant: 'AI Output',
}
export const STAGE_ICON_COLOR: Record<string, string> = {
  assistant: 'text-ops-cyan',
}

export const PROSE_CLASS =
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
