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
    <div className="flex flex-col gap-6">
      <div className="flex items-center justify-between">
        <div>
          <h4 className="text-ops-text font-medium">分组</h4>
          <p className="text-sm text-ops-muted mt-1">管理资产分组，资产类型仍在资产配置中单独维护。</p>
        </div>
        <button type="button" className="px-4 py-2 text-sm rounded-md bg-ops-cyan text-ops-bg hover:bg-ops-cyan/90 transition-colors font-medium" onClick={onStartCreate}>新增分组</button>
      </div>

      {showGroupForm ? (
        <form className="bg-ops-deep/30 p-5 rounded-lg border border-ops-border/20 flex flex-col gap-4 mt-2" onSubmit={onSave}>
          <label className="flex flex-col gap-1.5 text-sm text-ops-muted">
            名称
            <input className="bg-ops-panel text-ops-text border border-ops-border/30 rounded px-3 py-2 outline-none focus:border-ops-cyan transition-colors" value={groupForm.name} onChange={(event) => onFormChange({ ...groupForm, name: event.target.value })} required />
          </label>
          <label className="flex flex-col gap-1.5 text-sm text-ops-muted">
            描述
            <textarea className="bg-ops-panel text-ops-text border border-ops-border/30 rounded px-3 py-2 outline-none focus:border-ops-cyan transition-colors" value={groupForm.description} onChange={(event) => onFormChange({ ...groupForm, description: event.target.value })} rows={3} />
          </label>
          <div className="flex items-center justify-end gap-3 mt-2">
            <button type="button" className="px-4 py-2 text-sm rounded-md hover:bg-ops-border/20 text-ops-muted transition-colors" onClick={onCancelForm}>取消</button>
            <button type="submit" className="px-4 py-2 text-sm rounded-md bg-ops-cyan text-ops-bg hover:bg-ops-cyan/90 transition-colors font-medium disabled:opacity-50" disabled={saving}>{saving ? '保存中...' : '保存'}</button>
          </div>
        </form>
      ) : null}

      {groups.length === 0 ? <div className="text-center py-10 text-ops-muted text-sm bg-ops-panel/20 rounded-lg border border-ops-border/10 border-dashed">暂无分组</div> : null}
      <div className="flex flex-col gap-2">
        {groups.map((group) => (
          <article key={group.id} className="flex items-center justify-between p-4 rounded-lg bg-ops-panel border border-ops-border/20 hover:border-ops-border/50 transition-colors group">
            <div className="flex flex-col gap-1">
              <strong className="text-ops-text font-medium">{group.name}</strong>
              <span className="text-xs text-ops-muted">{group.description || '无描述'}</span>
            </div>
            <div className="flex items-center gap-2 opacity-0 group-hover:opacity-100 transition-opacity">
              <button type="button" className="px-3 py-1.5 text-xs rounded border border-ops-border/30 text-ops-muted hover:text-ops-text hover:bg-ops-border/20 transition-colors" onClick={() => onStartEdit(group)}>编辑</button>
              <button type="button" className="px-3 py-1.5 text-xs rounded border border-red-500/30 text-red-500 hover:bg-red-500/10 transition-colors" onClick={() => onStartDelete(group)}>删除</button>
            </div>
          </article>
        ))}
      </div>
    </div>
  )
}
