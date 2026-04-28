import { AssetSidebar } from './components/assets/AssetSidebar'
import { AssistantPanel } from './components/assistant/AssistantPanel'
import { LoadingState } from './components/layout/LoadingState'
import { TopBar } from './components/layout/TopBar'
import { TerminalPanel } from './components/terminal/TerminalPanel'
import { useConsoleData } from './hooks/useConsoleData'

export function App() {
  const {
    tab,
    setTab,
    bootstrap,
    selectedAsset,
    selectedModel,
    setSelectedModel,
    prompt,
    setPrompt,
    events,
    history,
    setSelectedAssetId,
    runAgent,
  } = useConsoleData()

  if (!selectedAsset) {
    return <LoadingState message="Loading mock console..." />
  }

  return (
    <div className="app-shell">
      <TopBar />

      <main className="layout-grid">
        <AssetSidebar
          assets={bootstrap.assets}
          history={history}
          selectedAssetId={selectedAsset.id}
          tab={tab}
          onSelectAsset={setSelectedAssetId}
          onTabChange={setTab}
        />

        <TerminalPanel asset={selectedAsset} output={bootstrap.terminalOutput} />

        <AssistantPanel
          events={events}
          models={bootstrap.modelOptions}
          selectedModel={selectedModel}
          prompt={prompt}
          onModelChange={setSelectedModel}
          onPromptChange={setPrompt}
          onRun={() => {
            void runAgent()
          }}
        />
      </main>
    </div>
  )
}
