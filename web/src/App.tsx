import { type FormEvent, useState } from 'react'
import { AssetSidebar } from './components/assets/AssetSidebar'
import { AssistantPanel } from './components/assistant/AssistantPanel'
import { LoadingState } from './components/layout/LoadingState'
import { TopBar } from './components/layout/TopBar'
import { SettingsDialog } from './components/settings/SettingsDialog'
import { TerminalPanel } from './components/terminal/TerminalPanel'
import { useConsoleData } from './hooks/useConsoleData'

type ActiveModal = 'add-asset' | 'settings' | null

type ConnectionMode = 'ssh' | 'serial' | 'telnet'

type AddAssetForm = {
  mode: ConnectionMode
  name: string
  host: string
  port: string
  username: string
  authType: string
  credentialSecret: string
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
    setSelectedAssetId,
    addAsset,
    updateAsset,
    deleteAsset,
    replaceGroups,
    replaceModelOptions,
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

  const closeAddAssetModal = () => {
    setAddAssetForm(emptyAddAssetForm)
    setAddAssetError(null)
    setActiveModal(null)
  }

  const handleAddAssetSubmit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault()
    setAddAssetError(null)
    try {
      await addAsset({
        name: addAssetForm.name,
        asset_type: getAssetTypeByMode(addAssetForm.mode),
        group_id: addAssetForm.groupId ? Number(addAssetForm.groupId) : null,
        host: addAssetForm.mode === 'serial' ? addAssetForm.serialPort.trim() : addAssetForm.host.trim(),
        port: addAssetForm.mode === 'serial' ? Number(addAssetForm.baudRate) : Number(addAssetForm.port),
        username: addAssetForm.mode === 'serial' ? '' : addAssetForm.username.trim(),
        auth_type: addAssetForm.mode === 'ssh' ? addAssetForm.authType : addAssetForm.mode === 'telnet' ? 'password' : '',
        credential_secret: addAssetForm.mode === 'serial' ? undefined : addAssetForm.credentialSecret.trim() || undefined,
        tags: buildConnectionTags(addAssetForm),
        vendor: '',
        description: '',
      })
      closeAddAssetModal()
    } catch (error) {
      setAddAssetError(error instanceof Error ? error.message : '添加资产失败')
    }
  }

  if (loadError && bootstrap.assets.length === 0) {
    return <LoadingState message={loadError} />
  }

  return (
    <div className="app-shell">
      <TopBar onOpenSettings={() => setActiveModal('settings')} />

      <main className="layout-grid">
        <AssetSidebar
          assets={bootstrap.assets}
          groups={bootstrap.groups}
          selectedAssetId={selectedAsset?.id ?? 0}
          onSelectAsset={setSelectedAssetId}
          onUpdateAsset={updateAsset}
          onDeleteAsset={deleteAsset}
          onAddAsset={() => setActiveModal('add-asset')}
        />

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
          <section className="panel-card panel-fill">
            <p className="status-line">暂无资产，请先添加资产。</p>
          </section>
        )}

        {loadError ? (
          <section className="panel-card panel-fill">
            <p className="status-line">{loadError}</p>
          </section>
        ) : null}

        {selectedAsset ? (
          <AssistantPanel
            events={events}
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
        ) : null}
      </main>

      {activeModal === 'add-asset' ? (
        <div className="modal-backdrop" role="presentation">
          <form className="asset-modal" role="dialog" aria-modal="true" aria-labelledby="add-asset-title" onSubmit={handleAddAssetSubmit}>
            <h3 id="add-asset-title" className="modal-title">添加资产</h3>
            <div className="asset-form-grid">
              <label>
                类型
                <select className="field-control" value={addAssetForm.mode} onChange={(event) => updateAddAssetForm('mode', event.target.value)}>
                  <option value="ssh">SSH</option>
                  <option value="serial">Serial</option>
                  <option value="telnet">Telnet</option>
                </select>
              </label>
              <label>
                名称
                <input className="field-control" value={addAssetForm.name} onChange={(event) => updateAddAssetForm('name', event.target.value)} placeholder={addAssetForm.mode === 'serial' ? '串口设备' : addAssetForm.mode === 'telnet' ? 'telnet-switch-01' : 'backup-linux-03'} required />
              </label>
              <label>
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
                  <label>
                    地址
                    <input className="field-control" value={addAssetForm.host} onChange={(event) => updateAddAssetForm('host', event.target.value)} placeholder="10.10.3.19" required />
                  </label>
                  <label>
                    端口
                    <input className="field-control" type="number" min="1" max="65535" value={addAssetForm.port} onChange={(event) => updateAddAssetForm('port', event.target.value)} placeholder="22" required />
                  </label>
                  <label>
                    用户名
                    <input className="field-control" value={addAssetForm.username} onChange={(event) => updateAddAssetForm('username', event.target.value)} placeholder="ops" required />
                  </label>
                  <label>
                    认证方式
                    <select className="field-control" value={addAssetForm.authType} onChange={(event) => updateAddAssetForm('authType', event.target.value)}>
                      <option value="password">密码</option>
                      <option value="key">密钥</option>
                      <option value="password_and_key">密码 + 密钥</option>
                    </select>
                  </label>
                  <label>
                    {addAssetForm.authType === 'key' ? '密钥内容' : addAssetForm.authType === 'password_and_key' ? '密码或密钥凭据' : '密码'}
                    {addAssetForm.authType === 'key' ? (
                      <textarea className="field-control" value={addAssetForm.credentialSecret} onChange={(event) => updateAddAssetForm('credentialSecret', event.target.value)} placeholder="粘贴私钥内容" rows={5} required />
                    ) : (
                      <input className="field-control" type="password" value={addAssetForm.credentialSecret} onChange={(event) => updateAddAssetForm('credentialSecret', event.target.value)} placeholder={addAssetForm.authType === 'password_and_key' ? '输入密码或密钥口令' : '请输入登录密码'} required />
                    )}
                  </label>
                </>
              ) : null}
              {addAssetForm.mode === 'telnet' ? (
                <>
                  <label>
                    地址
                    <input className="field-control" value={addAssetForm.host} onChange={(event) => updateAddAssetForm('host', event.target.value)} placeholder="10.10.3.20" required />
                  </label>
                  <label>
                    端口
                    <input className="field-control" type="number" min="1" max="65535" value={addAssetForm.port} onChange={(event) => updateAddAssetForm('port', event.target.value)} placeholder="23" required />
                  </label>
                  <label>
                    用户名
                    <input className="field-control" value={addAssetForm.username} onChange={(event) => updateAddAssetForm('username', event.target.value)} placeholder="可选" />
                  </label>
                  <label>
                    登录密码
                    <input className="field-control" type="password" value={addAssetForm.credentialSecret} onChange={(event) => updateAddAssetForm('credentialSecret', event.target.value)} placeholder="请输入 Telnet 密码" required />
                  </label>
                </>
              ) : null}
              {addAssetForm.mode === 'serial' ? (
                <>
                  <label>
                    串口设备
                    <input className="field-control" value={addAssetForm.serialPort} onChange={(event) => updateAddAssetForm('serialPort', event.target.value)} placeholder="COM3 / /dev/ttyUSB0" required />
                  </label>
                  <label>
                    波特率
                    <input className="field-control" type="number" value={addAssetForm.baudRate} onChange={(event) => updateAddAssetForm('baudRate', event.target.value)} placeholder="9600" required />
                  </label>
                  <label>
                    数据位
                    <select className="field-control" value={addAssetForm.dataBits} onChange={(event) => updateAddAssetForm('dataBits', event.target.value)}>
                      <option value="5">5</option>
                      <option value="6">6</option>
                      <option value="7">7</option>
                      <option value="8">8</option>
                    </select>
                  </label>
                  <label>
                    校验位
                    <select className="field-control" value={addAssetForm.parity} onChange={(event) => updateAddAssetForm('parity', event.target.value)}>
                      <option value="none">None</option>
                      <option value="odd">Odd</option>
                      <option value="even">Even</option>
                    </select>
                  </label>
                  <label>
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
              <button type="button" className="button" onClick={closeAddAssetModal}>取消</button>
              <button type="submit" className="button button-primary">保存</button>
            </div>
          </form>
        </div>
      ) : null}

      {activeModal === 'settings' ? (
        <SettingsDialog
          initialGroups={bootstrap.groups}
          selectedModel={selectedModel}
          onSelectedModelChange={setSelectedModel}
          onGroupsChange={replaceGroups}
          onModelOptionsChange={replaceModelOptions}
          onClose={() => setActiveModal(null)}
        />
      ) : null}
    </div>
  )
}
