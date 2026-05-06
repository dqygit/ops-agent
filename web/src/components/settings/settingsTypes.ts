import type { FormEvent } from 'react'
import type { AssetGroup, ModelConfig, SSHKey } from '../../types/ops'

export type SettingsSection = 'groups' | 'models' | 'sshKeys'

export type GroupForm = {
  name: string
  description: string
}

export type ModelForm = {
  name: string
  provider: string
  baseUrl: string
  apiKey: string
  modelName: string
  isDefault: boolean
  timeoutSeconds: string
  temperature: string
  maxTokens: string
  description: string
}

export type SSHKeyForm = {
  name: string
  publicKey: string
  privateKey: string
  passphrase: string
}

export type SettingsDialogProps = {
  initialGroups: AssetGroup[]
  selectedModel: string
  sshKeys: SSHKey[]
  onSelectedModelChange: (model: string) => void
  onGroupsChange: (groups: AssetGroup[]) => void
  onModelOptionsChange: (modelOptions: string[]) => void
  onSSHKeysChange: (sshKeys: SSHKey[]) => void
  onClose: () => void
}

export type GroupsSectionProps = {
  groups: AssetGroup[]
  groupForm: GroupForm
  showGroupForm: boolean
  saving: boolean
  onStartCreate: () => void
  onStartEdit: (group: AssetGroup) => void
  onStartDelete: (group: AssetGroup) => void
  onFormChange: (form: GroupForm) => void
  onCancelForm: () => void
  onSave: (event: FormEvent<HTMLFormElement>) => void
}

export type ModelsSectionProps = {
  selectedModel: string
  modelConfigs: ModelConfig[]
  modelForm: ModelForm
  showModelForm: boolean
  editingModel: ModelConfig | null
  saving: boolean
  testResult: string | null
  onStartCreate: () => void
  onStartEdit: (config: ModelConfig) => void
  onStartDelete: (config: ModelConfig) => void
  onFormChange: (form: ModelForm) => void
  onCancelForm: () => void
  onSave: (event: FormEvent<HTMLFormElement>) => void
  onSetDefault: (config: ModelConfig) => void
  onTest: () => void
}

export type SSHKeysSectionProps = {
  sshKeys: SSHKey[]
  sshKeyForm: SSHKeyForm
  showSSHKeyForm: boolean
  editingSSHKey: SSHKey | null
  saving: boolean
  onStartCreate: () => void
  onStartEdit: (sshKey: SSHKey) => void
  onStartDelete: (sshKey: SSHKey) => void
  onFormChange: (form: SSHKeyForm) => void
  onCancelForm: () => void
  onSave: (event: FormEvent<HTMLFormElement>) => void
}
