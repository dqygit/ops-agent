import { Button } from '../layout/Button'

type AssetTabsProps = {
  tab: 'assets' | 'history'
  onTabChange: (tab: 'assets' | 'history') => void
}

export function AssetTabs({ tab, onTabChange }: AssetTabsProps) {
  return (
    <div className="tab-row" role="tablist" aria-label="Resource explorer tabs">
      <Button
        variant={tab === 'assets' ? 'tab-active' : 'default'}
        onClick={() => onTabChange('assets')}
        role="tab"
        aria-selected={tab === 'assets'}
      >
        主机资源
      </Button>
      <Button
        variant={tab === 'history' ? 'tab-active' : 'default'}
        onClick={() => onTabChange('history')}
        role="tab"
        aria-selected={tab === 'history'}
      >
        直接连接
      </Button>
    </div>
  )
}
