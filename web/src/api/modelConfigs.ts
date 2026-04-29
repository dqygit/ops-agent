import { requestJson, requestVoid } from './client'
import type { ModelConfig } from '../types/ops'

export type ModelConfigPayload = {
  name: string
  provider: string
  baseUrl: string
  apiKey?: string
  modelName: string
  isDefault: boolean
  timeoutSeconds: number
  temperature: number
  maxTokens: number
  description: string
}

export type ModelConnectionTestPayload = {
  provider: string
  baseUrl: string
  apiKey: string
  modelName: string
  timeoutSeconds: number
  temperature: number
  maxTokens: number
}

export type ModelConnectionTestResult = {
  success: boolean
  message: string
}

type ModelConfigDto = {
  id: number
  name: string
  provider: string
  base_url: string
  api_key_masked: string
  model_name: string
  is_default: boolean
  timeout_seconds: number
  temperature: number
  max_tokens: number
  description: string
  created_at: string | null
  updated_at: string | null
}

type ModelConfigRequest = {
  name: string
  provider: string
  base_url: string
  api_key?: string
  model_name: string
  is_default: boolean
  timeout_seconds: number
  temperature: number
  max_tokens: number
  description: string
}

type ModelConnectionTestRequest = {
  provider: string
  base_url: string
  api_key: string
  model_name: string
  timeout_seconds: number
  temperature: number
  max_tokens: number
}

function toModelConfigRequest(payload: ModelConfigPayload): ModelConfigRequest {
  return {
    name: payload.name,
    provider: payload.provider,
    base_url: payload.baseUrl,
    ...(payload.apiKey ? { api_key: payload.apiKey } : {}),
    model_name: payload.modelName,
    is_default: payload.isDefault,
    timeout_seconds: payload.timeoutSeconds,
    temperature: payload.temperature,
    max_tokens: payload.maxTokens,
    description: payload.description,
  }
}

function toConnectionTestRequest(payload: ModelConnectionTestPayload): ModelConnectionTestRequest {
  return {
    provider: payload.provider,
    base_url: payload.baseUrl,
    api_key: payload.apiKey,
    model_name: payload.modelName,
    timeout_seconds: payload.timeoutSeconds,
    temperature: payload.temperature,
    max_tokens: payload.maxTokens,
  }
}

export function mapModelConfig(config: ModelConfigDto): ModelConfig {
  return {
    id: config.id,
    name: config.name,
    provider: config.provider,
    baseUrl: config.base_url,
    apiKeyMasked: config.api_key_masked,
    modelName: config.model_name,
    isDefault: config.is_default,
    timeoutSeconds: config.timeout_seconds,
    temperature: config.temperature,
    maxTokens: config.max_tokens,
    description: config.description,
    createdAt: config.created_at,
    updatedAt: config.updated_at,
  }
}

export async function getModelConfigs(): Promise<ModelConfig[]> {
  const configs = await requestJson<ModelConfigDto[]>('/api/model-configs')
  return configs.map(mapModelConfig)
}

export async function createModelConfig(payload: ModelConfigPayload): Promise<ModelConfig> {
  const config = await requestJson<ModelConfigDto>('/api/model-configs', {
    method: 'POST',
    body: JSON.stringify(toModelConfigRequest(payload)),
  })
  return mapModelConfig(config)
}

export async function updateModelConfig(configId: number, payload: ModelConfigPayload): Promise<ModelConfig> {
  const config = await requestJson<ModelConfigDto>(`/api/model-configs/${configId}`, {
    method: 'PUT',
    body: JSON.stringify(toModelConfigRequest(payload)),
  })
  return mapModelConfig(config)
}

export async function deleteModelConfig(configId: number): Promise<void> {
  await requestVoid(`/api/model-configs/${configId}`, { method: 'DELETE' })
}

export async function setDefaultModelConfig(configId: number): Promise<ModelConfig> {
  const config = await requestJson<ModelConfigDto>(`/api/model-configs/${configId}/default`, { method: 'POST' })
  return mapModelConfig(config)
}

export async function testModelConfig(payload: ModelConnectionTestPayload): Promise<ModelConnectionTestResult> {
  return requestJson<ModelConnectionTestResult>('/api/model-configs/test', {
    method: 'POST',
    body: JSON.stringify(toConnectionTestRequest(payload)),
  })
}
