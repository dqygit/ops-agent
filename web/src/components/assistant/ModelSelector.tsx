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
    />
  )
}
