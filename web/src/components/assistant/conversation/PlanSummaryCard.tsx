import type { PlanEvent } from '../../../types/ops'

type PlanSummaryCardProps = {
  event: PlanEvent
}

export function PlanSummaryCard({ event }: PlanSummaryCardProps) {
  const isPlanMode = event.mode === 'plan'
  const totalSteps = event.steps.length
  const completedSteps = event.steps.filter((step) => step.status === 'completed').length
  const runningStep = event.steps.find((step) => step.status === 'running')
  const progress = totalSteps > 0 ? Math.round((completedSteps / totalSteps) * 100) : 0

  return (
    <div className="rounded-xl border border-ops-border/30 bg-ops-deep/60 p-4 shadow-inner backdrop-blur-sm">
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
