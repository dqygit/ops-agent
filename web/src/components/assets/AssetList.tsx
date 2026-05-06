import { useState } from 'react'
import type { AssetPayload } from '../../api'
import { ListItemCard } from '../layout/ListItemCard'
import type { Asset, AssetGroup } from '../../types/ops'

type AssetListProps = {
  assets: Asset[]
  groups: AssetGroup[]
  selectedAssetId: number
  onSelectAsset: (assetId: number) => void
  onUpdateAsset: (assetId: number, payload: AssetPayload) => Promise<Asset>
  onDeleteAsset: (assetId: number) => Promise<void>
}

type EditAssetForm = {
  name: string
  mode: 'ssh' | 'serial' | 'telnet'
  host: string
  port: string
  username: string
  authType: string
  credentialSecret: string
  groupId: string
  serialPort: string
  baudRate: string
  dataBits: string
  parity: string
  stopBits: string
}

type AssetListGroup = {
  id: number | null
  label: string
}

function inferConnectionMode(asset: Asset): 'ssh' | 'serial' | 'telnet' {
  if (asset.tags.includes('connection:serial')) {
    return 'serial'
  }
  if (asset.tags.includes('connection:telnet')) {
    return 'telnet'
  }
  return 'ssh'
}

function findTagValue(tags: string[], prefix: string, fallback: string): string {
  return tags.find((tag) => tag.startsWith(prefix))?.slice(prefix.length) ?? fallback
}

function getAssetMeta(asset: Asset): string {
  return asset.assetType === 'local_terminal' ? '本地终端' : `${asset.host}:${asset.port}`
}

function toEditAssetForm(asset: Asset): EditAssetForm {
  const mode = inferConnectionMode(asset)
  return {
    name: asset.name,
    mode,
    host: asset.host,
    port: String(asset.port),
    username: asset.username,
    authType: asset.authType || 'password',
    credentialSecret: '',
    groupId: asset.groupId === null ? '' : String(asset.groupId),
    serialPort: mode === 'serial' ? asset.host : '',
    baudRate: mode === 'serial' ? String(asset.port) : '9600',
    dataBits: findTagValue(asset.tags, 'data-bits:', '8'),
    parity: findTagValue(asset.tags, 'parity:', 'none'),
    stopBits: findTagValue(asset.tags, 'stop-bits:', '1'),
  }
}

function buildEditTags(form: EditAssetForm): string[] {
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

export function AssetList({ assets, groups, selectedAssetId, onSelectAsset, onUpdateAsset, onDeleteAsset }: AssetListProps) {
  const [menuAssetId, setMenuAssetId] = useState<number | null>(null)
  const [editingAsset, setEditingAsset] = useState<Asset | null>(null)
  const [editAssetForm, setEditAssetForm] = useState<EditAssetForm | null>(null)
  const [editAssetSaving, setEditAssetSaving] = useState(false)
  const [editAssetError, setEditAssetError] = useState<string | null>(null)
  const [deletingAsset, setDeletingAsset] = useState<Asset | null>(null)
  const [deleteAssetSaving, setDeleteAssetSaving] = useState(false)
  const [deleteAssetError, setDeleteAssetError] = useState<string | null>(null)
  const visibleAssets = assets.filter((asset) => asset.assetType !== 'local_terminal')
  const assetGroups: AssetListGroup[] = [...groups.map((group) => ({ id: group.id, label: group.name })), { id: null, label: '未分组' }]
  const groupedAssets = visibleAssets.reduce<Record<string, Asset[]>>(
    (grouped, asset) => {
      const key = String(asset.groupId)
      grouped[key] = [...(grouped[key] ?? []), asset]
      return grouped
    },
    {},
  )

  return (
    <>
      <div className="flex flex-col h-full bg-ops-panel" aria-label="Host connections" onMouseLeave={() => setMenuAssetId(null)}>
        {visibleAssets.length === 0 ? <p className="text-center py-10 text-ops-muted text-sm">暂无远程资产</p> : null}
        {assetGroups.map((group) => {
          const groupKey = String(group.id)
          const groupAssets = groupedAssets[groupKey] ?? []
          if (groupAssets.length === 0) {
            return null
          }

          return (
            <section key={groupKey} className="mb-4" aria-label={group.label}>
              <h3 className="px-4 py-1.5 text-[11px] font-semibold text-ops-muted uppercase tracking-wider bg-ops-deep/50">{group.label}</h3>
              <ul className="flex flex-col list-none m-0 p-0">
                {groupAssets.map((asset) => {
                  const selected = asset.id === selectedAssetId
                  const menuOpen = asset.id === menuAssetId
                  const panelOpen = editingAsset?.id === asset.id || deletingAsset?.id === asset.id

                  return (
                    <li key={asset.id} className="relative border-b border-ops-border/10 last:border-b-0">
                      <div className={`relative flex items-center group ${menuOpen || panelOpen ? 'bg-ops-border/10' : ''}`}>
                        <ListItemCard
                          title={asset.name}
                          meta={getAssetMeta(asset)}
                          active={selected}
                          onClick={() => onSelectAsset(asset.id)}
                          onContextMenu={(event) => {
                            event.preventDefault()
                            setEditingAsset(null)
                            setDeletingAsset(null)
                            setMenuAssetId(asset.id)
                          }}
                        />

                        <button
                          type="button"
                          className="absolute right-2 opacity-0 group-hover:opacity-100 focus:opacity-100 p-1.5 hover:bg-ops-border/20 text-ops-muted hover:text-ops-text rounded transition-all z-10"
                          aria-label={`${asset.name} 操作`}
                          onClick={(event) => {
                            event.stopPropagation()
                            setEditingAsset(null)
                            setDeletingAsset(null)
                            setMenuAssetId((current) => (current === asset.id ? null : asset.id))
                          }}
                        >
                          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><circle cx="12" cy="12" r="1"></circle><circle cx="12" cy="5" r="1"></circle><circle cx="12" cy="19" r="1"></circle></svg>
                        </button>
                      </div>

                      {menuOpen ? (
                        <div className="absolute right-2 top-10 w-32 py-1 bg-ops-strong border border-ops-border/30 rounded shadow-xl z-20" role="menu" aria-label={`${asset.name} actions`}>
                          <button
                            type="button"
                            className="w-full text-left px-3 py-1.5 text-sm text-ops-text hover:bg-ops-border/20 transition-colors"
                            role="menuitem"
                            onClick={() => {
                              setEditingAsset(asset)
                              setEditAssetForm(toEditAssetForm(asset))
                              setEditAssetError(null)
                              setDeletingAsset(null)
                              setMenuAssetId(null)
                            }}
                          >
                            编辑信息
                          </button>
                          <button
                            type="button"
                            className="w-full text-left px-3 py-1.5 text-sm text-red-400 hover:bg-red-500/10 transition-colors"
                            role="menuitem"
                            onClick={() => {
                              setDeletingAsset(asset)
                              setEditingAsset(null)
                              setEditAssetForm(null)
                              setEditAssetError(null)
                              setDeleteAssetError(null)
                              setMenuAssetId(null)
                            }}
                          >
                            删除资产
                          </button>
                        </div>
                      ) : null}

                      {editingAsset?.id === asset.id ? (
                        <section className="bg-ops-deep/80 border-t border-ops-border/20 p-4" role="dialog" aria-labelledby={`edit-asset-title-${asset.id}`}>
                          <div className="flex items-center justify-between mb-3">
                            <h3 id={`edit-asset-title-${asset.id}`} className="text-sm font-medium text-ops-text">编辑主机连接</h3>
                            <button type="button" className="text-ops-muted hover:text-ops-text p-1" onClick={() => {
                              setEditingAsset(null)
                              setEditAssetForm(null)
                              setEditAssetError(null)
                            }}>
                              <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><line x1="18" y1="6" x2="6" y2="18"></line><line x1="6" y1="6" x2="18" y2="18"></line></svg>
                            </button>
                          </div>
                          <div className="asset-form-grid asset-inline-grid">
                            <label>
                              名称
                              <input className="field-control" value={editAssetForm?.name ?? ''} onChange={(event) => setEditAssetForm((current) => (current ? { ...current, name: event.target.value } : current))} />
                            </label>
                            <label>
                              类型
                              <select className="field-control" value={editAssetForm?.mode ?? 'ssh'} onChange={(event) => setEditAssetForm((current) => (current ? { ...current, mode: event.target.value as EditAssetForm['mode'] } : current))}>
                                <option value="ssh">SSH</option>
                                <option value="serial">Serial</option>
                                <option value="telnet">Telnet</option>
                              </select>
                            </label>
                            <label>
                              分组
                              <select className="field-control" value={editAssetForm?.groupId ?? ''} onChange={(event) => setEditAssetForm((current) => (current ? { ...current, groupId: event.target.value } : current))}>
                                <option value="">未分组</option>
                                {groups.map((group) => (
                                  <option key={group.id} value={group.id}>{group.name}</option>
                                ))}
                              </select>
                            </label>

                            {editAssetForm?.mode === 'ssh' ? (
                              <>
                                <label>
                                  地址
                                  <input className="field-control" value={editAssetForm?.host ?? ''} onChange={(event) => setEditAssetForm((current) => (current ? { ...current, host: event.target.value } : current))} />
                                </label>
                                <label>
                                  端口
                                  <input className="field-control" type="number" min="1" max="65535" value={editAssetForm?.port ?? ''} onChange={(event) => setEditAssetForm((current) => (current ? { ...current, port: event.target.value } : current))} />
                                </label>
                                <label>
                                  用户名
                                  <input className="field-control" value={editAssetForm?.username ?? ''} onChange={(event) => setEditAssetForm((current) => (current ? { ...current, username: event.target.value } : current))} />
                                </label>
                                <label>
                                  认证方式
                                  <select className="field-control" value={editAssetForm?.authType ?? 'password'} onChange={(event) => setEditAssetForm((current) => (current ? { ...current, authType: event.target.value } : current))}>
                                    <option value="password">密码</option>
                                    <option value="key">密钥</option>
                                    <option value="password_and_key">密码 + 密钥</option>
                                  </select>
                                </label>
                                <label>
                                  {editAssetForm?.authType === 'key' ? '更新密钥内容' : editAssetForm?.authType === 'password_and_key' ? '更新密码或密钥凭据' : '更新密码'}
                                  {editAssetForm?.authType === 'key' ? (
                                    <textarea className="field-control" value={editAssetForm?.credentialSecret ?? ''} onChange={(event) => setEditAssetForm((current) => (current ? { ...current, credentialSecret: event.target.value } : current))} placeholder="留空则保持不变" rows={5} />
                                  ) : (
                                    <input className="field-control" type="password" value={editAssetForm?.credentialSecret ?? ''} onChange={(event) => setEditAssetForm((current) => (current ? { ...current, credentialSecret: event.target.value } : current))} placeholder="留空则保持不变" />
                                  )}
                                </label>
                              </>
                            ) : null}

                            {editAssetForm?.mode === 'telnet' ? (
                              <>
                                <label>
                                  地址
                                  <input className="field-control" value={editAssetForm?.host ?? ''} onChange={(event) => setEditAssetForm((current) => (current ? { ...current, host: event.target.value } : current))} />
                                </label>
                                <label>
                                  端口
                                  <input className="field-control" type="number" min="1" max="65535" value={editAssetForm?.port ?? ''} onChange={(event) => setEditAssetForm((current) => (current ? { ...current, port: event.target.value } : current))} />
                                </label>
                                <label>
                                  用户名
                                  <input className="field-control" value={editAssetForm?.username ?? ''} onChange={(event) => setEditAssetForm((current) => (current ? { ...current, username: event.target.value } : current))} />
                                </label>
                                <label>
                                  更新密码
                                  <input className="field-control" type="password" value={editAssetForm?.credentialSecret ?? ''} onChange={(event) => setEditAssetForm((current) => (current ? { ...current, credentialSecret: event.target.value } : current))} placeholder="留空则保持不变" />
                                </label>
                              </>
                            ) : null}

                            {editAssetForm?.mode === 'serial' ? (
                              <>
                                <label>
                                  串口设备
                                  <input className="field-control" value={editAssetForm?.serialPort ?? ''} onChange={(event) => setEditAssetForm((current) => (current ? { ...current, serialPort: event.target.value } : current))} />
                                </label>
                                <label>
                                  波特率
                                  <input className="field-control" type="number" value={editAssetForm?.baudRate ?? ''} onChange={(event) => setEditAssetForm((current) => (current ? { ...current, baudRate: event.target.value } : current))} />
                                </label>
                                <label>
                                  数据位
                                  <select className="field-control" value={editAssetForm?.dataBits ?? '8'} onChange={(event) => setEditAssetForm((current) => (current ? { ...current, dataBits: event.target.value } : current))}>
                                    <option value="5">5</option>
                                    <option value="6">6</option>
                                    <option value="7">7</option>
                                    <option value="8">8</option>
                                  </select>
                                </label>
                                <label>
                                  校验位
                                  <select className="field-control" value={editAssetForm?.parity ?? 'none'} onChange={(event) => setEditAssetForm((current) => (current ? { ...current, parity: event.target.value } : current))}>
                                    <option value="none">None</option>
                                    <option value="odd">Odd</option>
                                    <option value="even">Even</option>
                                  </select>
                                </label>
                                <label>
                                  停止位
                                  <select className="field-control" value={editAssetForm?.stopBits ?? '1'} onChange={(event) => setEditAssetForm((current) => (current ? { ...current, stopBits: event.target.value } : current))}>
                                    <option value="1">1</option>
                                    <option value="1.5">1.5</option>
                                    <option value="2">2</option>
                                  </select>
                                </label>
                              </>
                            ) : null}
                          </div>
                          {editAssetError ? <div className="settings-error">{editAssetError}</div> : null}
                          <div className="modal-actions asset-inline-actions">
                            <button type="button" className="button" onClick={() => {
                              setEditingAsset(null)
                              setEditAssetForm(null)
                              setEditAssetError(null)
                            }}>取消</button>
                            <button
                              type="button"
                              className="button button-primary"
                              disabled={!editAssetForm || editAssetSaving}
                              onClick={async () => {
                                if (!editAssetForm) {
                                  return
                                }
                                setEditAssetSaving(true)
                                setEditAssetError(null)
                                try {
                                  await onUpdateAsset(asset.id, {
                                    name: editAssetForm.name.trim(),
                                    asset_type: editAssetForm.mode === 'ssh' ? 'linux' : 'network',
                                    group_id: editAssetForm.groupId ? Number(editAssetForm.groupId) : null,
                                    host: editAssetForm.mode === 'serial' ? editAssetForm.serialPort.trim() : editAssetForm.host.trim(),
                                    port: editAssetForm.mode === 'serial' ? Number(editAssetForm.baudRate) : Number(editAssetForm.port),
                                    username: editAssetForm.mode === 'serial' ? '' : editAssetForm.username.trim(),
                                    auth_type: editAssetForm.mode === 'ssh' ? editAssetForm.authType : editAssetForm.mode === 'telnet' ? 'password' : '',
                                    credential_secret: editAssetForm.mode === 'serial' ? undefined : editAssetForm.credentialSecret.trim() || undefined,
                                    tags: buildEditTags(editAssetForm),
                                    vendor: asset.vendor,
                                    description: asset.description,
                                  })
                                  setEditingAsset(null)
                                  setEditAssetForm(null)
                                } catch (error) {
                                  setEditAssetError(error instanceof Error ? error.message : '更新资产失败')
                                } finally {
                                  setEditAssetSaving(false)
                                }
                              }}
                            >
                              {editAssetSaving ? '保存中...' : '保存'}
                            </button>
                          </div>
                        </section>
                      ) : null}

                      {deletingAsset?.id === asset.id ? (
                        <section className="asset-inline-panel asset-inline-panel-danger" role="alertdialog" aria-labelledby={`delete-asset-title-${asset.id}`}>
                          <div className="asset-inline-panel-header">
                            <h3 id={`delete-asset-title-${asset.id}`} className="modal-title">确认删除主机连接？</h3>
                            <button type="button" className="asset-inline-close" onClick={() => {
                              setDeletingAsset(null)
                              setDeleteAssetError(null)
                            }}>×</button>
                          </div>
                          <p className="modal-description">{deletingAsset.name} · {getAssetMeta(deletingAsset)}</p>
                          {deleteAssetError ? <div className="settings-error">{deleteAssetError}</div> : null}
                          <div className="modal-actions asset-inline-actions">
                            <button type="button" className="button" onClick={() => {
                              setDeletingAsset(null)
                              setDeleteAssetError(null)
                            }}>取消</button>
                            <button
                              type="button"
                              className="button button-danger"
                              disabled={deleteAssetSaving}
                              onClick={async () => {
                                setDeleteAssetSaving(true)
                                setDeleteAssetError(null)
                                try {
                                  await onDeleteAsset(asset.id)
                                  setDeletingAsset(null)
                                } catch (error) {
                                  setDeleteAssetError(error instanceof Error ? error.message : '删除资产失败')
                                } finally {
                                  setDeleteAssetSaving(false)
                                }
                              }}
                            >
                              {deleteAssetSaving ? '删除中...' : '删除'}
                            </button>
                          </div>
                        </section>
                      ) : null}
                    </li>
                  )
                })}
              </ul>
            </section>
          )
        })}
      </div>
    </>
  )
}
