import { SelectField } from '../layout/SelectField'

type ModelSelectorProps = {
  models: string[]
  selectedModel: string
  onModelChange: (model: string) => void
}

export function ModelSelector({ models, selectedModel, onModelChange }: ModelSelectorProps) {
  return (
    <SelectField
      id="model-selector"
      label="Model selector"
      value={selectedModel}
      options={models.map((model) => ({ label: model, value: model }))}
      onChange={(event) => onModelChange(event.target.value)}
      className="max-w-[220px] rounded-full border-ops-cyan/10 bg-ops-deep/70 px-3 py-1.5 text-[11px] font-bold tracking-[0.08em] text-ops-muted hover:border-ops-cyan/30 hover:text-ops-text focus:border-ops-cyan/60"
    />
  )
}
