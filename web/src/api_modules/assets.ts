import { requestJson } from './client'
import type { Asset } from '../types/ops'

export async function getAssets(): Promise<Asset[]> {
  return requestJson<Asset[]>('/api/assets')
}
