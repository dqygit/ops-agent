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
    <div className="flex flex-col gap-6">
      <div className="flex items-center justify-between">
        <div>
          <h4 className="text-ops-text font-medium">模型</h4>
          <p className="text-sm text-ops-muted mt-1">当前选择：{selectedModel || '未选择'}</p>
        </div>
        <button type="button" className="px-4 py-2 text-sm rounded-md bg-ops-cyan text-ops-bg hover:bg-ops-cyan/90 transition-colors font-medium" onClick={onStartCreate}>新增模型</button>
      </div>

      {showModelForm ? (
        <form className="bg-ops-deep/30 p-5 rounded-lg border border-ops-border/20 grid grid-cols-2 gap-4 mt-2" onSubmit={onSave}>
          <label className="flex flex-col gap-1.5 text-sm text-ops-muted">
            名称
            <input className="bg-ops-panel text-ops-text border border-ops-border/30 rounded px-3 py-2 outline-none focus:border-ops-cyan transition-colors" value={modelForm.name} onChange={(event) => onFormChange({ ...modelForm, name: event.target.value })} required />
          </label>
          <label className="flex flex-col gap-1.5 text-sm text-ops-muted">
            供应商
            <select className="bg-ops-panel text-ops-text border border-ops-border/30 rounded px-3 py-2 outline-none focus:border-ops-cyan transition-colors" value={modelForm.provider} onChange={(event) => onFormChange({ ...modelForm, provider: event.target.value })}>
              <option value="anthropic">anthropic</option>
              <option value="openai_compatible">openai_compatible</option>
            </select>
          </label>
          <label className="flex flex-col gap-1.5 text-sm text-ops-muted col-span-2">
            Base URL
            <input className="bg-ops-panel text-ops-text border border-ops-border/30 rounded px-3 py-2 outline-none focus:border-ops-cyan transition-colors" value={modelForm.baseUrl} onChange={(event) => onFormChange({ ...modelForm, baseUrl: event.target.value })} required />
          </label>
          <label className="flex flex-col gap-1.5 text-sm text-ops-muted col-span-2">
            API Key
            <input className="bg-ops-panel text-ops-text border border-ops-border/30 rounded px-3 py-2 outline-none focus:border-ops-cyan transition-colors" type="password" value={modelForm.apiKey} onChange={(event) => onFormChange({ ...modelForm, apiKey: event.target.value })} placeholder={editingModel ? '留空则保持不变' : ''} required={!editingModel} />
          </label>
          <label className="flex flex-col gap-1.5 text-sm text-ops-muted col-span-2">
            模型名称
            <input className="bg-ops-panel text-ops-text border border-ops-border/30 rounded px-3 py-2 outline-none focus:border-ops-cyan transition-colors" value={modelForm.modelName} onChange={(event) => onFormChange({ ...modelForm, modelName: event.target.value })} required />
          </label>
          <label className="flex flex-col gap-1.5 text-sm text-ops-muted">
            超时时间
            <input className="bg-ops-panel text-ops-text border border-ops-border/30 rounded px-3 py-2 outline-none focus:border-ops-cyan transition-colors" type="number" min="1" value={modelForm.timeoutSeconds} onChange={(event) => onFormChange({ ...modelForm, timeoutSeconds: event.target.value })} required />
          </label>
          <label className="flex flex-col gap-1.5 text-sm text-ops-muted">
            Temperature
            <input className="bg-ops-panel text-ops-text border border-ops-border/30 rounded px-3 py-2 outline-none focus:border-ops-cyan transition-colors" type="number" step="0.1" value={modelForm.temperature} onChange={(event) => onFormChange({ ...modelForm, temperature: event.target.value })} required />
          </label>
          <label className="flex flex-col gap-1.5 text-sm text-ops-muted">
            Max Tokens
            <input className="bg-ops-panel text-ops-text border border-ops-border/30 rounded px-3 py-2 outline-none focus:border-ops-cyan transition-colors" type="number" min="1" value={modelForm.maxTokens} onChange={(event) => onFormChange({ ...modelForm, maxTokens: event.target.value })} required />
          </label>
          <label className="flex items-center gap-2 text-sm text-ops-text col-span-2 mt-2">
            <input type="checkbox" className="accent-ops-cyan w-4 h-4" checked={modelForm.isDefault} disabled={editingModel?.isDefault} onChange={(event) => onFormChange({ ...modelForm, isDefault: event.target.checked })} />
            {editingModel?.isDefault ? '当前默认模型' : '设为默认'}
          </label>
          <label className="flex flex-col gap-1.5 text-sm text-ops-muted col-span-2">
            描述
            <textarea className="bg-ops-panel text-ops-text border border-ops-border/30 rounded px-3 py-2 outline-none focus:border-ops-cyan transition-colors" value={modelForm.description} onChange={(event) => onFormChange({ ...modelForm, description: event.target.value })} rows={3} />
          </label>
          {testResult ? <div className="col-span-2 p-3 text-sm text-ops-text bg-ops-panel border border-ops-border/20 rounded font-mono break-all">{testResult}</div> : null}
          <div className="flex items-center justify-between gap-3 mt-4 pt-4 border-t border-ops-border/20 col-span-2">
            <button type="button" className="px-4 py-2 text-sm rounded-md border border-ops-border/30 text-ops-text hover:bg-ops-border/20 transition-colors disabled:opacity-50" onClick={onTest} disabled={saving || !modelForm.apiKey.trim()} title={editingModel && !modelForm.apiKey.trim() ? '请输入新的 API Key 后再测试连接' : undefined}>测试连接</button>
            <div className="flex items-center gap-3">
              <button type="button" className="px-4 py-2 text-sm rounded-md hover:bg-ops-border/20 text-ops-muted transition-colors" onClick={onCancelForm}>取消</button>
              <button type="submit" className="px-4 py-2 text-sm rounded-md bg-ops-cyan text-ops-bg hover:bg-ops-cyan/90 transition-colors font-medium disabled:opacity-50" disabled={saving}>{saving ? '保存中...' : '保存'}</button>
            </div>
          </div>
        </form>
      ) : null}

      {modelConfigs.length === 0 ? <div className="text-center py-10 text-ops-muted text-sm bg-ops-panel/20 rounded-lg border border-ops-border/10 border-dashed">暂无模型配置</div> : null}
      <div className="flex flex-col gap-2">
        {modelConfigs.map((config) => (
          <article key={config.id} className="flex items-center justify-between p-4 rounded-lg bg-ops-panel border border-ops-border/20 hover:border-ops-border/50 transition-colors group">
            <div className="flex flex-col gap-1">
              <strong className="text-ops-text font-medium flex items-center gap-2">{config.name} {config.isDefault ? <span className="px-1.5 py-0.5 text-[10px] rounded text-ops-green bg-ops-green/10 border border-ops-green/20">默认</span> : null}</strong>
              <span className="text-xs text-ops-muted font-mono">{config.provider} · {config.modelName} · {config.apiKeyMasked}</span>
            </div>
            <div className="flex items-center gap-2 opacity-0 group-hover:opacity-100 transition-opacity">
              {!config.isDefault ? <button type="button" className="px-3 py-1.5 text-xs rounded border border-ops-border/30 text-ops-muted hover:text-ops-text hover:bg-ops-border/20 transition-colors" onClick={() => onSetDefault(config)} disabled={saving}>设为默认</button> : null}
              <button type="button" className="px-3 py-1.5 text-xs rounded border border-ops-border/30 text-ops-muted hover:text-ops-text hover:bg-ops-border/20 transition-colors" onClick={() => onStartEdit(config)}>编辑</button>
              <button type="button" className="px-3 py-1.5 text-xs rounded border border-red-500/30 text-red-500 hover:bg-red-500/10 transition-colors disabled:opacity-30 disabled:hover:bg-transparent" onClick={() => onStartDelete(config)} disabled={config.isDefault} title={config.isDefault ? '请先设置其他默认模型' : undefined}>删除</button>
            </div>
          </article>
        ))}
      </div>
    </div>
  )
}
