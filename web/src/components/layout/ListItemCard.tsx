import type { ButtonHTMLAttributes, ReactNode } from 'react'

type ListItemCardProps = {
  title: string
  meta: string
  active?: boolean
  children?: ReactNode
} & ButtonHTMLAttributes<HTMLButtonElement>

export function ListItemCard({ title, meta, active = false, className = '', children, type = 'button', ...props }: ListItemCardProps) {
  const baseClassName = active ? 'list-item list-item-active' : 'list-item'
  const mergedClassName = className ? `${baseClassName} ${className}` : baseClassName

  return (
    <button type={type} className={mergedClassName} {...props}>
      <span className="list-item-title">{title}</span>
      <span className="list-item-meta">{meta}</span>
      {children}
    </button>
  )
}
