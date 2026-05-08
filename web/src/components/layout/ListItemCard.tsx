import type { ButtonHTMLAttributes, ReactNode } from 'react'

type ListItemCardProps = {
  title: string
  meta: string
  active?: boolean
  children?: ReactNode
} & ButtonHTMLAttributes<HTMLButtonElement>

export function ListItemCard({ title, meta, active = false, className = '', children, type = 'button', ...props }: ListItemCardProps) {
  const baseClassName = `w-full flex flex-col items-start border-l-2 px-4 py-2.5 text-left transition-colors ${active ? 'border-l-ops-green bg-ops-green/8 text-ops-text' : 'border-l-transparent bg-transparent text-ops-muted hover:bg-ops-panel/80 hover:text-ops-text'}`
  const mergedClassName = className ? `${baseClassName} ${className}` : baseClassName

  return (
    <button type={type} className={mergedClassName} {...props}>
      <span className="w-full truncate text-sm font-medium leading-tight">{title}</span>
      <span className="mt-1 w-full truncate text-[11px] uppercase tracking-[0.08em] opacity-70">{meta}</span>
      {children}
    </button>
  )
}
