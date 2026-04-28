import { TextareaField } from '../layout/TextareaField'

type PromptInputProps = {
  prompt: string
  onPromptChange: (prompt: string) => void
}

export function PromptInput({ prompt, onPromptChange }: PromptInputProps) {
  return (
    <TextareaField
      id="prompt-input"
      label="Prompt input"
      className="prompt-input"
      value={prompt}
      onChange={(event) => onPromptChange(event.target.value)}
      placeholder="Describe the task you want to run against the selected asset"
    />
  )
}
