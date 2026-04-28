type SectionHeaderProps = {
  title: string
  description: string
}

export function SectionHeader({ title, description }: SectionHeaderProps) {
  return (
    <header className="panel-header">
      <div>
        <h2 className="section-title">{title}</h2>
        <p className="section-meta">{description}</p>
      </div>
    </header>
  )
}
