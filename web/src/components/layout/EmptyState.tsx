type EmptyStateProps = {
  title: string
  description: string
}

export function EmptyState({ title, description }: EmptyStateProps) {
  return (
    <div className="relative flex min-h-full flex-col items-center justify-center overflow-hidden rounded-[28px] border border-ops-border/15 bg-[radial-gradient(circle_at_50%_16%,rgba(6,182,212,0.13),transparent_32%),linear-gradient(180deg,rgba(21,27,40,0.28),rgba(5,8,15,0.18))] p-8 text-center" role="status">
      <div className="pointer-events-none absolute inset-8 rounded-full border border-ops-cyan/5" />
      <div className="pointer-events-none absolute h-44 w-44 rounded-full bg-ops-cyan/5 blur-3xl" />
      <div className="relative mb-5 flex h-16 w-16 items-center justify-center rounded-[22px] border border-ops-cyan/20 bg-[radial-gradient(circle_at_top,rgba(34,211,238,0.24),rgba(15,23,42,0.34))] text-2xl text-ops-cyan shadow-[0_16px_45px_rgba(8,145,178,0.16)]" aria-hidden="true">
        ✦
      </div>
      <h3 className="relative mb-2 text-sm font-black uppercase tracking-[0.14em] text-ops-text">{title}</h3>
      <p className="relative max-w-[320px] text-xs leading-6 text-ops-muted/78">{description}</p>
    </div>
  )
}
