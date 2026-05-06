import type { ReactNode } from 'react'

type ActionRowProps = {
  children: ReactNode
}

export function ActionRow({ children }: ActionRowProps) {
  return <div className="flex items-center gap-3 p-4 border-t border-ops-border/20 shrink-0">{children}</div>
}
