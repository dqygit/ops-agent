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
    <div className="prompt-composer">
      <div className="prompt-context" aria-label="Current host context">
        @{selectedAsset.host}
      </div>
      <label className="sr-only" htmlFor="prompt-input">
        Prompt input
      </label>
      <textarea
        id="prompt-input"
        className="field-control prompt-input"
        value={prompt}
        onChange={(event) => onPromptChange(event.target.value)}
        placeholder="到任意主机执行命令查询、排查错误和任务处理等任何事情"
      />
      <div className="prompt-toolbar">
        <ModelSelector models={models} selectedModel={selectedModel} onModelChange={onModelChange} />
        <button className="run-agent-icon-button" type="button" onClick={onRun} aria-label="Run Agent">
          <svg aria-hidden="true" viewBox="0 0 24 24" focusable="false">
            <path d="M5 3.8 20.2 12 5 20.2v-6.1L13.4 12 5 9.9z" />
          </svg>
        </button>
      </div>
    </div>
  )
}
