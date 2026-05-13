import { useEffect, useState } from 'react'
import type { PlanEvent, PlanStep } from '../../../types/ops'

type PlanSummaryCardProps = {
  event: PlanEvent
  onSave?: (runtimeId: string, steps: PlanStep[]) => Promise<void>
  onApprove?: (runtimeId: string) => Promise<void>
}

export function PlanSummaryCard({ event, onSave, onApprove }: PlanSummaryCardProps) {
  const isPlanMode = event.mode === 'plan'
  const isEditable = isPlanMode && !event.lockedPlan && event.isLatest !== false
  const runtimeId = event.runtimeId ?? event.planId
  const [draftSteps, setDraftSteps] = useState<PlanStep[]>(event.steps)
  const [isSaving, setIsSaving] = useState(false)
  const [isApproving, setIsApproving] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const visibleSteps = isEditable ? draftSteps : event.steps
  const totalSteps = visibleSteps.length
  const completedSteps = visibleSteps.filter((step) => step.status === 'completed').length
  const runningStep = visibleSteps.find((step) => step.status === 'running')
  const progress = totalSteps > 0 ? Math.round((completedSteps / totalSteps) * 100) : 0
  const title = event.title?.trim()
  const displayTitle = title || (isPlanMode ? '' : 'Task Plan')

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
    <div className="rounded-xl border border-ops-border/30 bg-ops-deep/60 p-4 shadow-inner backdrop-blur-sm">
      <div className="mb-2.5 flex items-center justify-between gap-3">
        <div className="flex items-center gap-2">
          <div className={`h-3.5 w-1.5 rounded-full ${isPlanMode ? 'bg-ops-cyan' : 'bg-ops-green'}`} />
          {displayTitle ? <h3 className="text-[13.5px] font-bold tracking-wide text-ops-text">{displayTitle}</h3> : null}
          {isPlanMode && event.lockedPlan ? (
            <span className="inline-flex items-center gap-1 rounded-md border border-ops-cyan/35 bg-ops-cyan/10 px-1.5 py-0.5 text-[10px] font-medium text-ops-cyan">
              <svg width="10" height="10" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.4" strokeLinecap="round" strokeLinejoin="round"><rect x="3" y="11" width="18" height="11" rx="2"></rect><path d="M7 11V7a5 5 0 0110 0v4"></path></svg>
              Locked
            </span>
          ) : null}
        </div>
        <div className="flex items-center gap-2 text-[10px] tracking-wider text-ops-muted">
          {isEditable ? <span className="text-ops-cyan">Review Required</span> : null}
          {event.loading ? <span className="animate-pulse text-ops-cyan">● Planning</span> : null}
          {totalSteps > 0 ? <span className="tabular-nums">{completedSteps}/{totalSteps}</span> : null}
          {typeof event.version === 'number' && event.version > 0 ? <span className="rounded bg-ops-border/20 px-1.5 py-0.5">v{event.version}</span> : null}
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
        {visibleSteps.map((step, index) => {
          const isRunning = step.status === 'running' || (runningStep === undefined && index === completedSteps && step.status === 'pending')
          const itemClassName = step.status === 'completed'
            ? 'border-ops-green/25 bg-ops-green/5 text-ops-green'
            : isRunning
              ? 'border-ops-cyan/35 bg-ops-cyan/8 text-ops-cyan shadow-[0_0_0_1px_rgba(34,211,238,0.18)]'
              : 'border-ops-border/20 bg-black/15 text-ops-muted'

          return (
            <li key={step.id ?? `step-${index}`} className={`rounded-md border px-2.5 py-1.5 text-[12px] transition-colors ${itemClassName}`} title={step.title}>
              {isEditable ? (
                <div className="flex flex-col gap-1.5">
                  <div className="flex items-center gap-2">
                    <span className="flex h-4 w-4 shrink-0 items-center justify-center rounded-full text-[10px] font-bold">{index + 1}</span>
                    <input className="field-control min-h-0 flex-1 px-2 py-1 text-[12px]" value={step.title} onChange={(change) => updateStep(index, { title: change.target.value })} />
                    <button type="button" className="button px-2 py-1 text-[10px]" onClick={() => moveStep(index, -1)} disabled={index === 0}>Up</button>
                    <button type="button" className="button px-2 py-1 text-[10px]" onClick={() => moveStep(index, 1)} disabled={index === draftSteps.length - 1}>Down</button>
                    <button type="button" className="button px-2 py-1 text-[10px] text-ops-danger" onClick={() => deleteStep(index)} disabled={draftSteps.length <= 1}>Delete</button>
                  </div>
                  <input className="field-control min-h-0 px-2 py-1 font-mono text-[12px]" value={step.command ?? ''} onChange={(change) => updateStep(index, { command: change.target.value })} placeholder="Command" />
                </div>
              ) : (
                <div className="flex items-start gap-2.5">
                  <span className="flex h-4 w-4 shrink-0 items-center justify-center rounded-full text-[10px] font-bold">{step.status === 'completed' ? '✓' : index + 1}</span>
                  <span className="min-w-0 flex-1 truncate font-medium">{step.title}</span>
                  {isRunning ? <span className="shrink-0 text-[10px] tracking-wider text-ops-cyan/80 animate-pulse">Executing</span> : null}
                </div>
              )}
            </li>
          )
        })}
      </ol>

      {error ? <p className="mt-2 text-[11px] text-ops-danger">{error}</p> : null}

      {isEditable ? (
        <div className="mt-3 flex justify-end gap-2">
          <button type="button" className="button px-3 py-1.5 text-[11px]" onClick={save} disabled={isSaving || isApproving || !runtimeId}>{isSaving ? 'Saving...' : 'Save Plan'}</button>
          <button type="button" className="button px-3 py-1.5 text-[11px] border-ops-cyan/40 bg-ops-cyan/10 text-ops-cyan" onClick={approve} disabled={isSaving || isApproving || !runtimeId}>{isApproving ? 'Starting...' : 'Confirm & Execute'}</button>
        </div>
      ) : null}
    </div>
  )
}
