import type { KeyboardEvent } from 'react'
import type { PermissionsForm, PermissionsSectionProps } from './settingsTypes'

function addPrefix(form: PermissionsForm, key: 'allow' | 'deny'): PermissionsForm {
  const inputKey = key === 'allow' ? 'allowInput' : 'denyInput'
  const value = form[inputKey].trim()
  if (!value || form[key].includes(value)) {
    return { ...form, [inputKey]: '' }
  }
  return { ...form, [key]: [...form[key], value], [inputKey]: '' }
}

function removePrefix(form: PermissionsForm, key: 'allow' | 'deny', value: string): PermissionsForm {
  return { ...form, [key]: form[key].filter((item) => item !== value) }
}

type PrefixEditorProps = {
  title: string
  description: string
  placeholder: string
  tone: 'allow' | 'deny'
  values: string[]
  inputValue: string
  saving: boolean
  onInputChange: (value: string) => void
  onAdd: () => void
  onRemove: (value: string) => void
}

function PrefixEditor({ title, description, placeholder, tone, values, inputValue, saving, onInputChange, onAdd, onRemove }: PrefixEditorProps) {
  const handleKeyDown = (event: KeyboardEvent<HTMLInputElement>) => {
    if (event.key === 'Enter') {
      event.preventDefault()
      onAdd()
    }
  }

  const accent = tone === 'allow' ? 'text-ops-cyan border-ops-cyan/20 bg-ops-cyan/10' : 'text-ops-warning border-ops-warning/20 bg-ops-warning/10'

  return (
    <section className="flex flex-col gap-4">
      <div>
        <h5 className="text-[12px] font-bold tracking-[0.12em] text-ops-text">{title}</h5>
        <p className="text-[10px] font-medium text-ops-muted mt-1 tracking-wider opacity-60">{description}</p>
      </div>
      <div className="flex items-center gap-3">
        <input
          className="field-control flex-1 font-mono"
          value={inputValue}
          onChange={(event) => onInputChange(event.target.value)}
          onKeyDown={handleKeyDown}
          placeholder={placeholder}
          disabled={saving}
        />
        <button type="button" className="button px-6" disabled={saving || !inputValue.trim()} onClick={onAdd}>添加</button>
      </div>
      <div className="flex min-h-[44px] flex-wrap gap-2">
        {values.length === 0 ? (
          <span className="rounded-full border border-dashed border-ops-border/30 px-3 py-1.5 text-[10px] text-ops-muted">暂无命令前缀</span>
        ) : values.map((value) => (
          <button
            key={value}
            type="button"
            className={`rounded-full border px-3 py-1.5 font-mono text-[11px] font-bold transition-colors hover:border-ops-danger/40 hover:text-ops-danger ${accent}`}
            onClick={() => onRemove(value)}
            disabled={saving}
            title="点击移除"
          >
            {value} <span className="ml-1 opacity-70">×</span>
          </button>
        ))}
      </div>
    </section>
  )
}

export function PermissionsSection({ permissionsForm, saving, onFormChange, onSave }: PermissionsSectionProps) {
  return (
    <div className="flex flex-col gap-8">
      <div className="flex items-center justify-between pb-4 border-b border-ops-border/20">
        <div>
          <h4 className="text-[14px] font-bold tracking-[0.15em] text-ops-text">命令审批策略</h4>
          <p className="text-[10px] font-medium text-ops-muted mt-1 tracking-wider opacity-60">按命令前缀匹配，适用于本地、SSH、网络设备和串口会话。</p>
        </div>
      </div>

      <form className="bg-ops-deep/40 p-6 rounded-2xl border border-ops-border/20 flex flex-col gap-8" onSubmit={onSave}>
        <PrefixEditor
          title="命令白名单"
          description="匹配的命令无需人工审批。添加 * 可以允许所有命令。"
          placeholder="输入命令前缀（例如 'show'）"
          tone="allow"
          values={permissionsForm.allow}
          inputValue={permissionsForm.allowInput}
          saving={saving}
          onInputChange={(value) => onFormChange({ ...permissionsForm, allowInput: value })}
          onAdd={() => onFormChange(addPrefix(permissionsForm, 'allow'))}
          onRemove={(value) => onFormChange(removePrefix(permissionsForm, 'allow', value))}
        />

        <PrefixEditor
          title="拒绝的命令"
          description="匹配的命令会自动拒绝，无需用户批准；与允许命令冲突时，拒绝优先。"
          placeholder="输入要拒绝的命令前缀（例如 'rm -rf'）"
          tone="deny"
          values={permissionsForm.deny}
          inputValue={permissionsForm.denyInput}
          saving={saving}
          onInputChange={(value) => onFormChange({ ...permissionsForm, denyInput: value })}
          onAdd={() => onFormChange(addPrefix(permissionsForm, 'deny'))}
          onRemove={(value) => onFormChange(removePrefix(permissionsForm, 'deny', value))}
        />

        <div className="flex items-center justify-between gap-3 pt-6 border-t border-ops-border/20">
          <p className="text-[10px] text-ops-muted max-w-[460px]">前缀匹配要求命令完全相等或后面紧跟空格，例如 git 匹配 git status，但不匹配 github。</p>
          <button type="submit" className="button button-primary px-8" disabled={saving}>{saving ? '保存中...' : '保存策略'}</button>
        </div>
      </form>
    </div>
  )
}
