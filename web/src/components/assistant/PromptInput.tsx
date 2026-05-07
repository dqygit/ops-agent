import type { Asset } from '../../types/ops'
import { ModelSelector } from './ModelSelector'

type PromptInputProps = {
  prompt: string
  models: string[]
  selectedModel: string
  selectedAsset: Asset
  onPromptChange: (prompt: string) => void
  onModelChange: (model: string) => void
  onRun: () => void
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
  return (
    <div className="flex flex-col m-4 border border-ops-border/40 rounded-xl overflow-hidden focus-within:border-ops-green/50 transition-colors shrink-0 bg-ops-deep/50 relative">
      <div className="px-3 py-1.5 text-xs text-ops-cyan bg-ops-cyan/5 border-b border-ops-border/20 inline-block w-fit rounded-br-lg" aria-label="Current host context">
        @{selectedAsset.host}
      </div>
      <label className="sr-only" htmlFor="prompt-input">
        Prompt input
      </label>
      <textarea
        id="prompt-input"
        className="w-full bg-transparent text-ops-text p-3 min-h-[80px] resize-none focus:outline-none placeholder:text-ops-muted/50 text-sm"
        value={prompt}
        onChange={(event) => onPromptChange(event.target.value)}
        onKeyDown={(e) => {
          if (e.key === 'Enter' && !e.shiftKey) {
            e.preventDefault()
            if (prompt.trim()) {
              onRun()
            } else {
              alert('请输入内容')
            }
          }
        }}
        placeholder="到任意主机执行命令查询、排查错误和任务处理等任何事情"
      />
      <div className="flex items-center justify-between px-2 pb-2">
        <ModelSelector models={models} selectedModel={selectedModel} onModelChange={onModelChange} />
        <button
          className={`w-8 h-8 rounded shrink-0 flex items-center justify-center transition-colors shadow-lg ${
            prompt.trim() ? 'bg-ops-cyan text-ops-bg hover:bg-ops-cyan/90' : 'bg-ops-muted/20 text-ops-muted cursor-not-allowed'
          }`}
          type="button"
          onClick={() => {
            if (prompt.trim()) {
              onRun()
            } else {
              alert('请输入内容')
            }
          }}
          aria-label="Run Agent"
        >
          <svg aria-hidden="true" viewBox="0 0 24 24" focusable="false" className="w-4 h-4 fill-current"><path d="M5 3.8 20.2 12 5 20.2v-6.1L13.4 12 5 9.9z" /></svg>
        </button>
      </div>
    </div>
  )
}
