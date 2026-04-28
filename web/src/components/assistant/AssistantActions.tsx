import { ActionRow } from '../layout/ActionRow'
import { DangerButton, PrimaryButton, SecondaryButton } from '../layout/Button'

type AssistantActionsProps = {
  onRun: () => void
}

export function AssistantActions({ onRun }: AssistantActionsProps) {
  return (
    <>
      <ActionRow>
        <SecondaryButton>Attach Context</SecondaryButton>
        <PrimaryButton onClick={onRun}>Run Agent</PrimaryButton>
      </ActionRow>

      <ActionRow>
        <PrimaryButton>Approve</PrimaryButton>
        <DangerButton>Reject</DangerButton>
      </ActionRow>
    </>
  )
}
