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
    <div className="settings-section">
      <div className="settings-section-header">
        <div>
          <h4>分组</h4>
          <p>管理资产分组，资产类型仍在资产配置中单独维护。</p>
        </div>
        <button type="button" className="button button-primary" onClick={onStartCreate}>新增分组</button>
      </div>

      {showGroupForm ? (
        <form className="settings-form" onSubmit={onSave}>
          <label>
            名称
            <input className="field-control" value={groupForm.name} onChange={(event) => onFormChange({ ...groupForm, name: event.target.value })} required />
          </label>
          <label>
            描述
            <textarea className="field-control" value={groupForm.description} onChange={(event) => onFormChange({ ...groupForm, description: event.target.value })} rows={3} />
          </label>
          <div className="modal-actions">
            <button type="button" className="button" onClick={onCancelForm}>取消</button>
            <button type="submit" className="button button-primary" disabled={saving}>{saving ? '保存中...' : '保存'}</button>
          </div>
        </form>
      ) : null}

      {groups.length === 0 ? <div className="settings-empty">暂无分组</div> : null}
      <div className="settings-list">
        {groups.map((group) => (
          <article key={group.id} className="settings-row">
            <div className="settings-row-main">
              <strong>{group.name}</strong>
              <span>{group.description || '无描述'}</span>
            </div>
            <div className="settings-row-actions">
              <button type="button" className="button" onClick={() => onStartEdit(group)}>编辑</button>
              <button type="button" className="button button-danger" onClick={() => onStartDelete(group)}>删除</button>
            </div>
          </article>
        ))}
      </div>
    </div>
  )
}
