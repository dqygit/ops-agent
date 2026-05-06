import type { ReactNode } from 'react'

type PanelCardProps = {
  children: ReactNode
  fill?: boolean
  className?: string
}

export function PanelCard({ children, fill = false, className = '' }: PanelCardProps) {
  const defaultClasses = "flex flex-col bg-ops-panel"
  const fillClasses = fill ? "flex-1 overflow-hidden" : ""
  
  return (
    <section className={`${defaultClasses} ${fillClasses} ${className}`.trim()}>
      {children}
    </section>
  )
}
