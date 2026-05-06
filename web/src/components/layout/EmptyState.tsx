type EmptyStateProps = {
  title: string
  description: string
}

export function EmptyState({ title, description }: EmptyStateProps) {
  return (
    <div className="flex flex-col items-center justify-center p-8 text-center" role="status">
      <div className="w-12 h-12 flex items-center justify-center rounded-full bg-ops-border/10 text-ops-muted text-xl mb-4 border border-ops-border/20" aria-hidden="true">
        ∅
      </div>
      <h3 className="text-sm font-medium text-ops-text mb-1">{title}</h3>
      <p className="text-xs text-ops-muted max-w-[250px] leading-relaxed">{description}</p>
    </div>
  )
}
