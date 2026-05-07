import type { SSHKeysSectionProps } from './settingsTypes'

export function SSHKeysSection({ sshKeys, sshKeyForm, showSSHKeyForm, editingSSHKey, saving, onStartCreate, onStartEdit, onStartDelete, onFormChange, onCancelForm, onSave }: SSHKeysSectionProps) {
  return (
    <section className="flex flex-col gap-4">
      <div className="flex items-center justify-between">
        <div>
          <h4 className="text-base font-medium text-ops-text">SSH 密钥</h4>
          <p className="text-sm text-ops-muted mt-1">管理可复用的 SSH 密钥库。</p>
        </div>
        <button type="button" className="px-4 py-2 rounded-md bg-ops-cyan/20 text-ops-cyan hover:bg-ops-cyan/30 transition-colors text-sm" onClick={onStartCreate}>新增密钥</button>
      </div>

      {showSSHKeyForm ? (
        <form className="p-4 rounded-lg border border-ops-border/30 bg-ops-deep/60 flex flex-col gap-4" onSubmit={onSave}>
          <div className="grid grid-cols-1 gap-4">
            <label className="flex flex-col gap-1 text-sm text-ops-muted">
              名称
              <input className="bg-ops-panel text-ops-text border border-ops-border/30 rounded px-3 py-2 outline-none focus:border-ops-cyan transition-colors" value={sshKeyForm.name} onChange={(event) => onFormChange({ ...sshKeyForm, name: event.target.value })} required />
            </label>
            <label className="flex flex-col gap-1 text-sm text-ops-muted">
              公钥内容
              <textarea className="bg-ops-panel text-ops-text border border-ops-border/30 rounded px-3 py-2 outline-none focus:border-ops-cyan transition-colors font-mono" value={sshKeyForm.publicKey} onChange={(event) => onFormChange({ ...sshKeyForm, publicKey: event.target.value })} rows={4} />
            </label>
            <label className="flex flex-col gap-1 text-sm text-ops-muted">
              {editingSSHKey ? '更新私钥内容' : '私钥内容'}
              <textarea className="bg-ops-panel text-ops-text border border-ops-border/30 rounded px-3 py-2 outline-none focus:border-ops-cyan transition-colors font-mono" value={sshKeyForm.privateKey} onChange={(event) => onFormChange({ ...sshKeyForm, privateKey: event.target.value })} rows={8} placeholder={editingSSHKey ? '留空则保持不变' : '粘贴私钥内容'} required={!editingSSHKey} />
            </label>
            <label className="flex flex-col gap-1 text-sm text-ops-muted">
              私钥口令
              <input className="bg-ops-panel text-ops-text border border-ops-border/30 rounded px-3 py-2 outline-none focus:border-ops-cyan transition-colors" type="password" value={sshKeyForm.passphrase} onChange={(event) => onFormChange({ ...sshKeyForm, passphrase: event.target.value })} placeholder={editingSSHKey ? '留空则保持不变' : '可选'} />
            </label>
          </div>
          <div className="flex items-center justify-between gap-3 mt-2">
            <button type="button" className="px-4 py-2 text-sm rounded-md hover:bg-ops-border/20 text-ops-muted transition-colors" onClick={onCancelForm}>取消</button>
            <button type="submit" className="px-4 py-2 text-sm rounded-md bg-ops-cyan text-ops-bg hover:bg-ops-cyan/90 transition-colors font-medium disabled:opacity-50" disabled={saving}>{saving ? '保存中...' : '保存'}</button>
          </div>
        </form>
      ) : null}

      <div className="space-y-3">
        {sshKeys.length === 0 ? <div className="text-sm text-ops-muted py-10 text-center">暂无 SSH 密钥</div> : null}
        {sshKeys.map((sshKey) => (
          <div key={sshKey.id} className="p-4 rounded-lg border border-ops-border/20 bg-ops-panel flex items-start justify-between gap-4">
            <div className="min-w-0">
              <div className="text-sm font-medium text-ops-text">{sshKey.name}</div>
              <div className="text-xs text-ops-muted mt-1 break-all">{sshKey.publicKey || '未配置公钥'}</div>
              <div className="text-xs text-ops-muted mt-2">{sshKey.hasPassphrase ? '已配置口令' : '无口令'}</div>
            </div>
            <div className="flex items-center gap-2 shrink-0">
              <button type="button" className="px-3 py-1.5 text-xs rounded border border-ops-border/30 text-ops-muted hover:text-ops-text hover:bg-ops-border/20 transition-colors" onClick={() => onStartEdit(sshKey)}>编辑</button>
              <button type="button" className="px-3 py-1.5 text-xs rounded border border-red-500/30 text-red-500 hover:bg-red-500/10 transition-colors" onClick={() => onStartDelete(sshKey)}>删除</button>
            </div>
          </div>
        ))}
      </div>
    </section>
  )
}
