import type { ReactNode } from 'react'

type ActionRowProps = {
  children: ReactNode
}

export function ActionRow({ children }: ActionRowProps) {
  return <div className="action-row">{children}</div>
}
