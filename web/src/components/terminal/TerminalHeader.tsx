import type { Asset } from '../../types/ops'
import { LOCAL_TERMINAL_ASSET_ID } from '../../hooks/console/consoleShared'

type TerminalHeaderProps = {
  asset: Asset
  tabs: Asset[]
  activeAssetId: number
  busyCommand: string | null
  onSelectTab: (assetId: number) => void
  onCloseTab: (assetId: number) => void
  onClear: () => void
  onCopy: () => void
  onReconnect: () => void
}

export function TerminalHeader({
  asset,
  tabs,
  activeAssetId,
  busyCommand,
  onSelectTab,
  onCloseTab,
  onClear,
  onCopy,
  onReconnect,
}: TerminalHeaderProps) {
  return (
    <header className="flex shrink-0 flex-col border-b border-ops-border/40 bg-[#090d0b]">
      <div className="flex items-center gap-2 px-2 py-1.5">
        {/* Tabs（带关闭按钮，本地终端不可关） */}
        <div className="flex min-w-0 flex-1 items-center gap-1 overflow-x-auto" aria-label="终端标签页">
          {tabs.map((tabAsset) => {
            const isActive = tabAsset.id === activeAssetId
            const isLocal = tabAsset.id === LOCAL_TERMINAL_ASSET_ID
            const label = tabAsset.name || tabAsset.host || 'Terminal'
            return (
              <div
                key={tabAsset.id}
                className={`group relative flex max-w-[180px] shrink-0 items-center rounded-md border transition-colors ${
                  isActive
                    ? 'border-ops-green/45 bg-[#0d1410]'
                    : 'border-transparent bg-transparent hover:border-ops-border/30 hover:bg-ops-panel/60'
                }`}
              >
                <button
                  type="button"
                  className={`flex min-w-0 items-center gap-1.5 px-2.5 py-1 text-xs ${
                    isActive ? 'text-ops-green font-medium' : 'text-ops-muted'
                  }`}
                  onClick={() => onSelectTab(tabAsset.id)}
                  title={`${label}${isLocal ? '（本地）' : ''}`}
                >
                  <span
                    className={`h-1.5 w-1.5 shrink-0 rounded-full ${isActive ? 'bg-ops-green shadow-[0_0_6px_rgba(34,197,94,0.6)]' : 'bg-ops-border/60'}`}
                    aria-hidden="true"
                  />
                  <span className="truncate">{label}</span>
                </button>
                {isLocal ? null : (
                  <button
                    type="button"
                    className="mr-1 flex h-5 w-5 shrink-0 items-center justify-center rounded text-ops-muted opacity-0 transition-all hover:bg-ops-danger/15 hover:text-ops-danger group-hover:opacity-100 focus:opacity-100"
                    onClick={(event) => {
                      event.stopPropagation()
                      onCloseTab(tabAsset.id)
                    }}
                    aria-label={`关闭终端 ${label}`}
                    title={`关闭 ${label}`}
                  >
                    <svg width="10" height="10" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round"><path d="M18 6L6 18M6 6l12 12" /></svg>
                  </button>
                )}
              </div>
            )
          })}
        </div>

        {/* 状态徽标 */}
        <span className="hidden items-center gap-1.5 rounded-md border border-ops-green/35 bg-ops-green/10 px-2 py-0.5 text-[10px] uppercase tracking-[0.12em] text-ops-green md:inline-flex">
          <span className="h-1.5 w-1.5 rounded-full bg-ops-green" />
          {asset.id === LOCAL_TERMINAL_ASSET_ID ? '本地' : `${asset.host}:${asset.port}`}
        </span>

        {/* 工具按钮组 */}
        <div className="flex shrink-0 items-center gap-0.5 rounded-md border border-ops-border/30 bg-ops-panel/60 p-0.5">
          <ToolButton onClick={onClear} title="清屏" aria-label="清空终端显示">
            <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M3 6h18M8 6V4a2 2 0 012-2h4a2 2 0 012 2v2M19 6l-1 14a2 2 0 01-2 2H8a2 2 0 01-2-2L5 6" /></svg>
          </ToolButton>
          <ToolButton onClick={onCopy} title="复制最近输出" aria-label="复制终端输出">
            <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><rect x="9" y="9" width="13" height="13" rx="2" /><path d="M5 15H4a2 2 0 01-2-2V4a2 2 0 012-2h9a2 2 0 012 2v1" /></svg>
          </ToolButton>
          <ToolButton onClick={onReconnect} title="断线重连" aria-label="重连终端">
            <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M21 12a9 9 0 11-3-6.7M21 4v5h-5" /></svg>
          </ToolButton>
        </div>
      </div>

      {busyCommand ? (
        <div className="flex items-center gap-2 border-t border-amber-500/25 bg-amber-500/8 px-3 py-1 text-[11px] text-amber-200/95">
          <svg className="h-3 w-3 shrink-0 text-amber-400 animate-pulse" viewBox="0 0 24 24" fill="currentColor" aria-hidden="true">
            <circle cx="12" cy="12" r="6" />
          </svg>
          <span className="text-[10px] font-bold uppercase tracking-wider text-amber-400/95">正在执行</span>
          <code className="min-w-0 flex-1 truncate font-mono text-amber-100/90" title={busyCommand}>
            {busyCommand}
          </code>
        </div>
      ) : null}
    </header>
  )
}

type ToolButtonProps = {
  onClick: () => void
  title: string
  'aria-label': string
  children: React.ReactNode
}

function ToolButton({ onClick, title, 'aria-label': ariaLabel, children }: ToolButtonProps) {
  return (
    <button
      type="button"
      onClick={onClick}
      title={title}
      aria-label={ariaLabel}
      className="flex h-7 w-7 items-center justify-center rounded text-ops-muted transition-colors hover:bg-ops-border/25 hover:text-ops-text active:bg-ops-border/35"
    >
      {children}
    </button>
  )
}
