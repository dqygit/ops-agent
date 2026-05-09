import { useEffect, useMemo, useRef, useState } from 'react'
import type { RunMode } from './types/api'
import { Group as PanelGroup, Panel, Separator as PanelResizeHandle } from 'react-resizable-panels'
import { AssetModals, type AssetModalsRef } from './components/assets/AssetModals'
import { AssetSidebar } from './components/assets/AssetSidebar'
import { AssistantPanel } from './components/assistant/AssistantPanel'
import { LoadingState } from './components/layout/LoadingState'
import { TopBar } from './components/layout/TopBar'
import { SettingsDialog } from './components/settings/SettingsDialog'
import { TerminalPanel } from './components/terminal/TerminalPanel'
import { useAgentRun } from './hooks/console/useAgentRun'
import { useAssetCatalog } from './hooks/console/useAssetCatalog'
import { useConsoleBootstrap } from './hooks/console/useConsoleBootstrap'
import { useConversationState } from './hooks/console/useConversationState'
import { useTerminalSessions } from './hooks/console/useTerminalSessions'

type ActiveModal = 'settings' | null

export function App() {
  const [activeModal, setActiveModal] = useState<ActiveModal>(null)
  const [sidebarCollapsed, setSidebarCollapsed] = useState(false)
  const [runMode, setRunMode] = useState<RunMode>('agent')
  const centerFallbackClassName = 'flex h-full items-center justify-center border-x border-ops-border/40 bg-ops-deep'
  const assetModalsRef = useRef<AssetModalsRef>(null)

  const {
    bootstrap,
    isBootstrapLoaded,
    setBootstrap,
    selectedModel,
    setSelectedModel,
    prompt,
    setPrompt,
    loadError,
    setLoadError,
  } = useConsoleBootstrap()

  const {
    conversationSummaries,
    activeConversationId,
    activeConversationIdRef,
    activeConversationTitle,
    events,
    setEvents,
    runtimeSummaries,
    activeRuntimeSnapshot,
    loadConversation,
    syncConversationRuntimes,
    refreshConversationList,
    createConversation,
    deleteConversation,
    applyConversationDetailIfActive,
    upsertConversationSummary,
  } = useConversationState(selectedModel)

  const {
    terminalTabs,
    activeTerminalAssetId,
    setActiveTerminalAssetId,
    selectedAsset,
    activeTerminalTab,
    removeTerminalTab,
    sendTerminalInput,
    resizeTerminal,
    initializeLocalTerminal,
    selectAsset,
    clearActiveTerminal,
    copyActiveTerminalOutput,
    reconnectActiveTerminal,
  } = useTerminalSessions({
    assets: bootstrap.assets,
    historyByAsset: bootstrap.historyByAsset,
    setLoadError,
  })

  const {
    addAsset,
    updateAsset,
    deleteAsset,
    replaceGroups,
    replaceModelOptions,
    replaceSSHKeys,
  } = useAssetCatalog({
    bootstrap,
    setBootstrap,
    selectAsset,
    removeTerminalTab,
    setSelectedModel,
  })

  const {
    pendingApprovalRuntimeId,
    runAgent,
    approveRun,
    rejectRun,
  } = useAgentRun({
    activeConversationId,
    activeConversationIdRef,
    events,
    setEvents,
    createConversation,
    applyConversationDetailIfActive,
    upsertConversationSummary,
    refreshConversationList,
    syncConversationRuntimes,
    selectedAsset,
    activeTerminalTab,
    selectedModel,
    runMode,
    setLoadError,
  })

  const terminalOutput = activeTerminalTab?.output ?? ''
  const selectedAssetId = selectedAsset?.id ?? 0
  const [isConsoleInitialized, setIsConsoleInitialized] = useState(false)

  const busyCommand = useMemo(() => {
    const commandsInOrder: Array<{ id: string; cmd: string }> = []
    const ended = new Set<string>()
    for (const evt of events) {
      if (evt.kind === 'command_start') {
        commandsInOrder.push({ id: evt.commandId, cmd: evt.command })
      } else if (evt.kind === 'command_end') {
        ended.add(evt.commandId)
      }
    }
    for (let i = commandsInOrder.length - 1; i >= 0; i -= 1) {
      const item = commandsInOrder[i]
      if (!ended.has(item.id)) return item.cmd
    }
    return null
  }, [events])

  useEffect(() => {
    if (!isBootstrapLoaded || loadError || isConsoleInitialized) {
      return
    }

    let active = true

    void (async () => {
      try {
        initializeLocalTerminal(bootstrap.terminalSessionId, bootstrap.terminalOutput)

        const items = await refreshConversationList()
        if (!active) {
          return
        }

        if (items.length > 0) {
          const [latestConversation] = [...items].sort((left, right) =>
            right.updatedAt.localeCompare(left.updatedAt)
          )
          await loadConversation(latestConversation.id)

          if (!active) {
            return
          }

          setIsConsoleInitialized(true)
          return
        }

        await createConversation()

        if (!active) {
          return
        }

        setIsConsoleInitialized(true)
      } catch (error: unknown) {
        if (!active) {
          return
        }

        setLoadError(
          error instanceof Error
            ? `Failed to load conversations: ${error.message}`
            : 'Failed to load conversations.'
        )
        setIsConsoleInitialized(false)
      }
    })()

    return () => {
      active = false
    }
  }, [
    bootstrap.terminalOutput,
    bootstrap.terminalSessionId,
    createConversation,
    initializeLocalTerminal,
    isBootstrapLoaded,
    isConsoleInitialized,
    loadConversation,
    loadError,
    refreshConversationList,
    setLoadError,
  ])

  if (loadError && bootstrap.assets.length === 0) {
    return <LoadingState message={loadError} />
  }

  return (
    <div className="flex h-screen w-screen flex-col overflow-hidden bg-ops-bg text-ops-text">
      <TopBar onOpenSettings={() => setActiveModal('settings')} />

      <main className="flex flex-1 overflow-hidden">
        <AssetSidebar
          assets={bootstrap.assets}
          groups={bootstrap.groups}
          conversationSummaries={conversationSummaries}
          activeConversationId={activeConversationId}
          selectedAssetId={selectedAssetId}
          collapsed={sidebarCollapsed}
          onToggleCollapse={() => setSidebarCollapsed((current) => !current)}
          onSelectAsset={selectAsset}
          onSelectConversation={(conversationId) => {
            void loadConversation(conversationId)
          }}
          onDeleteConversation={(conversationId) => {
            void deleteConversation(conversationId)
          }}
          onUpdateAsset={updateAsset}
          onDeleteAsset={deleteAsset}
          onAddAsset={() => assetModalsRef.current?.openAddModal()}
          onEditAsset={(asset) => assetModalsRef.current?.openEditModal(asset)}
          onDeleteAssetConfirm={(asset) => assetModalsRef.current?.openDeleteModal(asset)}
        />

        <PanelGroup orientation="horizontal" className="h-full min-w-0 flex-1">
          <Panel defaultSize={selectedAsset ? 66 : 100} minSize={36}>
            {selectedAsset ? (
              <AssistantPanel
                conversationSummaries={conversationSummaries}
                activeConversationId={activeConversationId}
                activeConversationTitle={activeConversationTitle}
                events={events}
                pendingApprovalRuntimeId={pendingApprovalRuntimeId}
                runtimeSummaries={runtimeSummaries}
                activeRuntimeSnapshot={activeRuntimeSnapshot}
                models={bootstrap.modelOptions}
                selectedModel={selectedModel}
                prompt={prompt}
                runMode={runMode}
                selectedAsset={selectedAsset}
                loadError={loadError}
                onModelChange={setSelectedModel}
                onRunModeChange={setRunMode}
                onPromptChange={setPrompt}
                onCreateConversation={() => {
                  void createConversation()
                }}
                onSelectConversation={(conversationId) => {
                  void loadConversation(conversationId)
                }}
                onDeleteConversation={(conversationId) => {
                  void deleteConversation(conversationId)
                }}
                onRun={(nextPrompt) => {
                  return runAgent(nextPrompt)
                }}
                onApprove={() => {
                  void approveRun()
                }}
                onReject={() => {
                  void rejectRun()
                }}
              />
            ) : loadError ? (
              <section className={centerFallbackClassName}>
                <p className="text-ops-danger text-sm">{loadError}</p>
              </section>
            ) : (
              <section className={centerFallbackClassName}>
                <p className="text-ops-muted text-sm">暂无目标连接，请先在左侧选择或添加资产。</p>
              </section>
            )}
          </Panel>

          {selectedAsset ? (
            <>
              <PanelResizeHandle className="w-1 bg-transparent group cursor-col-resize flex flex-col items-center justify-center relative">
                <div className="absolute inset-y-0 -left-1 -right-1 z-10" />
                <div className="w-px h-16 bg-ops-border/50 group-hover:bg-ops-cyan group-active:bg-ops-cyan transition-colors" />
              </PanelResizeHandle>

              <Panel defaultSize={34} minSize={24}>
                <TerminalPanel
                  asset={selectedAsset}
                  tabs={terminalTabs.map((item) => item.asset)}
                  activeAssetId={activeTerminalAssetId}
                  output={terminalOutput}
                  busyCommand={busyCommand}
                  onInput={sendTerminalInput}
                  onResize={resizeTerminal}
                  onSelectTab={setActiveTerminalAssetId}
                  onCloseTab={removeTerminalTab}
                  onClear={clearActiveTerminal}
                  onCopy={() => {
                    void copyActiveTerminalOutput()
                  }}
                  onReconnect={() => {
                    void reconnectActiveTerminal()
                  }}
                />
              </Panel>
            </>
          ) : null}
        </PanelGroup>
      </main>

      <AssetModals
        ref={assetModalsRef}
        groups={bootstrap.groups}
        sshKeys={bootstrap.sshKeys}
        onAddAsset={addAsset}
        onUpdateAsset={async (id, payload) => {
          await updateAsset(id, payload)
        }}
        onDeleteAsset={deleteAsset}
      />

      {activeModal === 'settings' ? (
        <SettingsDialog
          initialGroups={bootstrap.groups}
          sshKeys={bootstrap.sshKeys}
          selectedModel={selectedModel}
          onSelectedModelChange={setSelectedModel}
          onGroupsChange={replaceGroups}
          onModelOptionsChange={replaceModelOptions}
          onSSHKeysChange={replaceSSHKeys}
          onClose={() => setActiveModal(null)}
        />
      ) : null}
    </div>
  )
}
