type SectionHeaderProps = {
  title: string
  description: string
}

export function SectionHeader({ title, description }: SectionHeaderProps) {
  return (
    <header className="p-4 border-b border-ops-border/20 bg-ops-panel shrink-0">
      <div>
        <h2 className="text-sm font-medium text-ops-text">{title}</h2>
        <p className="text-xs text-ops-muted mt-1 leading-relaxed">{description}</p>
      </div>
    </header>
  )
}
