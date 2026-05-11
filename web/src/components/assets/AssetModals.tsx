import { type FormEvent, forwardRef, useImperativeHandle, useState, useEffect } from 'react'
import type { Asset, AssetGroup, SSHKey } from '../../types/ops'

type ActiveModal = 'add-asset' | 'edit-asset' | 'delete-asset' | null

type ConnectionMode = 'ssh' | 'serial'
type AssetKind = 'linux' | 'network' | 'cisco' | 'huawei' | 'juniper' | 'h3c' | 'serial'

type AddAssetForm = {
  mode: ConnectionMode
  assetKind: AssetKind
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
  assetKind: 'linux',
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
      `data-bits:${form.dataBits}`,
      `parity:${form.parity}`,
      `stop-bits:${form.stopBits}`,
    ]
  }

  return ['connection:ssh']
}

export interface AssetModalsRef {
  openAddModal: () => void
  openEditModal: (asset: Asset) => void
  openDeleteModal: (asset: Asset) => void
}

interface AssetModalsProps {
  groups: AssetGroup[]
  sshKeys: SSHKey[]
  onAddAsset: (payload: any) => Promise<void>
  onUpdateAsset: (id: number, payload: any) => Promise<void>
  onDeleteAsset: (id: number) => Promise<void>
}

export const AssetModals = forwardRef<AssetModalsRef, AssetModalsProps>(
  ({ groups, sshKeys, onAddAsset, onUpdateAsset, onDeleteAsset }, ref) => {
    const [activeModal, setActiveModal] = useState<ActiveModal>(null)
    const [targetAsset, setTargetAsset] = useState<Asset | null>(null)
    const [addAssetForm, setAddAssetForm] = useState<AddAssetForm>(emptyAddAssetForm)
    const [addAssetError, setAddAssetError] = useState<string | null>(null)
    const [systemSerialPorts, setSystemSerialPorts] = useState<{device: string, description: string}[]>([])

    useEffect(() => {
      if ((activeModal === 'add-asset' || activeModal === 'edit-asset') && addAssetForm.mode === 'serial') {
        fetch('/api/system/serial-ports')
          .then(res => res.json())
          .then(data => setSystemSerialPorts(data))
          .catch(err => console.error('Failed to fetch serial ports:', err))
      }
    }, [activeModal, addAssetForm.mode])

    const updateAddAssetForm = (field: keyof AddAssetForm, value: string) => {
      setAddAssetForm((currentForm) => ({ ...currentForm, [field]: value }))
    }

    const closeModal = () => {
      setAddAssetForm(emptyAddAssetForm)
      setAddAssetError(null)
      setTargetAsset(null)
      setActiveModal(null)
    }

    const openAddModal = () => {
      setActiveModal('add-asset')
    }

    const openEditModal = (asset: Asset) => {
      setTargetAsset(asset)
      const mode: ConnectionMode = asset.assetType === 'serial' ? 'serial' : 'ssh'
      const assetKind: AssetKind = ['linux', 'network', 'cisco', 'huawei', 'juniper', 'h3c'].includes(asset.assetType)
        ? (asset.assetType as AssetKind)
        : 'linux'
      const tagValue = (prefix: string, fallback: string) => asset.tags.find((tag) => tag.startsWith(`${prefix}:`))?.split(':')[1] ?? fallback

      setAddAssetForm({
        mode,
        assetKind: mode === 'serial' ? 'serial' : assetKind,
        name: asset.name,
        host: asset.host,
        port: String(asset.port),
        username: asset.username,
        authType: asset.authType || 'password',
        credentialSecret: '',
        sshKeyId: asset.sshKeyId ? String(asset.sshKeyId) : '',
        serialPort: mode === 'serial' ? asset.host : '',
        baudRate: mode === 'serial' ? String(asset.port) : '9600',
        dataBits: tagValue('data-bits', '8'),
        parity: tagValue('parity', 'none'),
        stopBits: tagValue('stop-bits', '1'),
        groupId: asset.groupId ? String(asset.groupId) : '',
      })
      setActiveModal('edit-asset')
    }

    const openDeleteModal = (asset: Asset) => {
      setTargetAsset(asset)
      setActiveModal('delete-asset')
    }

    useImperativeHandle(ref, () => ({
      openAddModal,
      openEditModal,
      openDeleteModal,
    }))

    const handleAssetSubmit = async (event: FormEvent<HTMLFormElement>) => {
      event.preventDefault()
      setAddAssetError(null)
      try {
        const payload = addAssetForm.mode === 'serial'
          ? {
            name: addAssetForm.name,
            asset_type: 'serial' as const,
            group_id: addAssetForm.groupId ? Number(addAssetForm.groupId) : null,
            host: addAssetForm.serialPort.trim(),
            port: Number(addAssetForm.baudRate),
            username: '',
            auth_type: '',
            tags: buildConnectionTags(addAssetForm),
            vendor: targetAsset?.vendor || '',
            description: targetAsset?.description || '',
          }
          : {
            name: addAssetForm.name,
            asset_type: addAssetForm.assetKind,
            group_id: addAssetForm.groupId ? Number(addAssetForm.groupId) : null,
            host: addAssetForm.host.trim(),
            port: Number(addAssetForm.port),
            username: addAssetForm.username.trim(),
            auth_type: addAssetForm.authType,
            ssh_key_id: ['key', 'password_and_key'].includes(addAssetForm.authType) ? (addAssetForm.sshKeyId ? Number(addAssetForm.sshKeyId) : null) : null,
            credential_secret: addAssetForm.credentialSecret.trim() || undefined,
            tags: buildConnectionTags(addAssetForm),
            vendor: targetAsset?.vendor || '',
            description: targetAsset?.description || '',
          }

        if (activeModal === 'edit-asset' && targetAsset) {
          await onUpdateAsset(targetAsset.id, payload)
        } else {
          await onAddAsset(payload)
        }
        closeModal()
      } catch (error) {
        setAddAssetError(error instanceof Error ? error.message : 'Failed to save infrastructure')
      }
    }

    return (
      <>
        {(activeModal === 'add-asset' || activeModal === 'edit-asset') ? (
          <div className="fixed inset-0 z-50 flex items-center justify-center bg-ops-bg/60 backdrop-blur-md animate-in fade-in duration-300" role="presentation">
            <form className="w-[520px] max-w-[90vw] max-h-[90vh] overflow-y-auto bg-ops-panel/90 border border-ops-border/40 rounded-2xl p-8 shadow-2xl flex flex-col gap-6 backdrop-blur-xl animate-in zoom-in-95 duration-300" role="dialog" aria-modal="true" aria-labelledby="add-asset-title" onSubmit={handleAssetSubmit}>
              <div className="flex items-center justify-between pb-4 border-b border-ops-border/20">
                <h3 id="add-asset-title" className="text-[16px] font-bold  tracking-[0.15em] text-ops-cyan">
                  {activeModal === 'edit-asset' ? 'Update Infrastructure' : 'New Infrastructure'}
                </h3>
                <button type="button" onClick={closeModal} className="text-ops-muted hover:text-ops-text transition-colors">
                  <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round"><path d="M18 6L6 18M6 6l12 12" /></svg>
                </button>
              </div>
              <div className="grid grid-cols-2 gap-4">
                <label className="flex flex-col gap-2 text-[11px] font-bold  tracking-widest text-ops-muted/70 col-span-2 sm:col-span-1">
                  Connection Mode
                  <select className="field-control" value={addAssetForm.mode} onChange={(event) => updateAddAssetForm('mode', event.target.value as ConnectionMode)}>
                    <option value="ssh">SSH Protocol</option>
                    <option value="serial">Serial Connection</option>
                  </select>
                </label>
                {addAssetForm.mode === 'ssh' ? (
                  <label className="flex flex-col gap-2 text-[11px] font-bold  tracking-widest text-ops-muted/70 col-span-2 sm:col-span-1">
                    Environment
                    <select className="field-control" value={addAssetForm.assetKind} onChange={(event) => updateAddAssetForm('assetKind', event.target.value as AssetKind)}>
                      <option value="linux">Linux Server</option>
                      <option value="cisco">Cisco IOS</option>
                      <option value="huawei">Huawei VRP</option>
                      <option value="juniper">Juniper JunOS</option>
                      <option value="h3c">H3C Comware</option>
                      <option value="network">Generic Network</option>
                    </select>
                  </label>
                ) : (
                  <div className="col-span-2 sm:col-span-1" />
                )}
                <label className="flex flex-col gap-2 text-[11px] font-bold  tracking-widest text-ops-muted/70 col-span-2 sm:col-span-1">
                  Display Name
                  <input className="field-control" value={addAssetForm.name} onChange={(event) => updateAddAssetForm('name', event.target.value)} placeholder={addAssetForm.mode === 'serial' ? 'serial-dev-01' : 'prod-server-01'} required />
                </label>
                <label className="flex flex-col gap-2 text-[11px] font-bold  tracking-widest text-ops-muted/70 col-span-2 sm:col-span-1">
                  Resource Group
                  <select className="field-control" value={addAssetForm.groupId} onChange={(event) => updateAddAssetForm('groupId', event.target.value)}>
                    <option value="">Default Group</option>
                    {groups.map((group) => (
                      <option key={group.id} value={group.id}>{group.name}</option>
                    ))}
                  </select>
                </label>
                {addAssetForm.mode === 'ssh' ? (
                  <>
                    <label className="flex flex-col gap-2 text-[11px] font-bold  tracking-widest text-ops-muted/70 col-span-2 sm:col-span-1">
                      Endpoint Host
                      <input className="field-control font-mono" value={addAssetForm.host} onChange={(event) => updateAddAssetForm('host', event.target.value)} placeholder="10.0.0.1" required />
                    </label>
                    <label className="flex flex-col gap-2 text-[11px] font-bold  tracking-widest text-ops-muted/70 col-span-2 sm:col-span-1">
                      Port
                      <input className="field-control font-mono" type="number" min="1" max="65535" value={addAssetForm.port} onChange={(event) => updateAddAssetForm('port', event.target.value)} placeholder="22" required />
                    </label>
                    <label className="flex flex-col gap-2 text-[11px] font-bold  tracking-widest text-ops-muted/70 col-span-2 sm:col-span-1">
                      System User
                      <input className="field-control font-mono" value={addAssetForm.username} onChange={(event) => updateAddAssetForm('username', event.target.value)} placeholder="root" required />
                    </label>
                    <label className="flex flex-col gap-2 text-[11px] font-bold  tracking-widest text-ops-muted/70 col-span-2 sm:col-span-1">
                      Auth Strategy
                      <select className="field-control" value={addAssetForm.authType} onChange={(event) => updateAddAssetForm('authType', event.target.value)}>
                        <option value="password">Password</option>
                        <option value="key">SSH Keypair</option>
                        <option value="password_and_key">2-Factor (Key + Pass)</option>
                      </select>
                    </label>
                    {['key', 'password_and_key'].includes(addAssetForm.authType) ? (
                      <label className="flex flex-col gap-2 text-[11px] font-bold  tracking-widest text-ops-muted/70 col-span-2 sm:col-span-1">
                        Select SSH Key
                        <select className="field-control" value={addAssetForm.sshKeyId} onChange={(event) => updateAddAssetForm('sshKeyId', event.target.value)} required>
                          <option value="">Select identity...</option>
                          {sshKeys.map((sshKey) => (
                            <option key={sshKey.id} value={sshKey.id}>{sshKey.name}</option>
                          ))}
                        </select>
                      </label>
                    ) : null}
                    <label className="flex flex-col gap-2 text-[11px] font-bold  tracking-widest text-ops-muted/70 col-span-2">
                      Credential / Passphrase
                      <input className="field-control font-mono" type="password" value={addAssetForm.credentialSecret} onChange={(event) => updateAddAssetForm('credentialSecret', event.target.value)} placeholder="••••••••••••" required={activeModal !== 'edit-asset'} />
                    </label>
                  </>
                ) : null}
                {addAssetForm.mode === 'serial' ? (
                  <>
                    <label className="flex flex-col gap-1 text-sm text-ops-muted col-span-2 sm:col-span-1">
                      Serial Port
                      <input className="field-control" list="serial-ports-list" value={addAssetForm.serialPort} onChange={(event) => updateAddAssetForm('serialPort', event.target.value)} placeholder="COM3 / /dev/ttyUSB0" required />
                      <datalist id="serial-ports-list">
                        {systemSerialPorts.map((port) => (
                          <option key={port.device} value={port.device}>
                            {port.description && port.description !== 'n/a' ? `${port.device} (${port.description})` : port.device}
                          </option>
                        ))}
                      </datalist>
                    </label>
                    <label className="flex flex-col gap-1 text-sm text-ops-muted col-span-2 sm:col-span-1">
                      Baud Rate
                      <input className="field-control" type="number" value={addAssetForm.baudRate} onChange={(event) => updateAddAssetForm('baudRate', event.target.value)} placeholder="9600" required />
                    </label>
                    <label className="flex flex-col gap-1 text-sm text-ops-muted col-span-2 sm:col-span-1">
                      Data Bits
                      <select className="field-control" value={addAssetForm.dataBits} onChange={(event) => updateAddAssetForm('dataBits', event.target.value)}>
                        <option value="5">5</option>
                        <option value="6">6</option>
                        <option value="7">7</option>
                        <option value="8">8</option>
                      </select>
                    </label>
                    <label className="flex flex-col gap-1 text-sm text-ops-muted col-span-2 sm:col-span-1">
                      Parity
                      <select className="field-control" value={addAssetForm.parity} onChange={(event) => updateAddAssetForm('parity', event.target.value)}>
                        <option value="none">None</option>
                        <option value="odd">Odd</option>
                        <option value="even">Even</option>
                      </select>
                    </label>
                    <label className="flex flex-col gap-1 text-sm text-ops-muted col-span-2 sm:col-span-1">
                      Stop Bits
                      <select className="field-control" value={addAssetForm.stopBits} onChange={(event) => updateAddAssetForm('stopBits', event.target.value)}>
                        <option value="1">1</option>
                        <option value="1.5">1.5</option>
                        <option value="2">2</option>
                      </select>
                    </label>
                  </>
                ) : null}
              </div>
              {addAssetError ? <div className="settings-error text-center py-2 px-4 bg-ops-danger/10 border border-ops-danger/20 rounded-lg">{addAssetError}</div> : null}
              <div className="flex items-center justify-end gap-3 pt-4 border-t border-ops-border/20">
                <button type="button" className="button px-6" onClick={closeModal}>Cancel</button>
                <button type="submit" className="button button-primary px-8 shadow-glow">Authorize & Save</button>
              </div>
            </form>
          </div>
        ) : null}

        {activeModal === 'delete-asset' && targetAsset ? (
          <div className="fixed inset-0 z-50 flex items-center justify-center bg-ops-bg/60 backdrop-blur-md animate-in fade-in duration-300" role="presentation">
            <div className="w-[420px] max-w-[90vw] bg-ops-panel/90 border border-ops-border/40 rounded-2xl p-8 shadow-2xl flex flex-col gap-6 backdrop-blur-xl animate-in zoom-in-95 duration-300" role="dialog" aria-modal="true">
              <div className="flex items-center gap-4 text-ops-danger">
                <div className="flex h-12 w-12 shrink-0 items-center justify-center rounded-full bg-ops-danger/10">
                  <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5"><path d="M10.29 3.86L1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z" /><line x1="12" y1="9" x2="12" y2="13" /><line x1="12" y1="17" x2="12.01" y2="17" /></svg>
                </div>
                <h3 className="text-lg font-bold  tracking-wider">Confirm Deletion</h3>
              </div>
              <p className="text-[13px] leading-relaxed text-ops-text/80">
                Are you sure you want to decommission <span className="font-bold text-ops-cyan">{targetAsset.name}</span>? This action is permanent and cannot be recovered.
              </p>
              <div className="flex items-center justify-end gap-3 pt-2">
                <button type="button" className="button px-6" onClick={closeModal}>Cancel</button>
                <button
                  type="button"
                  className="button button-danger px-8"
                  onClick={async () => {
                    try {
                      await onDeleteAsset(targetAsset.id)
                      closeModal()
                    } catch (error) {
                      setAddAssetError(error instanceof Error ? error.message : 'Deletion Failed')
                    }
                  }}
                >
                  Decommission
                </button>
              </div>
              {addAssetError ? <p className="settings-error mt-2">{addAssetError}</p> : null}
            </div>
          </div>
        ) : null}
      </>
    )
  }
)

AssetModals.displayName = 'AssetModals'
