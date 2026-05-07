import { mapAsset } from './assets'
import { requestEventStream, requestJson } from './client'
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

export async function runAgent(prompt: string, currentEvents: EventItem[], assetId?: number, terminalId?: string | null, modelName?: string): Promise<EventItem[]> {
  return requestJson<EventItem[]>('/api/console/run', {
    method: 'POST',
    body: JSON.stringify({ prompt, currentEvents, asset_id: assetId, terminal_id: terminalId, model_name: modelName }),
  })
}

export async function approveAgent(runId: string, approved: boolean): Promise<EventItem[]> {
  return requestJson<EventItem[]>('/api/console/approval', {
    method: 'POST',
    body: JSON.stringify({ run_id: runId, approved }),
  })
}

function parseSseBlock(block: string): EventItem | null {
  const lines = block.split('\n')
  const dataLines = lines.filter((line) => line.startsWith('data:')).map((line) => line.slice(5).trim())
  if (dataLines.length === 0) {
    return null
  }
  return JSON.parse(dataLines.join('\n')) as EventItem
}

async function* readEventStream(response: Response): AsyncGenerator<EventItem, void, void> {
  const reader = response.body?.getReader()
  if (!reader) {
    return
  }
  const decoder = new TextDecoder()
  let buffer = ''
  while (true) {
    const { done, value } = await reader.read()
    if (done) {
      break
    }
    buffer += decoder.decode(value, { stream: true })
    const blocks = buffer.split('\n\n')
    buffer = blocks.pop() ?? ''
    for (const block of blocks) {
      const event = parseSseBlock(block)
      if (event) {
        yield event
      }
    }
  }
  if (buffer.trim()) {
    const event = parseSseBlock(buffer)
    if (event) {
      yield event
    }
  }
}

export async function streamRunAgent(prompt: string, currentEvents: EventItem[], assetId?: number, terminalId?: string | null, modelName?: string): Promise<AsyncGenerator<EventItem, void, void>> {
  const response = await requestEventStream('/api/console/run', {
    method: 'POST',
    body: JSON.stringify({ prompt, currentEvents, asset_id: assetId, terminal_id: terminalId, model_name: modelName }),
  })
  return readEventStream(response)
}

export async function streamApproveAgent(runId: string, approved: boolean): Promise<AsyncGenerator<EventItem, void, void>> {
  const response = await requestEventStream('/api/console/approval', {
    method: 'POST',
    body: JSON.stringify({ run_id: runId, approved }),
  })
  return readEventStream(response)
}
