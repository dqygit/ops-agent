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
    <div className="relative mx-6 mb-4 mt-2 flex shrink-0 flex-col overflow-hidden rounded-2xl border border-ops-border/40 bg-ops-panel/80 shadow-2xl backdrop-blur-md transition-all duration-200 focus-within:border-ops-cyan/50 focus-within:shadow-glow">
      <div className="inline-flex w-fit items-center gap-2 border-b border-r border-ops-border/20 bg-ops-cyan/5 px-4 py-2 text-[10px] font-bold tracking-[0.1em] text-ops-cyan" aria-label="Context">
        <span className="h-1.5 w-1.5 rounded-full bg-ops-cyan shadow-glow animate-pulse"></span>
        {selectedAsset.name} / {selectedAsset.host}
      </div>
      <label className="sr-only" htmlFor="prompt-input">
        Command Input
      </label>
      <div className="relative w-full">
        <textarea
          id="prompt-input"
          className="min-h-[72px] w-full resize-none bg-transparent py-4 pl-5 pr-16 text-[14px] leading-relaxed text-ops-text focus:outline-none placeholder:text-ops-muted/30 font-medium scrollbar-thin"
          value={prompt}
          onChange={(event) => onPromptChange(event.target.value)}
          onKeyDown={(e) => {
            if (e.key === 'Enter' && !e.shiftKey) {
              e.preventDefault()
              void submitPrompt()
            }
          }}
          placeholder="Enter mission objectives or system commands..."
        />
        <div className="absolute bottom-2.5 right-2.5 flex items-center justify-center">
          <button
            className={`flex h-10 w-12 shrink-0 items-center justify-center rounded-xl border transition-all duration-200 active:scale-95 ${prompt.trim()
              ? 'border-ops-cyan/40 bg-ops-cyan/15 text-ops-cyan shadow-glow hover:bg-ops-cyan/25 hover:border-ops-cyan/60'
              : 'cursor-not-allowed border-ops-border/20 bg-ops-deep text-ops-muted/30'
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
      </div>
      <div className="flex items-center gap-4 border-t border-ops-border/10 bg-ops-deep/30 px-4 py-2.5">
        <div className="flex flex-1 items-center gap-4 overflow-x-auto scrollbar-none">
          <ModelSelector models={models} selectedModel={selectedModel} onModelChange={onModelChange} />

          <div
            className="group flex items-center gap-4"
          >
            <div
              className="inline-flex items-center rounded-xl border border-ops-border/20 bg-ops-deep p-1"
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
                    className={`inline-flex items-center gap-2 rounded-lg px-4 py-1.5 text-[10px] font-bold tracking-[0.1em] transition-all duration-200 active:scale-95 ${isActive
                      ? mode === 'agent'
                        ? 'bg-ops-cyan/15 text-ops-cyan border border-ops-cyan/30 shadow-glow'
                        : 'bg-ops-emerald/15 text-ops-emerald border border-ops-emerald/30 shadow-glow'
                      : 'text-ops-muted hover:text-ops-text hover:bg-ops-panel border border-transparent'
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
            <span className="hidden max-w-[280px] truncate text-[10px] font-bold tracking-[0.1em] text-ops-muted/40 transition-all duration-300 opacity-0 group-hover:opacity-100 sm:inline">
              {MODE_DESCRIPTION[runMode]}
            </span>
          </div>
        </div>
      </div>
    </div>
  )
}
