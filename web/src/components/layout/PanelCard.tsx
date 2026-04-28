import type { ReactNode } from 'react'

type PanelCardProps = {
  children: ReactNode
  fill?: boolean
}

export function PanelCard({ children, fill = false }: PanelCardProps) {
  return <section className={fill ? 'panel-card panel-fill' : 'panel-card'}>{children}</section>
}
