import type { Asset } from '../types/ops'

const assets: Asset[] = [
  { id: 1, name: 'prod-linux-01', assetType: 'linux', host: '10.10.1.24', port: 22 },
  { id: 2, name: 'core-sw-01', assetType: 'huawei', host: '10.20.0.5', port: 22 },
  { id: 3, name: 'backup-linux-02', assetType: 'linux', host: '10.10.3.18', port: 22 },
]

export async function getMockAssets(): Promise<Asset[]> {
  return structuredClone(assets)
}
