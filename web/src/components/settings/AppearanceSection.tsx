import { languages, type Language } from '../../i18n/translations'
import { type ThemeMode, useAppearance } from '../../hooks/useAppearance'
import type { AppearanceSectionProps } from './settingsTypes'

const themeOptions: ThemeMode[] = ['system', 'dark', 'light']

function getThemeOptionLabel(themeMode: ThemeMode, t: ReturnType<typeof useAppearance>['t']) {
  if (themeMode === 'system') {
    return t('settings.themeSystem')
  }

  return themeMode === 'dark' ? t('settings.themeDark') : t('settings.themeLight')
}

export function AppearanceSection({ language, themeMode, resolvedTheme, onLanguageChange, onThemeModeChange }: AppearanceSectionProps) {
  const { t } = useAppearance()
  const themeLabel = resolvedTheme === 'dark' ? t('settings.themeDark') : t('settings.themeLight')
  const currentThemeLabel = themeMode === 'system'
    ? t('settings.currentThemeWithSystem', { theme: themeLabel })
    : t('settings.currentTheme', { theme: themeLabel })

  return (
    <div className="flex flex-col gap-8">
      <div className="flex items-center justify-between pb-4 border-b border-ops-border/20">
        <div>
          <h4 className="text-[14px] font-bold tracking-[0.15em] text-ops-text">{t('settings.appearance')}</h4>
          <p className="text-[10px] font-medium text-ops-muted mt-1 tracking-wider opacity-60">{t('settings.appearanceDescription')}</p>
        </div>
      </div>

      <section className="bg-ops-deep/40 p-6 rounded-2xl border border-ops-border/20 flex flex-col gap-8">
        <div className="flex flex-col gap-4">
          <div>
            <h5 className="text-[12px] font-bold tracking-[0.12em] text-ops-text">{t('settings.language')}</h5>
          </div>
          <div className="flex flex-wrap gap-2">
            {languages.map((option) => (
              <button
                key={option.value}
                type="button"
                className={language === option.value ? 'button-mini button-mini-primary' : 'button-mini'}
                onClick={() => onLanguageChange(option.value as Language)}
              >
                {option.label}
              </button>
            ))}
          </div>
        </div>

        <div className="flex flex-col gap-4">
          <div>
            <h5 className="text-[12px] font-bold tracking-[0.12em] text-ops-text">{t('settings.theme')}</h5>
            <p className="text-[10px] font-medium text-ops-muted mt-1 tracking-wider opacity-60">{currentThemeLabel}</p>
          </div>
          <div className="flex flex-wrap gap-2">
            {themeOptions.map((option) => (
              <button
                key={option}
                type="button"
                className={themeMode === option ? 'button-mini button-mini-primary' : 'button-mini'}
                onClick={() => onThemeModeChange(option)}
              >
                {getThemeOptionLabel(option, t)}
              </button>
            ))}
          </div>
        </div>
      </section>
    </div>
  )
}
