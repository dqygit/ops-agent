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
  agent: '边规划边执行，每步可重试或重规划。适合探索性、不确定结果的任务。',
  plan: '一次锁定全部步骤，按顺序执行；中高风险逐条审批。适合规范化、可预知的流程。',
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
    <div className="m-4 flex shrink-0 flex-col overflow-hidden rounded-md border border-ops-border/50 bg-[#090d0b] shadow-[inset_0_1px_0_rgba(255,255,255,0.03)]">
      <div className="inline-flex w-fit border-b border-r border-ops-border/35 bg-ops-green/10 px-3 py-1 text-[11px] text-ops-green" aria-label="当前主机上下文">
        @{selectedAsset.host || selectedAsset.name}
      </div>
      <label className="sr-only" htmlFor="prompt-input">
        指令输入
      </label>
      <textarea
        id="prompt-input"
        className="min-h-[92px] w-full resize-none bg-transparent p-3 text-sm leading-6 text-ops-text focus:outline-none placeholder:text-ops-muted/50"
        value={prompt}
        onChange={(event) => onPromptChange(event.target.value)}
        onKeyDown={(e) => {
          if (e.key === 'Enter' && !e.shiftKey) {
            e.preventDefault()
            void submitPrompt()
          }
        }}
        placeholder="到任意主机执行命令查询、排查错误和任务处理等任何事情"
      />
      <div className="flex flex-wrap items-center justify-between gap-2 border-t border-ops-border/10 px-2.5 pb-2 pt-2">
        <div className="flex flex-wrap items-center gap-2">
          <ModelSelector models={models} selectedModel={selectedModel} onModelChange={onModelChange} />

          <div
            className="inline-flex items-center rounded-md border border-ops-border/40 bg-ops-panel p-0.5"
            role="radiogroup"
            aria-label="执行模式"
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
                  className={`inline-flex items-center gap-1 rounded px-2 py-1 text-[11px] font-medium transition-colors ${
                    isActive
                      ? mode === 'plan'
                        ? 'bg-ops-cyan/15 text-ops-cyan shadow-[inset_0_0_0_1px_rgba(34,211,238,0.35)]'
                        : 'bg-ops-green/15 text-ops-green shadow-[inset_0_0_0_1px_rgba(34,197,94,0.35)]'
                      : 'text-ops-muted hover:text-ops-text'
                  }`}
                >
                  {mode === 'plan' ? (
                    <svg width="11" height="11" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.4" strokeLinecap="round" strokeLinejoin="round"><rect x="3" y="11" width="18" height="11" rx="2"></rect><path d="M7 11V7a5 5 0 0110 0v4"></path></svg>
                  ) : (
                    <svg width="11" height="11" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.4" strokeLinecap="round" strokeLinejoin="round"><circle cx="12" cy="12" r="3" /><path d="M12 1v6M12 17v6M4.22 4.22l4.24 4.24M15.54 15.54l4.24 4.24M1 12h6M17 12h6M4.22 19.78l4.24-4.24M15.54 8.46l4.24-4.24" /></svg>
                  )}
                  {MODE_LABEL[mode]}
                </button>
              )
            })}
          </div>
          <span className="hidden max-w-[260px] truncate text-[11px] text-ops-muted/85 sm:inline" title={MODE_DESCRIPTION[runMode]}>
            {MODE_DESCRIPTION[runMode]}
          </span>
        </div>
        <button
          className={`flex h-9 min-w-9 shrink-0 items-center justify-center rounded-md border transition-colors ${
            prompt.trim()
              ? 'border-ops-green/60 bg-ops-green/12 text-ops-green hover:bg-ops-green/18'
              : 'cursor-not-allowed border-ops-border/40 bg-ops-panel text-ops-muted'
          }`}
          type="button"
          onClick={() => {
            void submitPrompt()
          }}
          disabled={!prompt.trim()}
          aria-label="执行任务"
        >
          <svg aria-hidden="true" viewBox="0 0 24 24" focusable="false" className="h-4 w-4 fill-current"><path d="M5 3.8 20.2 12 5 20.2v-6.1L13.4 12 5 9.9z" /></svg>
        </button>
      </div>
    </div>
  )
}
