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
    'bg-[linear-gradient(180deg,rgba(8,12,10,0.96),rgba(11,16,14,0.98))]',
    'shadow-[inset_0_1px_0_rgba(255,255,255,0.03)]',
  ].join(' ')
  const fillClasses = fill ? 'flex-1 overflow-hidden' : ''

  return <section className={`${defaultClasses} ${fillClasses} ${className}`.trim()}>{children}</section>
}
