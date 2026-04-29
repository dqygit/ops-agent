import { ActionRow } from '../layout/ActionRow'
import { DangerButton, PrimaryButton } from '../layout/Button'

type AssistantActionsProps = {
  onApprove: () => void
  onReject: () => void
}

export function AssistantActions({ onApprove, onReject }: AssistantActionsProps) {
  return (
    <ActionRow>
      <PrimaryButton onClick={onApprove}>Approve</PrimaryButton>
      <DangerButton onClick={onReject}>Reject</DangerButton>
    </ActionRow>
  )
}
