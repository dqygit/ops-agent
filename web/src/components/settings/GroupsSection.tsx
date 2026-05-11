import type { GroupsSectionProps } from './settingsTypes'

export function GroupsSection({
  groups,
  groupForm,
  showGroupForm,
  saving,
  onStartCreate,
  onStartEdit,
  onStartDelete,
  onFormChange,
  onCancelForm,
  onSave,
}: GroupsSectionProps) {
  return (
    <div className="flex flex-col gap-8">
      <div className="flex items-center justify-between pb-4 border-b border-ops-border/20">
        <div>
          <h4 className="text-[14px] font-bold  tracking-[0.15em] text-ops-text">Infrastructure Groups</h4>
          <p className="text-[10px] font-medium text-ops-muted mt-1 tracking-wider opacity-60">Organize your assets by environment or project.</p>
        </div>
        <button type="button" className="button button-primary" onClick={onStartCreate}>New Group</button>
      </div>

      {showGroupForm ? (
        <form className="bg-ops-deep/40 p-6 rounded-2xl border border-ops-border/20 flex flex-col gap-5 mt-2 animate-in slide-in-from-top-4 duration-300" onSubmit={onSave}>
          <label className="flex flex-col gap-2 text-[11px] font-bold  tracking-widest text-ops-muted/70">
            Group Label
            <input className="field-control" value={groupForm.name} onChange={(event) => onFormChange({ ...groupForm, name: event.target.value })} placeholder="e.g. Production Cluster" required />
          </label>
          <label className="flex flex-col gap-2 text-[11px] font-bold  tracking-widest text-ops-muted/70">
            Internal Description
            <textarea className="field-control min-h-[80px]" value={groupForm.description} onChange={(event) => onFormChange({ ...groupForm, description: event.target.value })} placeholder="Purpose of this grouping..." rows={3} />
          </label>
          <div className="flex items-center justify-end gap-3 mt-2 pt-4 border-t border-ops-border/20">
            <button type="button" className="button px-6" onClick={onCancelForm}>Cancel</button>
            <button type="submit" className="button button-primary px-8" disabled={saving}>{saving ? 'Processing...' : 'Save Group'}</button>
          </div>
        </form>
      ) : null}

      {groups.length === 0 ? <div className="text-center py-10 text-ops-muted text-sm bg-ops-panel/20 rounded-lg border border-ops-border/10 border-dashed">No groups found</div> : null}
      <div className="flex flex-col gap-3">
        {groups.map((group) => (
          <article key={group.id} className="flex items-center justify-between p-5 rounded-2xl bg-ops-panel/40 border border-ops-border/20 hover:border-ops-cyan/30 hover:bg-ops-panel/60 transition-all duration-300 group shadow-sm">
            <div className="flex flex-col gap-1.5">
              <strong className="text-[13px] font-bold text-ops-text tracking-tight">{group.name}</strong>
              {group.description ? <span className="text-[10px] text-ops-muted font-bold  tracking-widest opacity-60">{group.description === '默认分组' ? 'Default Group' : group.description}</span> : null}
            </div>
            <div className="flex items-center gap-2 opacity-0 group-hover:opacity-100 transition-all duration-200">
              <button type="button" className="button h-8 px-4 text-[10px]" onClick={() => onStartEdit(group)}>Edit</button>
              <button type="button" className="button button-danger h-8 px-4 text-[10px]" onClick={() => onStartDelete(group)}>Delete</button>
            </div>
          </article>
        ))}
      </div>
    </div>
  )
}
