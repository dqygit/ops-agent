import ReactMarkdown from 'react-markdown'
import remarkGfm from 'remark-gfm'
import type { EventItem } from '../../../types/ops'
import { PROSE_CLASS } from './types'
import { stripJsonBlocks } from './utils'
import { AssistantMessageContent } from './AssistantMessageContent'

type EventCardProps = {
  event: EventItem
  pendingApprovalRuntimeId: string | null
  onApprove?: () => void
  onReject?: () => void
}

export function EventCard({ event }: EventCardProps) {
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
            <span className="text-[10px] font-bold tracking-[0.2em] text-ops-cyan shadow-glow uppercase">Operator Command</span>
            <span className="text-[9px] font-bold text-ops-cyan/40 tracking-widest uppercase">Authorized</span>
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
          <span className="text-[10px] font-bold tracking-[0.2em] uppercase">Access Denied</span>
        </div>
        <p className="m-0 whitespace-pre-wrap font-mono text-[12px] leading-relaxed text-ops-text/80 border-l-2 border-ops-danger/30 pl-4">{event.command || event.text}</p>
      </div>
    )
  }

  if (event.kind === 'final') {
    return (
      <div className="mt-2">
        <AssistantMessageContent content={event.text} />
      </div>
    )
  }

  return null
}
