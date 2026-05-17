import logoUrl from '../../public/logo.png'
import { useAppearance } from '../../hooks/useAppearance'

type TopBarProps = {
  onOpenSettings?: () => void
}

export function TopBar({ onOpenSettings }: TopBarProps) {
  const { t } = useAppearance()

  return (
    <header className="flex h-[55px] shrink-0 items-center justify-between border-b border-ops-border/15 bg-ops-deep px-6 z-50 dark:border-ops-border/20 dark:bg-ops-panel/80 dark:shadow-2xl">
      <div className="flex items-center gap-5">
        <img
          src={logoUrl}
          alt="Ops Agent"
          className="h-10 w-10 rounded-xl border border-ops-cyan/40 bg-ops-cyan/10 object-cover shadow-glow"
        />
        <div className="hidden sm:block">
          <h1 className="text-[14px] font-black  tracking-[0.05em] text-ops-text leading-tight">{t('topBar.title')}</h1>
          <p className="text-[9px]  tracking-[0.2em] text-ops-muted/50 font-bold">{t('topBar.subtitle')}</p>
        </div>
      </div>
      <div className="flex items-center gap-6" aria-label="System status">
        <button type="button" onClick={onOpenSettings} className="button flex h-8 w-8 items-center justify-center p-0 active:scale-95" aria-label={t('topBar.openSettings')}>
          <svg viewBox="0 0 24 24" className="h-4 w-4" aria-hidden="true" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
            <path d="M12 15.5a3.5 3.5 0 1 0 0-7 3.5 3.5 0 0 0 0 7Z" />
            <path d="M19.4 15a1.7 1.7 0 0 0 .34 1.88l.06.06a2 2 0 1 1-2.83 2.83l-.06-.06A1.7 1.7 0 0 0 15 19.4a1.7 1.7 0 0 0-1 .6 1.7 1.7 0 0 0-.4 1.1V21a2 2 0 1 1-4 0v-.09A1.7 1.7 0 0 0 8.6 19.4a1.7 1.7 0 0 0-1.88.34l-.06.06a2 2 0 1 1-2.83-2.83l.06-.06A1.7 1.7 0 0 0 4.6 15a1.7 1.7 0 0 0-.6-1 1.7 1.7 0 0 0-1.1-.4H3a2 2 0 1 1 0-4h.09A1.7 1.7 0 0 0 4.6 8.6a1.7 1.7 0 0 0-.34-1.88l-.06-.06a2 2 0 1 1 2.83-2.83l.06.06A1.7 1.7 0 0 0 9 4.6a1.7 1.7 0 0 0 1-.6 1.7 1.7 0 0 0 .4-1.1V3a2 2 0 1 1 4 0v.09A1.7 1.7 0 0 0 15.4 4.6a1.7 1.7 0 0 0 1.88-.34l.06-.06a2 2 0 1 1 2.83 2.83l-.06.06A1.7 1.7 0 0 0 19.4 9c.38.27.6.7.6 1.1H21a2 2 0 1 1 0 4h-.09a1.7 1.7 0 0 0-1.51.9Z" />
          </svg>
        </button>
      </div>
    </header>
  )
}
