import { useState } from 'react'
import { useAppearance } from '../../../hooks/useAppearance'
import type { EventItem } from '../../../types/ops'
import { AssistantMessageContent } from './AssistantMessageContent'

type EventCardProps = {
  event: EventItem
  pendingApprovalRuntimeId: string | null
  onApprove?: (allowPrefix?: string) => void
  onReject?: () => void
  onTerminalRequestDecision?: (input: { runtimeId: string; requestId: string; approvalToken: string; approved: boolean }) => Promise<void>
  settledTerminalRequestIds?: Set<string>
}

function eventValue(event: EventItem, key: string): string | undefined {
  const value = (event as unknown as Record<string, unknown>)[key]
  return typeof value === 'string' ? value : undefined
}

export function EventCard({ event, onTerminalRequestDecision, settledTerminalRequestIds }: EventCardProps) {
  const { t } = useAppearance()
  const [submittingTerminalDecision, setSubmittingTerminalDecision] = useState(false)

  if (event.kind === 'error') {
    return (
      <div className="my-1 rounded-2xl border border-ops-danger/35 bg-[linear-gradient(135deg,rgb(var(--ops-danger)/0.14),rgb(var(--ops-panel)/0.58))] p-4 shadow-[0_16px_40px_rgb(var(--ops-bg)/0.22)]" role="alert">
        <div className="mb-2 flex items-center gap-2 text-[10px] font-black uppercase tracking-[0.16em] text-ops-danger">
          <span className="h-1.5 w-1.5 rounded-full bg-ops-danger" />
          {t('conversation.systemError')}
        </div>
        <p className="m-0 whitespace-pre-wrap font-mono text-xs leading-relaxed text-ops-text/90">{event.text}</p>
      </div>
    )
  }

  if (event.kind === 'user') {
    return (
      <div className="flex justify-end">
        <article className="group relative max-w-[78%] overflow-hidden rounded-[24px] rounded-br-md border border-ops-cyan/25 bg-[linear-gradient(135deg,rgb(var(--ops-cyan)/0.18),rgb(var(--ops-cyan)/0.06)_42%,rgb(var(--ops-panel)/0.78))] px-5 py-4 shadow-[0_18px_46px_rgb(var(--ops-bg)/0.26),inset_0_1px_0_rgb(var(--ops-text)/0.05)] backdrop-blur-md">
          <div className="pointer-events-none absolute inset-x-5 top-0 h-px bg-gradient-to-r from-transparent via-cyan-200/45 to-transparent" aria-hidden="true" />
          <div className="mb-3 flex items-center justify-between gap-4">
            <span className="inline-flex items-center gap-2 text-[10px] font-black uppercase tracking-[0.16em] text-ops-cyan/90">
              <span className="h-1.5 w-1.5 rounded-full bg-ops-cyan shadow-glow" />
              {t('conversation.operator')}
            </span>
          </div>
          <p className="m-0 whitespace-pre-wrap text-[14px] font-medium leading-7 text-ops-text">{event.text}</p>
        </article>
      </div>
    )
  }

  if (event.kind === 'terminal_session_request') {
    const runtimeId = event.runtimeId
    const requestId = event.requestId ?? undefined
    const approvalToken = event.approvalToken ?? undefined
    const assetName = event.assetName ?? `asset-${event.assetId ?? ''}`
    const reason = event.reason ?? 'Agent requested terminal access.'
    const settled = Boolean(requestId && settledTerminalRequestIds?.has(requestId))
    if (settled) return null
    const canDecide = Boolean(runtimeId && requestId && approvalToken && onTerminalRequestDecision && !submittingTerminalDecision)
    return (
      <div className="my-2 rounded-2xl border border-amber-400/35 bg-amber-400/10 p-5 shadow-[0_16px_40px_rgba(0,0,0,0.18)]">
        <div className="mb-3 flex items-center gap-2 text-amber-200">
          <span className="h-2 w-2 rounded-full bg-amber-300" />
          <span className="text-[10px] font-black uppercase tracking-[0.18em]">Terminal access request</span>
        </div>
        <p className="m-0 text-sm font-semibold text-ops-text">{assetName}</p>
        <p className="mt-2 whitespace-pre-wrap text-xs leading-relaxed text-ops-muted">{reason}</p>
        {settled ? <p className="mt-3 text-xs text-ops-muted">This request has been decided.</p> : null}
        {canDecide ? (
          <div className="mt-4 flex gap-2">
            <button
              type="button"
              className="rounded-xl border border-ops-green/30 bg-ops-green/10 px-3 py-2 text-[10px] font-black uppercase tracking-[0.14em] text-ops-green hover:bg-ops-green/20"
              disabled={!canDecide}
              onClick={() => {
                if (!runtimeId || !requestId || !approvalToken || !onTerminalRequestDecision) return
                setSubmittingTerminalDecision(true)
                void onTerminalRequestDecision({ runtimeId, requestId, approvalToken, approved: true }).finally(() => {
                  setSubmittingTerminalDecision(false)
                })
              }}
            >
              {submittingTerminalDecision ? 'Submitting' : 'Allow'}
            </button>
            <button
              type="button"
              className="rounded-xl border border-ops-danger/30 bg-ops-danger/10 px-3 py-2 text-[10px] font-black uppercase tracking-[0.14em] text-ops-danger hover:bg-ops-danger/20"
              disabled={!canDecide}
              onClick={() => {
                if (!runtimeId || !requestId || !approvalToken || !onTerminalRequestDecision) return
                setSubmittingTerminalDecision(true)
                void onTerminalRequestDecision({ runtimeId, requestId, approvalToken, approved: false }).finally(() => {
                  setSubmittingTerminalDecision(false)
                })
              }}
            >
              Reject
            </button>
          </div>
        ) : null}
      </div>
    )
  }

  if (event.kind === 'terminal_session_opened') {
    return null
  }

  if (event.kind === 'terminal_session_rejected') {
    return null
  }

  if (event.kind === 'terminal_authorization_revoked') {
    return null
  }

  if ((event.kind === 'approval_required' || event.kind === 'approval_decision') && event.status === 'rejected') {
    return (
      <div className="my-2 rounded-2xl border border-ops-danger/35 bg-ops-danger/10 p-5 shadow-[0_16px_40px_rgba(0,0,0,0.2)]">
        <div className="mb-3 flex items-center gap-2 text-ops-danger">
          <svg aria-hidden="true" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="3"><circle cx="12" cy="12" r="10" /><line x1="15" y1="9" x2="9" y2="15" /><line x1="9" y1="9" x2="15" y2="15" /></svg>
          <span className="text-[10px] font-black uppercase tracking-[0.18em]">{t('conversation.accessDenied')}</span>
        </div>
        <p className="m-0 whitespace-pre-wrap rounded-xl border border-ops-danger/15 bg-ops-deep/45 p-3 font-mono text-[12px] leading-relaxed text-ops-text/80">{event.command || event.text}</p>
      </div>
    )
  }

  if (event.kind === 'final') {
    if (!event.text) return null
    return (
      <section className="relative my-2 overflow-hidden rounded-[24px] border border-ops-green/25 bg-[radial-gradient(circle_at_top_left,rgb(var(--ops-green)/0.16),transparent_36%),linear-gradient(145deg,rgb(var(--ops-panel)/0.82),rgb(var(--ops-deep)/0.76))] p-4 shadow-[0_18px_48px_rgb(var(--ops-bg)/0.24),inset_0_1px_0_rgb(var(--ops-text)/0.04)]" role="status" aria-live="polite">
        <div className="pointer-events-none absolute inset-x-7 top-0 h-px bg-gradient-to-r from-transparent via-ops-green/55 to-transparent" aria-hidden="true" />
        <div className="mb-3 flex items-center justify-between gap-3">
          <div className="flex items-center gap-3">
            <span className="flex h-8 w-8 items-center justify-center rounded-2xl border border-ops-green/30 bg-ops-green/10 text-ops-green shadow-[0_0_22px_rgba(16,185,129,0.12)]" aria-hidden="true">
              <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.8" strokeLinecap="round" strokeLinejoin="round"><path d="M20 6 9 17l-5-5" /></svg>
            </span>
            <div>
              <div className="text-[10px] font-black uppercase tracking-[0.18em] text-ops-green">{t('conversation.runComplete')}</div>
              <div className="mt-0.5 text-[12px] text-ops-muted/68">{t('conversation.finalSummary')}</div>
            </div>
          </div>
          <span className="rounded-full border border-ops-green/25 bg-ops-green/8 px-2.5 py-1 text-[9px] font-black uppercase tracking-[0.14em] text-ops-green">{t('conversation.finished')}</span>
        </div>
        <AssistantMessageContent content={event.text} />
      </section>
    )
  }

  return null
}
