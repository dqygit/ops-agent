import type { EventItem, CommandStartEvent, CommandChunkEvent, CommandEndEvent, ApprovalEvent, ExecutionStartedEvent, ExecutionOutputEvent, ExecutionCompletedEvent, AgentMessage } from '../../../types/ops'

export type DeltaEvent = Extract<EventItem, { kind: 'delta' }>
export type CommandStart = CommandStartEvent | ExecutionStartedEvent
export type CommandChunk = CommandChunkEvent | ExecutionOutputEvent
export type CommandEnd = CommandEndEvent | ExecutionCompletedEvent
export type Approval = ApprovalEvent

export type Group =
  | { type: 'event'; event: EventItem }
  | { type: 'thinking'; deltas?: DeltaEvent[]; message?: AgentMessage; key: string }
  | {
    type: 'command'
    key: string
    message?: AgentMessage
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
  // H1: 最高层级 - 大标题,带底部边框和图标效果
  '[&_h1]:text-[20px] [&_h1]:font-extrabold [&_h1]:tracking-wide [&_h1]:text-ops-cyan [&_h1]:mb-4 [&_h1]:mt-6 [&_h1]:pb-2 [&_h1]:border-b-2 [&_h1]:border-ops-cyan/30 ' +
  // H2: 次级标题 - 带左侧装饰条
  '[&_h2]:text-[17px] [&_h2]:font-bold [&_h2]:text-ops-text [&_h2]:mb-3 [&_h2]:mt-5 [&_h2]:pl-3 [&_h2]:border-l-4 [&_h2]:border-ops-cyan/60 ' +
  // H3: 三级标题 - 带背景高亮
  '[&_h3]:text-[15px] [&_h3]:font-semibold [&_h3]:text-ops-text/95 [&_h3]:mb-2 [&_h3]:mt-4 [&_h3]:px-2 [&_h3]:py-1 [&_h3]:bg-ops-cyan/10 [&_h3]:rounded [&_h3]:inline-block ' +
  // H4-H6: 更小的标题层级
  '[&_h4]:text-[14px] [&_h4]:font-semibold [&_h4]:text-ops-text/90 [&_h4]:mb-1.5 [&_h4]:mt-3 ' +
  '[&_h5]:text-[13px] [&_h5]:font-medium [&_h5]:text-ops-text/85 [&_h5]:mb-1 [&_h5]:mt-2.5 ' +
  '[&_h6]:text-[12px] [&_h6]:font-medium [&_h6]:text-ops-text/80 [&_h6]:mb-1 [&_h6]:mt-2 [&_h6]:uppercase [&_h6]:tracking-wider ' +
  // 段落样式 - 首行缩进(中文排版习惯)
  '[&_p]:my-3 [&_p]:text-indent-[2em] ' +
  '[&_p:first-of-type]:text-indent-0 ' +
  '[&_li_p]:text-indent-0 ' +
  '[&_blockquote_p]:text-indent-0 ' +
  // 列表样式 - 增强缩进和层级
  '[&_ul]:my-3 [&_ul]:space-y-2 [&_ul]:list-disc [&_ul]:pl-8 [&_ul]:ml-2 ' +
  '[&_ol]:my-3 [&_ol]:space-y-2 [&_ol]:list-decimal [&_ol]:pl-8 [&_ol]:ml-2 ' +
  // 嵌套列表 - 更明显的缩进
  '[&_ul_ul]:mt-1.5 [&_ul_ul]:mb-0 [&_ul_ul]:pl-6 [&_ul_ul]:list-circle ' +
  '[&_ol_ol]:mt-1.5 [&_ol_ol]:mb-0 [&_ol_ol]:pl-6 [&_ol_ol]:list-[lower-alpha] ' +
  '[&_ul_ol]:mt-1.5 [&_ul_ol]:mb-0 [&_ul_ol]:pl-6 ' +
  '[&_ol_ul]:mt-1.5 [&_ol_ul]:mb-0 [&_ol_ul]:pl-6 ' +
  // 列表项样式
  '[&_li]:leading-relaxed [&_li]:text-ops-text/90 [&_li]:pl-2 ' +
  '[&_li::marker]:text-ops-cyan/70 [&_li::marker]:font-bold ' +
  '[&_code]:bg-ops-deep [&_code]:px-1.5 [&_code]:py-0.5 [&_code]:rounded-md [&_code]:text-ops-cyan [&_code]:text-[12px] [&_code]:font-mono [&_code]:border [&_code]:border-ops-border/20 ' +
  '[&_pre]:bg-ops-deep [&_pre]:p-4 [&_pre]:rounded-xl [&_pre]:border [&_pre]:border-ops-border/30 [&_pre]:my-4 [&_pre]:shadow-inner ' +
  '[&_pre>code]:bg-transparent [&_pre>code]:p-0 [&_pre>code]:text-ops-text/80 [&_pre>code]:border-none ' +
  '[&_blockquote]:border-l-4 [&_blockquote]:border-ops-cyan/40 [&_blockquote]:pl-4 [&_blockquote]:italic [&_blockquote]:text-ops-text/60 [&_blockquote]:bg-ops-cyan/5 [&_blockquote]:py-2 [&_blockquote]:rounded-r-lg ' +
  // 表格样式 - 专业的数据展示
  '[&_table]:w-full [&_table]:my-4 [&_table]:border-collapse [&_table]:rounded-lg [&_table]:overflow-hidden [&_table]:border [&_table]:border-ops-border/30 ' +
  '[&_thead]:bg-ops-cyan/10 ' +
  '[&_th]:px-4 [&_th]:py-3 [&_th]:text-left [&_th]:text-[13px] [&_th]:font-bold [&_th]:text-ops-cyan [&_th]:border-b-2 [&_th]:border-ops-cyan/30 [&_th]:uppercase [&_th]:tracking-wide ' +
  '[&_td]:px-4 [&_td]:py-2.5 [&_td]:text-[13px] [&_td]:text-ops-text/90 [&_td]:border-b [&_td]:border-ops-border/20 ' +
  '[&_tbody_tr]:transition-colors [&_tbody_tr:hover]:bg-ops-cyan/5 ' +
  '[&_tbody_tr:last-child_td]:border-b-0 ' +
  '[&_strong]:font-bold [&_strong]:text-ops-text/100 [&_em]:italic ' +
  '[&_a]:text-ops-cyan [&_a]:underline hover:[&_a]:text-ops-cyan/80'
