import type { ReactNode } from 'react'

type PanelCardProps = {
  children: ReactNode
  fill?: boolean
  className?: string
}

export function PanelCard({ children, fill = false, className = '' }: PanelCardProps) {
  const defaultClasses = [
    'flex flex-col',
    'border border-ops-border/50',
    'bg-[linear-gradient(180deg,rgb(var(--ops-panel)/0.96),rgb(var(--ops-bg)/0.98))]',
    'shadow-[inset_0_1px_0_rgb(var(--ops-text)/0.03)]',
  ].join(' ')
  const fillClasses = fill ? 'flex-1 overflow-hidden' : ''

  return <section className={`${defaultClasses} ${fillClasses} ${className}`.trim()}>{children}</section>
}
