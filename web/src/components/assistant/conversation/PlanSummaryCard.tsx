import { useEffect, useState } from 'react'
import { useAppearance } from '../../../hooks/useAppearance'
import type { PlanEvent, PlanStep } from '../../../types/ops'

type PlanSummaryCardProps = {
  event: PlanEvent
  onSave?: (runtimeId: string, steps: PlanStep[]) => Promise<void>
  onApprove?: (runtimeId: string) => Promise<void>
}

export function PlanSummaryCard({ event, onSave, onApprove }: PlanSummaryCardProps) {
  const { t } = useAppearance()
  const isPlanMode = event.mode === 'plan'
  const isEditable = isPlanMode && !event.lockedPlan && event.isLatest !== false
  const runtimeId = event.runtimeId ?? event.planId
  const [draftSteps, setDraftSteps] = useState<PlanStep[]>(event.steps)
  const [isSaving, setIsSaving] = useState(false)
  const [isApproving, setIsApproving] = useState(false)
  const [showSteps, setShowSteps] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const visibleSteps = isEditable ? draftSteps : event.steps
  const totalSteps = visibleSteps.length
  const completedSteps = visibleSteps.filter((step) => step.status === 'completed').length
  const runningStep = visibleSteps.find((step) => step.status === 'running')
  const progress = totalSteps > 0 ? Math.round((completedSteps / totalSteps) * 100) : 0
  const title = event.title?.trim()
  const displayTitle = title || (isPlanMode ? t('conversation.executionPlan') : t('conversation.taskPlan'))
  const isPlanningEmpty = event.loading && totalSteps === 0
  const statusLabel = event.loading ? t('conversation.planning') : isEditable ? t('conversation.review') : event.lockedPlan ? t('conversation.locked') : t('assistant.plan')

  useEffect(() => {
    setDraftSteps(event.steps)
    setError(null)
  }, [event.steps, event.version])

  const updateStep = (index: number, updates: Partial<PlanStep>) => {
    setDraftSteps((steps) => steps.map((step, stepIndex) => (stepIndex === index ? { ...step, ...updates } : step)))
  }

  const moveStep = (index: number, direction: -1 | 1) => {
    const target = index + direction
    if (target < 0 || target >= draftSteps.length) return
    setDraftSteps((steps) => {
      const next = [...steps]
      const current = next[index]
      next[index] = next[target]
      next[target] = current
      return next
    })
  }

  const deleteStep = (index: number) => {
    setDraftSteps((steps) => steps.filter((_, stepIndex) => stepIndex !== index))
  }

  const save = async () => {
    if (!runtimeId || !onSave) return
    if (draftSteps.length === 0) {
      setError('Plan must include at least one step.')
      return
    }
    setIsSaving(true)
    setError(null)
    try {
      await onSave(runtimeId, draftSteps)
    } catch (saveError) {
      setError(saveError instanceof Error ? saveError.message : 'Failed to save plan.')
    } finally {
      setIsSaving(false)
    }
  }

  const approve = async () => {
    if (!runtimeId || !onApprove) return
    if (draftSteps.length === 0) {
      setError('Plan must include at least one step.')
      return
    }
    setIsApproving(true)
    setError(null)
    try {
      if (onSave) {
        await onSave(runtimeId, draftSteps)
      }
      await onApprove(runtimeId)
    } catch (approveError) {
      setError(approveError instanceof Error ? approveError.message : 'Failed to approve plan.')
    } finally {
      setIsApproving(false)
    }
  }

  return (
    <section className={`relative overflow-hidden border border-ops-cyan/18 bg-ops-deep/88 shadow-[0_10px_28px_rgb(var(--ops-bg)/0.18),inset_0_1px_0_rgb(var(--ops-text)/0.04)] backdrop-blur-xl transition-all duration-200 ${showSteps ? 'rounded-2xl' : 'rounded-full'}`}>
      <div className="pointer-events-none absolute inset-x-0 top-0 h-px bg-gradient-to-r from-transparent via-ops-cyan/50 to-transparent" />
      <div className={showSteps ? 'p-2.5' : 'px-3 py-2'}>
        <div className={`flex items-center justify-between gap-2 ${showSteps ? 'flex-wrap' : ''}`}>
          <div className="min-w-0 flex flex-1 items-center gap-2">
            <span className={`h-2.5 w-2.5 shrink-0 rounded-full ${event.loading ? 'animate-pulse bg-ops-cyan shadow-[0_0_16px_rgb(var(--ops-cyan)/0.55)]' : isPlanMode ? 'bg-ops-cyan' : 'bg-ops-green'}`} />
            <div className="min-w-0">
              <div className="flex min-w-0 items-center gap-2">
                <h3 className="truncate text-[11px] font-black uppercase tracking-[0.2em] text-ops-text/95">{showSteps ? displayTitle : t('conversation.taskPlan')}</h3>
                {showSteps && event.updated ? <span className="rounded-full border border-ops-warning/30 bg-ops-warning/10 px-1.5 py-0.5 text-[9px] font-bold uppercase tracking-[0.16em] text-ops-warning">{t('conversation.updated')}</span> : null}
                {showSteps && isPlanMode && event.lockedPlan ? (
                  <span className="inline-flex items-center gap-1 rounded-full border border-ops-cyan/30 bg-ops-cyan/10 px-1.5 py-0.5 text-[9px] font-bold uppercase tracking-[0.14em] text-ops-cyan">
                    <svg width="9" height="9" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.4" strokeLinecap="round" strokeLinejoin="round"><rect x="3" y="11" width="18" height="11" rx="2"></rect><path d="M7 11V7a5 5 0 0110 0v4"></path></svg>
                    {t('conversation.locked')}
                  </span>
                ) : null}
              </div>
              <div className={`flex items-center gap-2 text-[10px] text-ops-muted ${showSteps ? 'mt-1' : ''}`}>
                <span className={event.loading || isEditable ? 'text-ops-cyan' : undefined}>{statusLabel}</span>
                {totalSteps > 0 ? <span className="tabular-nums">{completedSteps}/{totalSteps}</span> : null}
                {showSteps && typeof event.version === 'number' && event.version > 0 ? <span className="rounded-md bg-ops-panel/55 px-1.5 py-0.5 font-mono text-[9px] text-ops-muted/90">v{event.version}</span> : null}
              </div>
            </div>
          </div>
          <div className="flex shrink-0 items-center gap-2">
            {showSteps && totalSteps > 0 ? (
              <>
                <div className="h-1.5 w-16 overflow-hidden rounded-full bg-ops-border/30 ring-1 ring-ops-border/20">
                  <div
                    className={`h-full rounded-full transition-all duration-700 ${isPlanMode ? 'bg-gradient-to-r from-ops-cyan to-emerald-300' : 'bg-gradient-to-r from-ops-green to-emerald-300'}`}
                    style={{ width: `${progress}%` }}
                  />
                </div>
                <span className="font-mono text-[10px] text-ops-muted tabular-nums">{progress}%</span>
              </>
            ) : null}
            <button
              type="button"
              className="button-mini h-7 px-2 text-[10px] uppercase tracking-[0.14em]"
              onClick={() => setShowSteps((visible) => !visible)}
              aria-expanded={showSteps}
            >
              {showSteps ? t('conversation.hide') : t('conversation.show')}
            </button>
          </div>
        </div>

        {showSteps && isPlanningEmpty ? (
          <div className="mt-3 grid gap-1.5">
            {[0, 1, 2].map((item) => (
              <div key={item} className="flex items-center gap-2 rounded-xl border border-ops-cyan/10 bg-ops-panel/35 px-2.5 py-2">
                <span className="h-4 w-4 rounded-full bg-ops-cyan/15" />
                <span className="h-2.5 flex-1 overflow-hidden rounded-full bg-ops-border/20">
                  <span className="block h-full w-1/2 animate-pulse rounded-full bg-gradient-to-r from-transparent via-ops-cyan/35 to-transparent" />
                </span>
              </div>
            ))}
          </div>
        ) : null}

        {showSteps && totalSteps > 0 ? (
          <ol className="mt-3 flex max-h-[min(52vh,420px)] flex-col gap-1.5 overflow-y-auto pr-1">
            {visibleSteps.map((step, index) => {
              const isRunning = step.status === 'running' || (runningStep === undefined && index === completedSteps && step.status === 'pending')
              const itemClassName = step.status === 'completed'
                ? 'border-ops-green/25 bg-ops-green/8 text-ops-green'
                : isRunning
                  ? 'border-ops-cyan/35 bg-ops-cyan/10 text-ops-cyan shadow-[0_0_0_1px_rgb(var(--ops-cyan)/0.16),0_10px_24px_rgb(var(--ops-cyan)/0.08)]'
                  : 'border-ops-border/20 bg-ops-panel/35 text-ops-muted'
              const indexClassName = step.status === 'completed'
                ? 'bg-ops-green/15 text-ops-green ring-ops-green/25'
                : isRunning
                  ? 'bg-ops-cyan/15 text-ops-cyan ring-ops-cyan/35'
                  : 'bg-ops-panel/45 text-ops-muted ring-ops-border/25'

              return (
                <li key={step.id ?? `step-${index}`} className={`rounded-xl border px-2.5 py-2 text-[12px] transition-all duration-300 ${itemClassName}`} title={step.title}>
                  {isEditable ? (
                    <div className="flex flex-col gap-1.5">
                      <div className="flex items-center gap-2">
                        <span className={`flex h-5 w-5 shrink-0 items-center justify-center rounded-full text-[10px] font-black ring-1 ${indexClassName}`}>{index + 1}</span>
                        <input className="field-control min-h-0 flex-1 rounded-lg px-2 py-1 text-[12px]" value={step.title} onChange={(change) => updateStep(index, { title: change.target.value })} />
                        <button type="button" className="button-mini px-2 py-1 text-[10px]" onClick={() => moveStep(index, -1)} disabled={index === 0}>{t('conversation.up')}</button>
                        <button type="button" className="button-mini px-2 py-1 text-[10px]" onClick={() => moveStep(index, 1)} disabled={index === draftSteps.length - 1}>{t('conversation.down')}</button>
                        <button type="button" className="button-mini button-mini-danger px-2 py-1 text-[10px]" onClick={() => deleteStep(index)} disabled={draftSteps.length <= 1}>{t('common.delete')}</button>
                      </div>
                      <input className="field-control min-h-0 rounded-lg px-2 py-1 font-mono text-[11px]" value={step.command ?? ''} onChange={(change) => updateStep(index, { command: change.target.value })} placeholder={t('conversation.command')} />
                    </div>
                  ) : (
                    <div className="flex items-center gap-2.5">
                      <span className={`flex h-5 w-5 shrink-0 items-center justify-center rounded-full text-[10px] font-black ring-1 ${indexClassName}`}>{step.status === 'completed' ? '✓' : index + 1}</span>
                      <span className="min-w-0 flex-1 truncate font-semibold">{step.title}</span>
                      {isRunning ? <span className="shrink-0 rounded-full border border-ops-cyan/25 bg-ops-cyan/10 px-2 py-0.5 text-[9px] font-bold uppercase tracking-[0.16em] text-ops-cyan animate-pulse">{t('conversation.running')}</span> : null}
                    </div>
                  )}
                </li>
              )
            })}
          </ol>
        ) : null}

        {error ? <p className="mt-2 text-[11px] text-ops-danger">{error}</p> : null}

        {isEditable ? (
          <div className="mt-3 flex justify-end gap-2 border-t border-ops-border/20 pt-3">
            <button type="button" className="button-mini px-3 py-1.5 text-[11px]" onClick={save} disabled={isSaving || isApproving || !runtimeId}>{isSaving ? t('conversation.saving') : t('conversation.savePlan')}</button>
            <button type="button" className="button-mini button-mini-primary px-3 py-1.5 text-[11px]" onClick={approve} disabled={isSaving || isApproving || !runtimeId}>{isApproving ? t('conversation.starting') : t('conversation.confirmExecute')}</button>
          </div>
        ) : null}
      </div>
    </section>
  )
}
