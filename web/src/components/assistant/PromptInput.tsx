import type { Asset } from '../../types/ops'
import { ModelSelector } from './ModelSelector'

type PromptInputProps = {
  prompt: string
  models: string[]
  selectedModel: string
  selectedAsset: Asset
  onPromptChange: (prompt: string) => void
  onModelChange: (model: string) => void
  onRun: () => Promise<void>
}

export function PromptInput({
  prompt,
  models,
  selectedModel,
  selectedAsset,
  onPromptChange,
  onModelChange,
  onRun,
}: PromptInputProps) {
  const submitPrompt = async () => {
    if (!prompt.trim()) {
      return
    }

    await onRun()
    onPromptChange('')
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
      <div className="flex items-center justify-between border-t border-ops-border/10 px-2.5 pb-2 pt-2">
        <ModelSelector models={models} selectedModel={selectedModel} onModelChange={onModelChange} />
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
