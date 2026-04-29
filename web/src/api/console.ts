import { mapAsset } from './assets'
import { requestJson } from './client'
import { mapAssetGroup, type AssetGroupDto } from './groups'
import type { ConsoleBootstrap } from '../types/api'
import type { EventItem } from '../types/ops'

type ConsoleBootstrapDto = Omit<ConsoleBootstrap, 'assets' | 'groups'> & {
  assets: Parameters<typeof mapAsset>[0][]
  groups: AssetGroupDto[]
}

export async function getConsoleBootstrap(): Promise<ConsoleBootstrap> {
  const bootstrap = await requestJson<ConsoleBootstrapDto>('/api/console/bootstrap')
  return {
    ...bootstrap,
    assets: bootstrap.assets.map(mapAsset),
    groups: bootstrap.groups.map(mapAssetGroup),
  }
}

export async function runAgent(prompt: string, currentEvents: EventItem[], assetId?: number, modelName?: string): Promise<EventItem[]> {
  return requestJson<EventItem[]>('/api/console/run', {
    method: 'POST',
    body: JSON.stringify({ prompt, currentEvents, asset_id: assetId, model_name: modelName }),
  })
}

export async function approveAgent(runId: string, approved: boolean): Promise<EventItem[]> {
  return requestJson<EventItem[]>('/api/console/approval', {
    method: 'POST',
    body: JSON.stringify({ run_id: runId, approved }),
  })
}
