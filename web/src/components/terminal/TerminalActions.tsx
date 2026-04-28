import { ActionRow } from '../layout/ActionRow'
import { PrimaryButton, SecondaryButton } from '../layout/Button'

export function TerminalActions() {
  return (
    <ActionRow>
      <PrimaryButton>Connect</PrimaryButton>
      <SecondaryButton>Disconnect</SecondaryButton>
    </ActionRow>
  )
}
