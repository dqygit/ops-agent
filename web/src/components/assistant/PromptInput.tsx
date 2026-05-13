import type { RunMode } from '../../types/api'
import type { Asset } from '../../types/ops'
import { ModelSelector } from './ModelSelector'

type PromptInputProps = {
  prompt: string
  models: string[]
  selectedModel: string
  runMode: RunMode
  selectedAsset: Asset
  onPromptChange: (prompt: string) => void
  onModelChange: (model: string) => void
  onRunModeChange: (mode: RunMode) => void
  onRun: (prompt: string) => Promise<void>
}

const MODE_DESCRIPTION: Record<RunMode, string> = {
  agent: 'Dynamic task execution with realtime tool invocation. Best for exploration.',
  plan: 'Structured multi-step planning with sequential execution and state tracking.',
}

const MODE_LABEL: Record<RunMode, string> = {
  agent: 'Agent',
  plan: 'Plan',
}

export function PromptInput({
  prompt,
  models,
  selectedModel,
  runMode,
  selectedAsset,
  onPromptChange,
  onModelChange,
  onRunModeChange,
  onRun,
}: PromptInputProps) {
  const submitPrompt = async () => {
    const currentPrompt = prompt

    if (!currentPrompt.trim()) {
      return
    }

    onPromptChange('')

    try {
      await onRun(currentPrompt)
    }
    catch {
      onPromptChange(currentPrompt)
    }
  }

  return (
    <div className="relative mx-6 mb-4 mt-2 shrink-0 rounded-[28px] border border-ops-cyan/10 bg-ops-deep/80 p-[1px] shadow-[0_24px_70px_rgba(0,0,0,0.45)] backdrop-blur-xl transition-all duration-300 before:pointer-events-none before:absolute before:inset-x-8 before:bottom-[-1px] before:h-px before:bg-gradient-to-r before:from-transparent before:via-ops-cyan/60 before:to-transparent focus-within:border-ops-cyan/40 focus-within:shadow-[0_28px_80px_rgba(0,0,0,0.55),0_0_36px_rgba(6,182,212,0.14)]">
      <div className="relative overflow-hidden rounded-[27px] border border-white/[0.04] bg-[radial-gradient(circle_at_18%_0%,rgba(6,182,212,0.14),transparent_34%),linear-gradient(180deg,rgba(21,27,40,0.92),rgba(5,8,15,0.96))]">
        <div className="pointer-events-none absolute inset-0 bg-[linear-gradient(90deg,rgba(255,255,255,0.025)_1px,transparent_1px),linear-gradient(180deg,rgba(255,255,255,0.018)_1px,transparent_1px)] bg-[size:28px_28px] opacity-40" />
        <div className="relative flex items-center justify-between gap-3 border-b border-white/[0.04] px-4 py-3">
          <div className="flex min-w-0 items-center gap-2" aria-label="Context">
            <span className="relative flex h-2.5 w-2.5 shrink-0">
              <span className="absolute inline-flex h-full w-full animate-ping rounded-full bg-ops-cyan opacity-30" />
              <span className="relative inline-flex h-2.5 w-2.5 rounded-full bg-ops-cyan shadow-glow" />
            </span>
            <span className="truncate text-[11px] font-black uppercase tracking-[0.18em] text-ops-cyan/90">
              {selectedAsset.name}
            </span>
            <span className="hidden truncate rounded-full border border-ops-border/30 bg-ops-deep/70 px-2.5 py-1 font-mono text-[10px] text-ops-muted/70 sm:inline">
              {selectedAsset.host || 'local'}
            </span>
          </div>
          <div className="hidden items-center gap-1.5 rounded-full border border-ops-border/20 bg-ops-deep/60 px-2.5 py-1 text-[10px] font-bold uppercase tracking-[0.14em] text-ops-muted/55 sm:flex">
            <span className="text-ops-cyan/70">Enter</span>
            <span>send</span>
            <span className="mx-1 h-1 w-1 rounded-full bg-ops-border/60" />
            <span className="text-ops-cyan/70">Shift Enter</span>
            <span>line</span>
          </div>
        </div>

        <label className="sr-only" htmlFor="prompt-input">
          Command Input
        </label>
        <div className="relative">
          <textarea
            id="prompt-input"
            className="min-h-[86px] w-full resize-none bg-transparent px-5 pb-5 pr-20 pt-4 text-[15px] font-medium leading-relaxed text-ops-text caret-ops-cyan outline-none placeholder:text-ops-muted/32 scrollbar-thin"
            value={prompt}
            onChange={(event) => onPromptChange(event.target.value)}
            onKeyDown={(e) => {
              if (e.key === 'Enter' && !e.shiftKey) {
                e.preventDefault()
                void submitPrompt()
              }
            }}
            placeholder="Describe the operation, paste logs, or ask the agent to investigate..."
          />
          <button
            className={`absolute bottom-4 right-4 flex h-12 w-12 shrink-0 items-center justify-center rounded-2xl border transition-all duration-200 active:scale-95 ${prompt.trim()
              ? 'border-ops-cyan/45 bg-ops-cyan text-ops-deep shadow-[0_0_28px_rgba(6,182,212,0.38)] hover:-translate-y-0.5 hover:bg-cyan-300 hover:shadow-[0_0_36px_rgba(6,182,212,0.55)]'
              : 'cursor-not-allowed border-ops-border/20 bg-ops-panel/70 text-ops-muted/25'
              }`}
            type="button"
            onClick={() => {
              void submitPrompt()
            }}
            disabled={!prompt.trim()}
            aria-label="Run Mission"
          >
            <svg aria-hidden="true" viewBox="0 0 24 24" focusable="false" className="h-5 w-5 fill-current"><path d="M5 3.8 20.2 12 5 20.2v-6.1L13.4 12 5 9.9z" /></svg>
          </button>
        </div>

        <div className="relative flex items-center gap-3 border-t border-white/[0.04] bg-ops-deep/45 px-4 py-3">
          <div className="flex flex-1 items-center gap-3 overflow-x-auto scrollbar-none">
            <ModelSelector models={models} selectedModel={selectedModel} onModelChange={onModelChange} />

            <div className="group flex min-w-fit items-center gap-3">
              <div
                className="inline-flex items-center rounded-full border border-ops-border/20 bg-ops-deep/75 p-1 shadow-[inset_0_1px_0_rgba(255,255,255,0.03)]"
                role="radiogroup"
                aria-label="Mode"
              >
                {(Object.keys(MODE_LABEL) as RunMode[]).map((mode) => {
                  const isActive = runMode === mode
                  return (
                    <button
                      key={mode}
                      type="button"
                      role="radio"
                      aria-checked={isActive}
                      title={MODE_DESCRIPTION[mode]}
                      onClick={() => onRunModeChange(mode)}
                      className={`inline-flex items-center gap-2 rounded-full border px-3.5 py-1.5 text-[10px] font-black uppercase tracking-[0.12em] transition-all duration-200 active:scale-95 ${isActive
                        ? mode === 'agent'
                          ? 'border-ops-cyan/35 bg-ops-cyan/16 text-ops-cyan shadow-[0_0_18px_rgba(6,182,212,0.16)]'
                          : 'border-ops-green/35 bg-ops-green/15 text-ops-green shadow-[0_0_18px_rgba(16,185,129,0.14)]'
                        : 'border-transparent text-ops-muted/55 hover:bg-ops-panel/80 hover:text-ops-text'
                        }`}
                    >
                      {mode === 'plan' ? (
                        <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="3"><rect x="3" y="11" width="18" height="11" rx="2"></rect><path d="M7 11V7a5 5 0 0110 0v4"></path></svg>
                      ) : (
                        <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="3"><circle cx="12" cy="12" r="3" /><path d="M12 1v6M12 17v6M4.22 4.22l4.24 4.24M15.54 15.54l4.24 4.24M1 12h6M17 12h6M4.22 19.78l4.24-4.24M15.54 8.46l4.24-4.24" /></svg>
                      )}
                      {MODE_LABEL[mode]}
                    </button>
                  )
                })}
              </div>
              <span className="hidden max-w-[280px] truncate text-[10px] font-bold tracking-[0.08em] text-ops-muted/35 transition-all duration-300 group-hover:text-ops-muted/70 lg:inline">
                {MODE_DESCRIPTION[runMode]}
              </span>
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}
