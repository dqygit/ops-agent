import { type FormEvent, useEffect, useState } from 'react'

import {
  createGroup,
  createModelConfig,
  deleteGroup,
  deleteModelConfig,
  getGroups,
  getModelConfigs,
  setDefaultModelConfig,
  testModelConfig,
  updateGroup,
  updateModelConfig,
} from '../../api'
import type { AssetGroup, ModelConfig } from '../../types/ops'
import { DeleteConfirmDialog } from './DeleteConfirmDialog'
import { GroupsSection } from './GroupsSection'
import { ModelsSection } from './ModelsSection'
import type { GroupForm, ModelForm, SettingsDialogProps, SettingsSection } from './settingsTypes'

const emptyGroupForm: GroupForm = {
  name: '',
  description: '',
}

const emptyModelForm: ModelForm = {
  name: '',
  provider: 'anthropic',
  baseUrl: '',
  apiKey: '',
  modelName: '',
  isDefault: false,
  timeoutSeconds: '30',
  temperature: '0.2',
  maxTokens: '1024',
  description: '',
}

function getModelOptions(configs: ModelConfig[]) {
  return configs.map((config) => config.modelName)
}

function modelToForm(config: ModelConfig): ModelForm {
  return {
    name: config.name,
    provider: config.provider,
    baseUrl: config.baseUrl,
    apiKey: '',
    modelName: config.modelName,
    isDefault: config.isDefault,
    timeoutSeconds: String(config.timeoutSeconds),
    temperature: String(config.temperature),
    maxTokens: String(config.maxTokens),
    description: config.description,
  }
}

export function SettingsDialog({ initialGroups, selectedModel, onSelectedModelChange, onGroupsChange, onModelOptionsChange, onClose }: SettingsDialogProps) {
  const [activeSection, setActiveSection] = useState<SettingsSection>('groups')
  const [groups, setGroups] = useState<AssetGroup[]>(initialGroups)
  const [modelConfigs, setModelConfigs] = useState<ModelConfig[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [groupForm, setGroupForm] = useState<GroupForm>(emptyGroupForm)
  const [showGroupForm, setShowGroupForm] = useState(false)
  const [editingGroup, setEditingGroup] = useState<AssetGroup | null>(null)
  const [deletingGroup, setDeletingGroup] = useState<AssetGroup | null>(null)
  const [modelForm, setModelForm] = useState<ModelForm>(emptyModelForm)
  const [showModelForm, setShowModelForm] = useState(false)
  const [editingModel, setEditingModel] = useState<ModelConfig | null>(null)
  const [deletingModel, setDeletingModel] = useState<ModelConfig | null>(null)
  const [saving, setSaving] = useState(false)
  const [testResult, setTestResult] = useState<string | null>(null)

  const loadSettings = async () => {
    setLoading(true)
    setError(null)
    try {
      const [nextGroups, nextModels] = await Promise.all([getGroups(), getModelConfigs()])
      setGroups(nextGroups)
      onGroupsChange(nextGroups)
      setModelConfigs(nextModels)
      onModelOptionsChange(getModelOptions(nextModels))
    } catch (loadError) {
      setError(loadError instanceof Error ? loadError.message : '加载设置失败')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    void loadSettings()
  }, [])

  const startCreateGroup = () => {
    setEditingGroup(null)
    setDeletingGroup(null)
    setGroupForm(emptyGroupForm)
    setShowGroupForm(true)
  }

  const startEditGroup = (group: AssetGroup) => {
    setEditingGroup(group)
    setDeletingGroup(null)
    setGroupForm({ name: group.name, description: group.description })
    setShowGroupForm(true)
  }

  const cancelGroupForm = () => {
    setEditingGroup(null)
    setShowGroupForm(false)
    setGroupForm(emptyGroupForm)
  }

  const saveGroup = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault()
    setSaving(true)
    setError(null)
    try {
      const payload = { name: groupForm.name.trim(), description: groupForm.description.trim() }
      const savedGroup = editingGroup
        ? await updateGroup(editingGroup.id, payload)
        : await createGroup(payload)
      const nextGroups = editingGroup
        ? groups.map((group) => (group.id === savedGroup.id ? savedGroup : group))
        : [savedGroup, ...groups]
      setGroups(nextGroups)
      onGroupsChange(nextGroups)
      cancelGroupForm()
    } catch (saveError) {
      setError(saveError instanceof Error ? saveError.message : '保存分组失败')
    } finally {
      setSaving(false)
    }
  }

  const confirmDeleteGroup = async () => {
    if (!deletingGroup) {
      return
    }
    setSaving(true)
    setError(null)
    try {
      await deleteGroup(deletingGroup.id)
      const nextGroups = groups.filter((group) => group.id !== deletingGroup.id)
      setGroups(nextGroups)
      onGroupsChange(nextGroups)
      setDeletingGroup(null)
    } catch (deleteError) {
      setError(deleteError instanceof Error ? deleteError.message : '删除分组失败')
    } finally {
      setSaving(false)
    }
  }

  const startCreateModel = () => {
    setEditingModel(null)
    setDeletingModel(null)
    setTestResult(null)
    setModelForm(emptyModelForm)
    setShowModelForm(true)
  }

  const startEditModel = (config: ModelConfig) => {
    setEditingModel(config)
    setDeletingModel(null)
    setTestResult(null)
    setModelForm(modelToForm(config))
    setShowModelForm(true)
  }

  const cancelModelForm = () => {
    setEditingModel(null)
    setShowModelForm(false)
    setTestResult(null)
    setModelForm(emptyModelForm)
  }

  const toModelPayload = () => ({
    name: modelForm.name.trim(),
    provider: modelForm.provider,
    baseUrl: modelForm.baseUrl.trim(),
    apiKey: modelForm.apiKey.trim() || undefined,
    modelName: modelForm.modelName.trim(),
    isDefault: modelForm.isDefault,
    timeoutSeconds: Number(modelForm.timeoutSeconds) || 30,
    temperature: Number(modelForm.temperature) || 0.2,
    maxTokens: Number(modelForm.maxTokens) || 1024,
    description: modelForm.description.trim(),
  })

  const saveModel = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault()
    setSaving(true)
    setError(null)
    try {
      const savedConfig = editingModel
        ? await updateModelConfig(editingModel.id, toModelPayload())
        : await createModelConfig(toModelPayload())
      const nextModels = editingModel
        ? modelConfigs.map((config) => (config.id === savedConfig.id ? savedConfig : { ...config, isDefault: savedConfig.isDefault ? false : config.isDefault }))
        : [savedConfig, ...modelConfigs.map((config) => ({ ...config, isDefault: savedConfig.isDefault ? false : config.isDefault }))]
      setModelConfigs(nextModels)
      onModelOptionsChange(getModelOptions(nextModels))
      if (savedConfig.isDefault) {
        onSelectedModelChange(savedConfig.modelName)
      }
      cancelModelForm()
    } catch (saveError) {
      setError(saveError instanceof Error ? saveError.message : '保存模型失败')
    } finally {
      setSaving(false)
    }
  }

  const setDefaultModel = async (config: ModelConfig) => {
    setSaving(true)
    setError(null)
    try {
      const defaultConfig = await setDefaultModelConfig(config.id)
      const nextModels = modelConfigs.map((item) => ({ ...item, isDefault: item.id === defaultConfig.id }))
      setModelConfigs(nextModels)
      onModelOptionsChange(getModelOptions(nextModels))
      onSelectedModelChange(defaultConfig.modelName)
    } catch (defaultError) {
      setError(defaultError instanceof Error ? defaultError.message : '设置默认模型失败')
    } finally {
      setSaving(false)
    }
  }

  const confirmDeleteModel = async () => {
    if (!deletingModel || deletingModel.isDefault) {
      return
    }
    setSaving(true)
    setError(null)
    try {
      await deleteModelConfig(deletingModel.id)
      const nextModels = modelConfigs.filter((config) => config.id !== deletingModel.id)
      setModelConfigs(nextModels)
      onModelOptionsChange(getModelOptions(nextModels))
      setDeletingModel(null)
    } catch (deleteError) {
      setError(deleteError instanceof Error ? deleteError.message : '删除模型失败')
    } finally {
      setSaving(false)
    }
  }

  const testModel = async () => {
    setSaving(true)
    setTestResult(null)
    setError(null)
    try {
      const result = await testModelConfig({
        provider: modelForm.provider,
        baseUrl: modelForm.baseUrl.trim(),
        apiKey: modelForm.apiKey.trim(),
        modelName: modelForm.modelName.trim(),
        timeoutSeconds: Number(modelForm.timeoutSeconds) || 30,
        temperature: Number(modelForm.temperature) || 0.2,
        maxTokens: Number(modelForm.maxTokens) || 1024,
      })
      setTestResult(result.message)
    } catch (testError) {
      setError(testError instanceof Error ? testError.message : '测试连接失败')
    } finally {
      setSaving(false)
    }
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm" role="presentation">
      <section className="w-[800px] max-w-[90vw] h-[600px] max-h-[90vh] bg-ops-strong border border-ops-border/50 rounded-xl shadow-2xl flex flex-col overflow-hidden" role="dialog" aria-modal="true" aria-labelledby="settings-title">
        <div className="flex items-center justify-between p-5 border-b border-ops-border/30 bg-ops-panel shrink-0">
          <div>
            <h3 id="settings-title" className="text-lg font-medium text-ops-text">设置</h3>
            <p className="text-sm text-ops-muted mt-1">管理分组和模型配置。</p>
          </div>
          <button type="button" className="px-4 py-2 text-sm rounded-md transition-colors text-ops-muted hover:text-ops-text hover:bg-ops-border/20" onClick={onClose}>关闭</button>
        </div>
        <div className="flex flex-1 overflow-hidden">
          <nav className="w-[200px] border-r border-ops-border/20 bg-ops-deep p-4 flex flex-col gap-1 shrink-0 overflow-y-auto" aria-label="设置导航">
            <button type="button" className={`w-full text-left px-3 py-2 rounded-md transition-colors text-sm font-medium ${activeSection === 'groups' ? 'bg-ops-border/20 text-ops-cyan' : 'text-ops-muted hover:text-ops-text hover:bg-ops-border/10'}`} onClick={() => setActiveSection('groups')}>分组</button>
            <button type="button" className={`w-full text-left px-3 py-2 rounded-md transition-colors text-sm font-medium ${activeSection === 'models' ? 'bg-ops-border/20 text-ops-cyan' : 'text-ops-muted hover:text-ops-text hover:bg-ops-border/10'}`} onClick={() => setActiveSection('models')}>模型</button>
          </nav>
          <div className="flex-1 p-6 overflow-y-auto bg-ops-panel/50 relative">
            {error ? <div className="p-4 mb-6 rounded-md bg-red-500/10 border border-red-500/20 text-red-500 text-sm flex items-center justify-between">{error}<button type="button" className="px-3 py-1.5 rounded-md bg-ops-border/20 hover:bg-ops-border/30 transition-colors text-ops-text text-sm" onClick={() => void loadSettings()}>重试</button></div> : null}
            {loading ? (
              <div className="flex items-center justify-center h-40 text-ops-muted text-sm">加载中...</div>
            ) : activeSection === 'groups' ? (
              <GroupsSection
                groups={groups}
                groupForm={groupForm}
                showGroupForm={showGroupForm}
                saving={saving}
                onStartCreate={startCreateGroup}
                onStartEdit={startEditGroup}
                onStartDelete={setDeletingGroup}
                onFormChange={setGroupForm}
                onCancelForm={cancelGroupForm}
                onSave={saveGroup}
              />
            ) : (
              <ModelsSection
                selectedModel={selectedModel}
                modelConfigs={modelConfigs}
                modelForm={modelForm}
                showModelForm={showModelForm}
                editingModel={editingModel}
                saving={saving}
                testResult={testResult}
                onStartCreate={startCreateModel}
                onStartEdit={startEditModel}
                onStartDelete={setDeletingModel}
                onFormChange={setModelForm}
                onCancelForm={cancelModelForm}
                onSave={saveModel}
                onSetDefault={(config) => void setDefaultModel(config)}
                onTest={() => void testModel()}
              />
            )}
          </div>
        </div>
        {deletingGroup ? (
          <DeleteConfirmDialog
            titleId="delete-group-title"
            title="确认删除分组？"
            message={deletingGroup.name}
            saving={saving}
            onCancel={() => setDeletingGroup(null)}
            onConfirm={() => void confirmDeleteGroup()}
          />
        ) : null}
        {deletingModel ? (
          <DeleteConfirmDialog
            titleId="delete-model-title"
            title="确认删除模型？"
            message={deletingModel.isDefault ? '默认模型不能删除，请先设置其他默认模型。' : deletingModel.name}
            saving={saving}
            confirmDisabled={deletingModel.isDefault}
            onCancel={() => setDeletingModel(null)}
            onConfirm={() => void confirmDeleteModel()}
          />
        ) : null}
      </section>
    </div>
  )
}
