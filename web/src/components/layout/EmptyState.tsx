type EmptyStateProps = {
  title: string
  description: string
}

export function EmptyState({ title, description }: EmptyStateProps) {
  return (
    <div className="flex flex-col items-center justify-center p-8 text-center" role="status">
      <div className="mb-4 flex h-14 w-14 items-center justify-center rounded-2xl border border-ops-cyan/15 bg-[radial-gradient(circle_at_top,rgba(34,211,238,0.18),rgba(15,23,42,0.2))] text-xl text-ops-cyan shadow-[0_10px_30px_rgba(8,145,178,0.12)]" aria-hidden="true">
        ✦
      </div>
      <h3 className="mb-1 text-sm font-medium tracking-[0.01em] text-ops-text">{title}</h3>
      <p className="max-w-[280px] text-xs leading-relaxed text-ops-muted">{description}</p>
    </div>
  )
}
