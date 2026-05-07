import { type FormEvent, useState } from 'react'
import { Group as PanelGroup, Panel, Separator as PanelResizeHandle } from 'react-resizable-panels'
import { AssetSidebar } from './components/assets/AssetSidebar'
import { AssistantPanel } from './components/assistant/AssistantPanel'
import { LoadingState } from './components/layout/LoadingState'
import { TopBar } from './components/layout/TopBar'
import { SettingsDialog } from './components/settings/SettingsDialog'
import { TerminalPanel } from './components/terminal/TerminalPanel'
import { useConsoleData } from './hooks/useConsoleData'
import type { Asset } from './types/ops'

type ActiveModal = 'add-asset' | 'edit-asset' | 'delete-asset' | 'settings' | null

type ConnectionMode = 'ssh' | 'serial' | 'telnet'

type AddAssetForm = {
  mode: ConnectionMode
  name: string
  host: string
  port: string
  username: string
  authType: string
  credentialSecret: string
  sshKeyId: string
  serialPort: string
  baudRate: string
  dataBits: string
  parity: string
  stopBits: string
  groupId: string
}

const emptyAddAssetForm: AddAssetForm = {
  mode: 'ssh',
  name: '',
  host: '',
  port: '22',
  username: '',
  authType: 'password',
  credentialSecret: '',
  sshKeyId: '',
  serialPort: '',
  baudRate: '9600',
  dataBits: '8',
  parity: 'none',
  stopBits: '1',
  groupId: '',
}

function buildConnectionTags(form: AddAssetForm): string[] {
  if (form.mode === 'serial') {
    return [
      'connection:serial',
      `serial-port:${form.serialPort.trim()}`,
      `baud-rate:${form.baudRate}`,
      `data-bits:${form.dataBits}`,
      `parity:${form.parity}`,
      `stop-bits:${form.stopBits}`,
    ]
  }

  return [`connection:${form.mode}`]
}

function getAssetTypeByMode(mode: ConnectionMode): 'linux' | 'network' {
  return mode === 'ssh' ? 'linux' : 'network'
}

export function App() {
  const [activeModal, setActiveModal] = useState<ActiveModal>(null)
  const [targetAsset, setTargetAsset] = useState<Asset | null>(null)
  const [addAssetForm, setAddAssetForm] = useState<AddAssetForm>(emptyAddAssetForm)
  const [addAssetError, setAddAssetError] = useState<string | null>(null)
  
  const {
    bootstrap,
    terminalOutput,
    terminalTabs,
    activeTerminalAssetId,
    selectedAsset,
    selectedModel,
    loadError,
    setSelectedModel,
    prompt,
    setPrompt,
    events,
    pendingApprovalRunId,
    setSelectedAssetId,
    addAsset,
    updateAsset,
    deleteAsset,
    replaceGroups,
    replaceModelOptions,
    replaceSSHKeys,
    runAgent,
    approveRun,
    rejectRun,
    sendTerminalInput,
    resizeTerminal,
    setActiveTerminalAssetId,
  } = useConsoleData()

  const updateAddAssetForm = (field: keyof AddAssetForm, value: string) => {
    setAddAssetForm((currentForm) => ({ ...currentForm, [field]: value }))
  }

  const closeModal = () => {
    setAddAssetForm(emptyAddAssetForm)
    setAddAssetError(null)
    setTargetAsset(null)
    setActiveModal(null)
  }

  const openEditAssetModal = (asset: Asset) => {
    setTargetAsset(asset)
    const mode = asset.tags.includes('connection:serial') ? 'serial' : asset.tags.includes('connection:telnet') ? 'telnet' : 'ssh'
    
    setAddAssetForm({
      mode,
      name: asset.name,
      host: asset.host,
      port: String(asset.port),
      username: asset.username,
      authType: asset.authType || 'password',
      credentialSecret: '',
      sshKeyId: asset.sshKeyId ? String(asset.sshKeyId) : '',
      serialPort: mode === 'serial' ? asset.host : '',
      baudRate: mode === 'serial' ? String(asset.port) : '9600',
      dataBits: asset.tags.find((t) => t.startsWith('data-bits:'))?.split(':')[1] || '8',
      parity: asset.tags.find((t) => t.startsWith('parity:'))?.split(':')[1] || 'none',
      stopBits: asset.tags.find((t) => t.startsWith('stop-bits:'))?.split(':')[1] || '1',
      groupId: asset.groupId ? String(asset.groupId) : '',
    })
    setActiveModal('edit-asset')
  }

  const openDeleteAssetModal = (asset: Asset) => {
    setTargetAsset(asset)
    setActiveModal('delete-asset')
  }

  const handleAssetSubmit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault()
    setAddAssetError(null)
    try {
      const payload = {
        name: addAssetForm.name,
        asset_type: getAssetTypeByMode(addAssetForm.mode),
        group_id: addAssetForm.groupId ? Number(addAssetForm.groupId) : null,
        host: addAssetForm.mode === 'serial' ? addAssetForm.serialPort.trim() : addAssetForm.host.trim(),
        port: addAssetForm.mode === 'serial' ? Number(addAssetForm.baudRate) : Number(addAssetForm.port),
        username: addAssetForm.mode === 'serial' ? '' : addAssetForm.username.trim(),
        auth_type: addAssetForm.mode === 'ssh' ? addAssetForm.authType : addAssetForm.mode === 'telnet' ? 'password' : '',
        ssh_key_id: addAssetForm.mode === 'ssh' && addAssetForm.authType === 'key' ? (addAssetForm.sshKeyId ? Number(addAssetForm.sshKeyId) : null) : null,
        credential_secret: addAssetForm.mode === 'serial' ? undefined : addAssetForm.credentialSecret.trim() || undefined,
        tags: buildConnectionTags(addAssetForm),
        vendor: targetAsset?.vendor || '',
        description: targetAsset?.description || '',
      }

      if (activeModal === 'edit-asset' && targetAsset) {
        await updateAsset(targetAsset.id, payload)
      } else {
        await addAsset(payload)
      }
      closeModal()
    } catch (error) {
      setAddAssetError(error instanceof Error ? error.message : '保存资产失败')
    }
  }

  if (loadError && bootstrap.assets.length === 0) {
    return <LoadingState message={loadError} />
  }

  return (
    <div className="flex flex-col h-screen w-screen bg-ops-bg text-ops-text overflow-hidden">
      <TopBar onOpenSettings={() => setActiveModal('settings')} />

      <main className="flex-1 flex overflow-hidden">
        <PanelGroup orientation="horizontal" className="h-full w-full">
          <Panel defaultSize={20} minSize={15}>
            <AssetSidebar
              assets={bootstrap.assets}
              groups={bootstrap.groups}
              selectedAssetId={selectedAsset?.id ?? 0}
              onSelectAsset={setSelectedAssetId}
              onUpdateAsset={updateAsset}
              onDeleteAsset={deleteAsset}
              onAddAsset={() => setActiveModal('add-asset')}
              onEditAsset={openEditAssetModal}
              onDeleteAssetConfirm={openDeleteAssetModal}
            />
          </Panel>

          <PanelResizeHandle className="w-1 bg-transparent group cursor-col-resize flex flex-col items-center justify-center relative">
            <div className="absolute inset-y-0 -left-1 -right-1 z-10" />
            <div className="w-px h-16 bg-ops-border/50 group-hover:bg-ops-cyan group-active:bg-ops-cyan transition-colors" />
          </PanelResizeHandle>

          <Panel defaultSize={selectedAsset ? 50 : 80} minSize={30}>
            {selectedAsset ? (
              <TerminalPanel
                asset={selectedAsset}
                tabs={terminalTabs.map((item) => item.asset)}
                activeAssetId={activeTerminalAssetId}
                output={terminalOutput}
                onInput={sendTerminalInput}
                onResize={resizeTerminal}
                onSelectTab={setActiveTerminalAssetId}
              />
            ) : (
              <section className="h-full flex items-center justify-center bg-ops-panel border-x border-ops-border/30 backdrop-blur-md">
                <p className="text-ops-muted text-sm">暂无资产，请先添加资产。</p>
              </section>
            )}
            
            {loadError ? (
              <section className="h-full flex items-center justify-center bg-ops-panel border-x border-ops-border/30 backdrop-blur-md">
                <p className="text-ops-danger text-sm">{loadError}</p>
              </section>
            ) : null}
          </Panel>

          {selectedAsset && !loadError ? (
            <>
              <PanelResizeHandle className="w-1 bg-transparent group cursor-col-resize flex flex-col items-center justify-center relative">
                <div className="absolute inset-y-0 -left-1 -right-1 z-10" />
                <div className="w-px h-16 bg-ops-border/50 group-hover:bg-ops-cyan group-active:bg-ops-cyan transition-colors" />
              </PanelResizeHandle>

              <Panel defaultSize={30} minSize={20}>
                <AssistantPanel
                  events={events}
                  pendingApprovalRunId={pendingApprovalRunId}
                  models={bootstrap.modelOptions}
                  selectedModel={selectedModel}
                  prompt={prompt}
                  selectedAsset={selectedAsset}
                  onModelChange={setSelectedModel}
                  onPromptChange={setPrompt}
                  onRun={() => {
                    void runAgent()
                  }}
                  onApprove={() => {
                    void approveRun()
                  }}
                  onReject={() => {
                    void rejectRun()
                  }}
                />
              </Panel>
            </>
          ) : null}
        </PanelGroup>
      </main>

      {(activeModal === 'add-asset' || activeModal === 'edit-asset') ? (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm" role="presentation">
          <form className="w-[500px] max-w-[90vw] max-h-[90vh] overflow-y-auto bg-ops-strong border border-ops-border/50 rounded-xl p-6 shadow-2xl flex flex-col gap-4" role="dialog" aria-modal="true" aria-labelledby="add-asset-title" onSubmit={handleAssetSubmit}>
            <h3 id="add-asset-title" className="text-lg font-medium text-ops-text pb-2 border-b border-ops-border/30">
              {activeModal === 'edit-asset' ? '编辑资产' : '添加资产'}
            </h3>
            <div className="grid grid-cols-2 gap-4">
              <label className="flex flex-col gap-1 text-sm text-ops-muted col-span-2 sm:col-span-1">
                类型
                <select className="field-control" value={addAssetForm.mode} onChange={(event) => updateAddAssetForm('mode', event.target.value as ConnectionMode)}>
                  <option value="ssh">SSH</option>
                  <option value="serial">Serial</option>
                  <option value="telnet">Telnet</option>
                </select>
              </label>
              <label className="flex flex-col gap-1 text-sm text-ops-muted col-span-2 sm:col-span-1">
                名称
                <input className="field-control" value={addAssetForm.name} onChange={(event) => updateAddAssetForm('name', event.target.value)} placeholder={addAssetForm.mode === 'serial' ? '串口设备' : addAssetForm.mode === 'telnet' ? 'telnet-switch-01' : 'backup-linux-03'} required />
              </label>
              <label className="flex flex-col gap-1 text-sm text-ops-muted col-span-2 sm:col-span-1">
                分组
                <select className="field-control" value={addAssetForm.groupId} onChange={(event) => updateAddAssetForm('groupId', event.target.value)}>
                  <option value="">未分组</option>
                  {bootstrap.groups.map((group) => (
                    <option key={group.id} value={group.id}>{group.name}</option>
                  ))}
                </select>
              </label>
              {addAssetForm.mode === 'ssh' ? (
                <>
                  <label className="flex flex-col gap-1 text-sm text-ops-muted col-span-2 sm:col-span-1">
                    地址
                    <input className="field-control" value={addAssetForm.host} onChange={(event) => updateAddAssetForm('host', event.target.value)} placeholder="10.10.3.19" required />
                  </label>
                  <label className="flex flex-col gap-1 text-sm text-ops-muted col-span-2 sm:col-span-1">
                    端口
                    <input className="field-control" type="number" min="1" max="65535" value={addAssetForm.port} onChange={(event) => updateAddAssetForm('port', event.target.value)} placeholder="22" required />
                  </label>
                  <label className="flex flex-col gap-1 text-sm text-ops-muted col-span-2 sm:col-span-1">
                    用户名
                    <input className="field-control" value={addAssetForm.username} onChange={(event) => updateAddAssetForm('username', event.target.value)} placeholder="ops" required />
                  </label>
                  <label className="flex flex-col gap-1 text-sm text-ops-muted col-span-2 sm:col-span-1">
                    认证方式
                    <select className="field-control" value={addAssetForm.authType} onChange={(event) => updateAddAssetForm('authType', event.target.value)}>
                      <option value="password">密码</option>
                      <option value="key">密钥</option>
                      <option value="password_and_key">密码 + 密钥</option>
                    </select>
                  </label>
                  {addAssetForm.authType === 'key' ? (
                    <label className="flex flex-col gap-1 text-sm text-ops-muted col-span-2 sm:col-span-1">
                      SSH 密钥
                      <select className="field-control" value={addAssetForm.sshKeyId} onChange={(event) => updateAddAssetForm('sshKeyId', event.target.value)} required>
                        <option value="">请选择密钥</option>
                        {bootstrap.sshKeys.map((sshKey) => (
                          <option key={sshKey.id} value={sshKey.id}>{sshKey.name}</option>
                        ))}
                      </select>
                    </label>
                  ) : null}
                  <label className="flex flex-col gap-1 text-sm text-ops-muted col-span-2">
                    {addAssetForm.authType === 'key' ? '私钥口令（可选）' : addAssetForm.authType === 'password_and_key' ? '密码或密钥凭据' : '密码'}
                    {addAssetForm.authType === 'key' ? (
                      <input className="field-control" type="password" value={addAssetForm.credentialSecret} onChange={(event) => updateAddAssetForm('credentialSecret', event.target.value)} placeholder="如密钥有口令可填写" />
                    ) : (
                      <input className="field-control" type="password" value={addAssetForm.credentialSecret} onChange={(event) => updateAddAssetForm('credentialSecret', event.target.value)} placeholder={addAssetForm.authType === 'password_and_key' ? '输入密码或密钥口令' : '请输入登录密码'} required={activeModal !== 'edit-asset'} />
                    )}
                  </label>
                </>
              ) : null}
              {addAssetForm.mode === 'telnet' ? (
                <>
                  <label className="flex flex-col gap-1 text-sm text-ops-muted col-span-2 sm:col-span-1">
                    地址
                    <input className="field-control" value={addAssetForm.host} onChange={(event) => updateAddAssetForm('host', event.target.value)} placeholder="10.10.3.20" required />
                  </label>
                  <label className="flex flex-col gap-1 text-sm text-ops-muted col-span-2 sm:col-span-1">
                    端口
                    <input className="field-control" type="number" min="1" max="65535" value={addAssetForm.port} onChange={(event) => updateAddAssetForm('port', event.target.value)} placeholder="23" required />
                  </label>
                  <label className="flex flex-col gap-1 text-sm text-ops-muted col-span-2 sm:col-span-1">
                    用户名
                    <input className="field-control" value={addAssetForm.username} onChange={(event) => updateAddAssetForm('username', event.target.value)} placeholder="可选" />
                  </label>
                  <label className="flex flex-col gap-1 text-sm text-ops-muted col-span-2">
                    登录密码
                    <input className="field-control" type="password" value={addAssetForm.credentialSecret} onChange={(event) => updateAddAssetForm('credentialSecret', event.target.value)} placeholder="请输入 Telnet 密码" required={activeModal !== 'edit-asset'} />
                  </label>
                </>
              ) : null}
              {addAssetForm.mode === 'serial' ? (
                <>
                  <label className="flex flex-col gap-1 text-sm text-ops-muted col-span-2 sm:col-span-1">
                    串口设备
                    <input className="field-control" value={addAssetForm.serialPort} onChange={(event) => updateAddAssetForm('serialPort', event.target.value)} placeholder="COM3 / /dev/ttyUSB0" required />
                  </label>
                  <label className="flex flex-col gap-1 text-sm text-ops-muted col-span-2 sm:col-span-1">
                    波特率
                    <input className="field-control" type="number" value={addAssetForm.baudRate} onChange={(event) => updateAddAssetForm('baudRate', event.target.value)} placeholder="9600" required />
                  </label>
                  <label className="flex flex-col gap-1 text-sm text-ops-muted col-span-2 sm:col-span-1">
                    数据位
                    <select className="field-control" value={addAssetForm.dataBits} onChange={(event) => updateAddAssetForm('dataBits', event.target.value)}>
                      <option value="5">5</option>
                      <option value="6">6</option>
                      <option value="7">7</option>
                      <option value="8">8</option>
                    </select>
                  </label>
                  <label className="flex flex-col gap-1 text-sm text-ops-muted col-span-2 sm:col-span-1">
                    校验位
                    <select className="field-control" value={addAssetForm.parity} onChange={(event) => updateAddAssetForm('parity', event.target.value)}>
                      <option value="none">None</option>
                      <option value="odd">Odd</option>
                      <option value="even">Even</option>
                    </select>
                  </label>
                  <label className="flex flex-col gap-1 text-sm text-ops-muted col-span-2 sm:col-span-1">
                    停止位
                    <select className="field-control" value={addAssetForm.stopBits} onChange={(event) => updateAddAssetForm('stopBits', event.target.value)}>
                      <option value="1">1</option>
                      <option value="1.5">1.5</option>
                      <option value="2">2</option>
                    </select>
                  </label>
                </>
              ) : null}
            </div>
            {addAssetError ? <div className="settings-error">{addAssetError}</div> : null}
            <div className="modal-actions">
              <button type="button" className="button" onClick={closeModal}>取消</button>
              <button type="submit" className="button button-primary">保存</button>
            </div>
          </form>
        </div>
      ) : null}

      {activeModal === 'delete-asset' && targetAsset ? (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm" role="presentation">
          <div className="w-[400px] max-w-[90vw] bg-ops-strong border border-ops-border/50 rounded-xl p-6 shadow-2xl flex flex-col gap-4" role="dialog" aria-modal="true">
            <h3 className="text-lg font-medium text-ops-danger">确认删除资产？</h3>
            <p className="text-sm text-ops-text">
              确定要删除 <span className="font-bold text-ops-cyan">{targetAsset.name}</span> 吗？此操作不可撤销。
            </p>
            <div className="modal-actions mt-4">
              <button type="button" className="button" onClick={closeModal}>取消</button>
              <button
                type="button"
                className="button button-danger"
                onClick={async () => {
                  try {
                    await deleteAsset(targetAsset.id)
                    closeModal()
                  } catch (error) {
                    setAddAssetError(error instanceof Error ? error.message : '删除失败')
                  }
                }}
              >
                删除
              </button>
            </div>
            {addAssetError ? <p className="settings-error mt-2">{addAssetError}</p> : null}
          </div>
        </div>
      ) : null}

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
