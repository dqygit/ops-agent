import type { SSHKeysSectionProps } from './settingsTypes'

export function SSHKeysSection({ sshKeys, sshKeyForm, showSSHKeyForm, editingSSHKey, saving, onStartCreate, onStartEdit, onStartDelete, onFormChange, onCancelForm, onSave }: SSHKeysSectionProps) {
  return (
    <section className="flex flex-col gap-8">
      <div className="flex items-center justify-between pb-4 border-b border-ops-border/20">
        <div>
          <h4 className="text-[14px] font-bold  tracking-[0.15em] text-ops-text">Identity Key Management</h4>
          <p className="text-[10px] font-medium text-ops-muted mt-1 tracking-wider opacity-60">Securely store SSH private keys for automated asset access.</p>
        </div>
        <button type="button" className="button button-primary" onClick={onStartCreate}>Provision New Key</button>
      </div>

      {showSSHKeyForm ? (
        <form className="bg-ops-deep/40 p-6 rounded-2xl border border-ops-border/20 flex flex-col gap-5 mt-2 animate-in slide-in-from-top-4 duration-300" onSubmit={onSave}>
          <label className="flex flex-col gap-2 text-[11px] font-bold  tracking-widest text-ops-muted/70">
            Key Identifier
            <input className="field-control" value={sshKeyForm.name} onChange={(event) => onFormChange({ ...sshKeyForm, name: event.target.value })} placeholder="e.g. ops-master-key" required />
          </label>
          <label className="flex flex-col gap-2 text-[11px] font-bold  tracking-widest text-ops-muted/70">
            Public Key (Standard Format)
            <textarea className="field-control font-mono min-h-[80px]" value={sshKeyForm.publicKey} onChange={(event) => onFormChange({ ...sshKeyForm, publicKey: event.target.value })} placeholder="ssh-rsa AAAA..." rows={3} required />
          </label>
          <label className="flex flex-col gap-2 text-[11px] font-bold  tracking-widest text-ops-muted/70">
            Private Key (PEM/OpenSSH)
            <textarea className="field-control font-mono min-h-[120px]" value={sshKeyForm.privateKey} onChange={(event) => onFormChange({ ...sshKeyForm, privateKey: event.target.value })} placeholder={editingSSHKey ? 'Keep Unchanged' : '-----BEGIN OPENSSH PRIVATE KEY-----'} rows={6} required={!editingSSHKey} />
          </label>
          <label className="flex flex-col gap-2 text-[11px] font-bold  tracking-widest text-ops-muted/70">
            Key Passphrase (Optional)
            <input className="field-control font-mono" type="password" value={sshKeyForm.passphrase} onChange={(event) => onFormChange({ ...sshKeyForm, passphrase: event.target.value })} placeholder="••••••••••••" />
          </label>
          <div className="flex items-center justify-end gap-3 mt-2 pt-4 border-t border-ops-border/20">
            <button type="button" className="button px-6" onClick={onCancelForm}>Cancel</button>
            <button type="submit" className="button button-primary px-8" disabled={saving}>{saving ? 'Processing...' : 'Authorize Key'}</button>
          </div>
        </form>
      ) : null}

      <div className="flex flex-col gap-3">
        {sshKeys.map((sshKey) => (
          <article key={sshKey.id} className="flex items-center justify-between p-5 rounded-2xl bg-ops-panel/40 border border-ops-border/20 hover:border-ops-cyan/30 hover:bg-ops-panel/60 transition-all duration-300 group shadow-sm">
            <div className="flex items-center gap-4">
              <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-xl bg-ops-deep border border-ops-border/20 text-ops-muted group-hover:text-ops-cyan group-hover:border-ops-cyan/30 transition-colors">
                <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M21 2l-2 2m-7.61 7.61a5.5 5.5 0 1 1-7.778 7.778 5.5 5.5 0 0 1 7.777-7.777zm0 0L15.5 7.5m0 0l3 3L22 7l-3-3L15.5 7.5z" /></svg>
              </div>
              <div className="flex flex-col gap-1">
                <strong className="text-[13px] font-bold text-ops-text tracking-tight">{sshKey.name}</strong>
                <span className="text-[10px] text-ops-muted font-mono opacity-60 truncate max-w-[400px]">{sshKey.publicKey.substring(0, 48)}...</span>
              </div>
            </div>
            <div className="flex items-center gap-2 opacity-0 group-hover:opacity-100 transition-all duration-200">
              <button type="button" className="button h-8 px-4 text-[10px]" onClick={() => onStartEdit(sshKey)}>Update</button>
              <button type="button" className="button button-danger h-8 px-4 text-[10px]" onClick={() => onStartDelete(sshKey)}>Revoke</button>
            </div>
          </article>
        ))}
      </div>
    </section>
  )
}
