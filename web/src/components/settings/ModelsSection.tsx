import type { ModelsSectionProps } from './settingsTypes'

export function ModelsSection({
  selectedModel,
  modelConfigs,
  modelForm,
  showModelForm,
  editingModel,
  saving,
  testResult,
  onStartCreate,
  onStartEdit,
  onStartDelete,
  onFormChange,
  onCancelForm,
  onSave,
  onSetDefault,
  onTest,
}: ModelsSectionProps) {
  return (
    <div className="settings-section">
      <div className="settings-section-header">
        <div>
          <h4>模型</h4>
          <p>当前选择：{selectedModel || '未选择'}</p>
        </div>
        <button type="button" className="button button-primary" onClick={onStartCreate}>新增模型</button>
      </div>

      {showModelForm ? (
        <form className="settings-form settings-model-form" onSubmit={onSave}>
          <label>
            名称
            <input className="field-control" value={modelForm.name} onChange={(event) => onFormChange({ ...modelForm, name: event.target.value })} required />
          </label>
          <label>
            供应商
            <select className="field-control" value={modelForm.provider} onChange={(event) => onFormChange({ ...modelForm, provider: event.target.value })}>
              <option value="anthropic">anthropic</option>
              <option value="openai_compatible">openai_compatible</option>
            </select>
          </label>
          <label>
            Base URL
            <input className="field-control" value={modelForm.baseUrl} onChange={(event) => onFormChange({ ...modelForm, baseUrl: event.target.value })} required />
          </label>
          <label>
            API Key
            <input className="field-control" type="password" value={modelForm.apiKey} onChange={(event) => onFormChange({ ...modelForm, apiKey: event.target.value })} placeholder={editingModel ? '留空则保持不变' : ''} required={!editingModel} />
          </label>
          <label>
            模型名称
            <input className="field-control" value={modelForm.modelName} onChange={(event) => onFormChange({ ...modelForm, modelName: event.target.value })} required />
          </label>
          <label>
            超时时间
            <input className="field-control" type="number" min="1" value={modelForm.timeoutSeconds} onChange={(event) => onFormChange({ ...modelForm, timeoutSeconds: event.target.value })} required />
          </label>
          <label>
            Temperature
            <input className="field-control" type="number" step="0.1" value={modelForm.temperature} onChange={(event) => onFormChange({ ...modelForm, temperature: event.target.value })} required />
          </label>
          <label>
            Max Tokens
            <input className="field-control" type="number" min="1" value={modelForm.maxTokens} onChange={(event) => onFormChange({ ...modelForm, maxTokens: event.target.value })} required />
          </label>
          <label className="settings-checkbox">
            <input type="checkbox" checked={modelForm.isDefault} disabled={editingModel?.isDefault} onChange={(event) => onFormChange({ ...modelForm, isDefault: event.target.checked })} />
            {editingModel?.isDefault ? '当前默认模型' : '设为默认'}
          </label>
          <label className="settings-form-wide">
            描述
            <textarea className="field-control" value={modelForm.description} onChange={(event) => onFormChange({ ...modelForm, description: event.target.value })} rows={3} />
          </label>
          {testResult ? <div className="settings-form-wide settings-result">{testResult}</div> : null}
          <div className="settings-form-wide modal-actions">
            <button type="button" className="button" onClick={onTest} disabled={saving || !modelForm.apiKey.trim()} title={editingModel && !modelForm.apiKey.trim() ? '请输入新的 API Key 后再测试连接' : undefined}>测试连接</button>
            <button type="button" className="button" onClick={onCancelForm}>取消</button>
            <button type="submit" className="button button-primary" disabled={saving}>{saving ? '保存中...' : '保存'}</button>
          </div>
        </form>
      ) : null}

      {modelConfigs.length === 0 ? <div className="settings-empty">暂无模型配置</div> : null}
      <div className="settings-list">
        {modelConfigs.map((config) => (
          <article key={config.id} className="settings-row">
            <div className="settings-row-main">
              <strong>{config.name} {config.isDefault ? <span className="settings-badge">默认</span> : null}</strong>
              <span>{config.provider} · {config.modelName} · {config.apiKeyMasked}</span>
            </div>
            <div className="settings-row-actions">
              {!config.isDefault ? <button type="button" className="button" onClick={() => onSetDefault(config)} disabled={saving}>设为默认</button> : null}
              <button type="button" className="button" onClick={() => onStartEdit(config)}>编辑</button>
              <button type="button" className="button button-danger" onClick={() => onStartDelete(config)} disabled={config.isDefault} title={config.isDefault ? '请先设置其他默认模型' : undefined}>删除</button>
            </div>
          </article>
        ))}
      </div>
    </div>
  )
}
