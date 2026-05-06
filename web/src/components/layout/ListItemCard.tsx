import type { ButtonHTMLAttributes, ReactNode } from 'react'

type ListItemCardProps = {
  title: string
  meta: string
  active?: boolean
  children?: ReactNode
} & ButtonHTMLAttributes<HTMLButtonElement>

export function ListItemCard({ title, meta, active = false, className = '', children, type = 'button', ...props }: ListItemCardProps) {
  const baseClassName = `w-full flex flex-col items-start px-4 py-2 transition-colors ${active ? 'bg-ops-border/20 text-ops-text border-l-2 border-ops-green' : 'bg-transparent text-ops-muted hover:bg-ops-border/10 hover:text-ops-text border-l-2 border-transparent'}`
  const mergedClassName = className ? `${baseClassName} ${className}` : baseClassName

  return (
    <button type={type} className={mergedClassName} {...props}>
      <span className="text-sm font-medium leading-tight truncate w-full text-left">{title}</span>
      <span className="text-[11px] opacity-70 mt-0.5 truncate w-full text-left">{meta}</span>
      {children}
    </button>
  )
}
