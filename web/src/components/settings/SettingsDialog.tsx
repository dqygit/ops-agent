import { type FormEvent, useEffect, useState } from 'react'

import {
  createGroup,
  createModelConfig,
  createSSHKey,
  deleteGroup,
  deleteModelConfig,
  deleteSSHKey,
  getApprovalPolicy,
  getGroups,
  getModelConfigs,
  getSSHKeys,
  setDefaultModelConfig,
  testModelConfig,
  updateApprovalPolicy,
  updateGroup,
  updateModelConfig,
  updateSSHKey,
} from '../../api'
import type { AssetGroup, ModelConfig, SSHKey } from '../../types/ops'
import { DeleteConfirmDialog } from './DeleteConfirmDialog'
import { GroupsSection } from './GroupsSection'
import { ModelsSection } from './ModelsSection'
import { PermissionsSection } from './PermissionsSection'
import { SSHKeysSection } from './SSHKeysSection'
import type { GroupForm, ModelForm, PermissionsForm, SettingsDialogProps, SettingsSection, SSHKeyForm } from './settingsTypes'

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

const emptySSHKeyForm: SSHKeyForm = {
  name: '',
  publicKey: '',
  privateKey: '',
  passphrase: '',
}

const emptyPermissionsForm: PermissionsForm = {
  allow: [],
  deny: [],
  allowInput: '',
  denyInput: '',
}

function sshKeyToForm(sshKey: SSHKey): SSHKeyForm {
  return {
    name: sshKey.name,
    publicKey: sshKey.publicKey,
    privateKey: '',
    passphrase: '',
  }
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

export function SettingsDialog({ initialGroups, selectedModel, sshKeys: initialSSHKeys, onSelectedModelChange, onGroupsChange, onModelOptionsChange, onSSHKeysChange, onClose }: SettingsDialogProps) {
  const [activeSection, setActiveSection] = useState<SettingsSection>('groups')
  const [groups, setGroups] = useState<AssetGroup[]>(initialGroups)
  const [modelConfigs, setModelConfigs] = useState<ModelConfig[]>([])
  const [sshKeys, setSSHKeys] = useState<SSHKey[]>(initialSSHKeys)
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
  const [sshKeyForm, setSSHKeyForm] = useState<SSHKeyForm>(emptySSHKeyForm)
  const [showSSHKeyForm, setShowSSHKeyForm] = useState(false)
  const [editingSSHKey, setEditingSSHKey] = useState<SSHKey | null>(null)
  const [deletingSSHKey, setDeletingSSHKey] = useState<SSHKey | null>(null)
  const [permissionsForm, setPermissionsForm] = useState<PermissionsForm>(emptyPermissionsForm)
  const [saving, setSaving] = useState(false)
  const [testResult, setTestResult] = useState<string | null>(null)

  const loadSettings = async () => {
    setLoading(true)
    setError(null)
    try {
      const [nextGroups, nextModels, nextSSHKeys, nextApprovalPolicy] = await Promise.all([getGroups(), getModelConfigs(), getSSHKeys(), getApprovalPolicy()])
      setGroups(nextGroups)
      onGroupsChange(nextGroups)
      setModelConfigs(nextModels)
      onModelOptionsChange(getModelOptions(nextModels))
      setSSHKeys(nextSSHKeys)
      onSSHKeysChange(nextSSHKeys)
      setPermissionsForm({ allow: nextApprovalPolicy.permissions.allow, deny: nextApprovalPolicy.permissions.deny, allowInput: '', denyInput: '' })
    } catch (loadError) {
      setError(loadError instanceof Error ? loadError.message : 'Failed to load settings')
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
      setError(saveError instanceof Error ? saveError.message : 'Failed to save group')
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
      setError(deleteError instanceof Error ? deleteError.message : 'Failed to delete group')
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

  const startCreateSSHKey = () => {
    setEditingSSHKey(null)
    setDeletingSSHKey(null)
    setSSHKeyForm(emptySSHKeyForm)
    setShowSSHKeyForm(true)
  }

  const startEditSSHKey = (sshKey: SSHKey) => {
    setEditingSSHKey(sshKey)
    setDeletingSSHKey(null)
    setSSHKeyForm(sshKeyToForm(sshKey))
    setShowSSHKeyForm(true)
  }

  const cancelSSHKeyForm = () => {
    setEditingSSHKey(null)
    setShowSSHKeyForm(false)
    setSSHKeyForm(emptySSHKeyForm)
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
      setError(saveError instanceof Error ? saveError.message : 'Failed to save model')
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
      setError(defaultError instanceof Error ? defaultError.message : 'Failed to set default model')
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
      setError(deleteError instanceof Error ? deleteError.message : 'Failed to delete model')
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
      setError(testError instanceof Error ? testError.message : 'Connection test failed')
    } finally {
      setSaving(false)
    }
  }

  const saveSSHKey = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault()
    setSaving(true)
    setError(null)
    try {
      const payload = {
        name: sshKeyForm.name.trim(),
        public_key: sshKeyForm.publicKey.trim(),
        private_key: sshKeyForm.privateKey.trim() || undefined,
        passphrase: sshKeyForm.passphrase.trim() || undefined,
      }
      const savedSSHKey = editingSSHKey
        ? await updateSSHKey(editingSSHKey.id, payload)
        : await createSSHKey({
          name: payload.name,
          public_key: payload.public_key,
          private_key: sshKeyForm.privateKey.trim(),
          passphrase: payload.passphrase,
        })
      const nextSSHKeys = editingSSHKey
        ? sshKeys.map((item) => (item.id === savedSSHKey.id ? savedSSHKey : item))
        : [savedSSHKey, ...sshKeys]
      setSSHKeys(nextSSHKeys)
      onSSHKeysChange(nextSSHKeys)
      cancelSSHKeyForm()
    } catch (saveError) {
      setError(saveError instanceof Error ? saveError.message : 'Failed to save SSH key')
    } finally {
      setSaving(false)
    }
  }

  const confirmDeleteSSHKey = async () => {
    if (!deletingSSHKey) {
      return
    }
    setSaving(true)
    setError(null)
    try {
      await deleteSSHKey(deletingSSHKey.id)
      const nextSSHKeys = sshKeys.filter((item) => item.id !== deletingSSHKey.id)
      setSSHKeys(nextSSHKeys)
      onSSHKeysChange(nextSSHKeys)
      setDeletingSSHKey(null)
    } catch (deleteError) {
      setError(deleteError instanceof Error ? deleteError.message : 'Failed to delete SSH key')
    } finally {
      setSaving(false)
    }
  }

  const savePermissions = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault()
    setSaving(true)
    setError(null)
    try {
      await updateApprovalPolicy({ permissions: { allow: permissionsForm.allow, deny: permissionsForm.deny } })
      setPermissionsForm({ ...permissionsForm, allowInput: '', denyInput: '' })
    } catch (saveError) {
      setError(saveError instanceof Error ? saveError.message : 'Failed to save permissions')
    } finally {
      setSaving(false)
    }
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-ops-bg/60 backdrop-blur-md animate-in fade-in duration-300" role="presentation">
      <section className="w-[880px] max-w-[95vw] h-[640px] max-h-[90vh] bg-ops-panel/90 border border-ops-border/40 rounded-2xl shadow-2xl flex flex-col overflow-hidden backdrop-blur-xl animate-in zoom-in-95 duration-300" role="dialog" aria-modal="true" aria-labelledby="settings-title">
        <div className="flex items-center justify-between p-6 border-b border-ops-border/20 bg-ops-panel shrink-0">
          <div>
            <h3 id="settings-title" className="text-[16px] font-bold  text-ops-cyan">System Configuration</h3>
            <p className="text-[11px] font-medium text-ops-muted mt-1 tracking-wider opacity-60">Manage your workspace environments and AI models.</p>
          </div>
          <button type="button" className="h-8 px-4 text-[11px] font-bold  tracking-widest rounded-lg transition-all duration-200 text-ops-muted hover:text-ops-text hover:bg-ops-border/30 active:scale-95" onClick={onClose}>Close</button>
        </div>
        <div className="flex flex-1 overflow-hidden">
          <nav className="w-[220px] border-r border-ops-border/20 bg-ops-deep/40 p-4 flex flex-col gap-2 shrink-0 overflow-y-auto" aria-label="Settings Navigation">
            <button type="button" className={`w-full text-left px-4 py-3 rounded-xl transition-all duration-200 text-[11px] font-bold  active:scale-[0.98] ${activeSection === 'groups' ? 'bg-ops-cyan/15 text-ops-cyan shadow-glow border border-ops-cyan/30' : 'text-ops-muted hover:text-ops-text hover:bg-ops-panel/60 border border-transparent'}`} onClick={() => setActiveSection('groups')}>Infrastructure Groups</button>
            <button type="button" className={`w-full text-left px-4 py-3 rounded-xl transition-all duration-200 text-[11px] font-bold  active:scale-[0.98] ${activeSection === 'models' ? 'bg-ops-cyan/15 text-ops-cyan shadow-glow border border-ops-cyan/30' : 'text-ops-muted hover:text-ops-text hover:bg-ops-panel/60 border border-transparent'}`} onClick={() => setActiveSection('models')}>AI Model Configs</button>
            <button type="button" className={`w-full text-left px-4 py-3 rounded-xl transition-all duration-200 text-[11px] font-bold  active:scale-[0.98] ${activeSection === 'sshKeys' ? 'bg-ops-cyan/15 text-ops-cyan shadow-glow border border-ops-cyan/30' : 'text-ops-muted hover:text-ops-text hover:bg-ops-panel/60 border border-transparent'}`} onClick={() => setActiveSection('sshKeys')}>Identity Keys (SSH)</button>
            <button type="button" className={`w-full text-left px-4 py-3 rounded-xl transition-all duration-200 text-[11px] font-bold  active:scale-[0.98] ${activeSection === 'permissions' ? 'bg-ops-cyan/15 text-ops-cyan shadow-glow border border-ops-cyan/30' : 'text-ops-muted hover:text-ops-text hover:bg-ops-panel/60 border border-transparent'}`} onClick={() => setActiveSection('permissions')}>Command Permissions</button>
          </nav>
          <div className="flex-1 p-6 overflow-y-auto bg-ops-panel/50 relative">
            {error ? <div className="p-4 mb-6 rounded-md bg-red-500/10 border border-red-500/20 text-red-500 text-sm flex items-center justify-between">{error}<button type="button" className="px-3 py-1.5 rounded-md bg-ops-border/20 hover:bg-ops-border/30 transition-colors text-ops-text text-sm" onClick={() => void loadSettings()}>Retry</button></div> : null}
            {loading ? (
              <div className="flex items-center justify-center h-40 text-ops-muted text-sm">Loading...</div>
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
            ) : activeSection === 'models' ? (
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
            ) : activeSection === 'sshKeys' ? (
              <SSHKeysSection
                sshKeys={sshKeys}
                sshKeyForm={sshKeyForm}
                showSSHKeyForm={showSSHKeyForm}
                editingSSHKey={editingSSHKey}
                saving={saving}
                onStartCreate={startCreateSSHKey}
                onStartEdit={startEditSSHKey}
                onStartDelete={setDeletingSSHKey}
                onFormChange={setSSHKeyForm}
                onCancelForm={cancelSSHKeyForm}
                onSave={saveSSHKey}
              />
            ) : (
              <PermissionsSection
                permissionsForm={permissionsForm}
                saving={saving}
                onFormChange={setPermissionsForm}
                onSave={savePermissions}
              />
            )}
          </div>
        </div>
        {deletingGroup ? (
          <DeleteConfirmDialog
            titleId="delete-group-title"
            title="Confirm Group Deletion?"
            message={deletingGroup.name}
            saving={saving}
            onCancel={() => setDeletingGroup(null)}
            onConfirm={() => void confirmDeleteGroup()}
          />
        ) : null}
        {deletingModel ? (
          <DeleteConfirmDialog
            titleId="delete-model-title"
            title="Confirm Model Deletion?"
            message={deletingModel.isDefault ? 'The default model cannot be deleted. Please set another model as default first.' : deletingModel.name}
            saving={saving}
            confirmDisabled={deletingModel.isDefault}
            onCancel={() => setDeletingModel(null)}
            onConfirm={() => void confirmDeleteModel()}
          />
        ) : null}
        {deletingSSHKey ? (
          <DeleteConfirmDialog
            titleId="delete-ssh-key-title"
            title="Confirm SSH Key Deletion?"
            message={deletingSSHKey.name}
            saving={saving}
            onCancel={() => setDeletingSSHKey(null)}
            onConfirm={() => void confirmDeleteSSHKey()}
          />
        ) : null}
      </section>
    </div>
  )
}
