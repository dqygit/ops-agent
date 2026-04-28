import type { SessionRecord } from '../types/ops'

const historyByAsset: Record<number, SessionRecord[]> = {
  1: [
    { id: 101, title: '巡检磁盘与内存', model: 'claude-sonnet-4-6' },
    { id: 102, title: '检查 nginx 状态', model: 'gpt-5.5' },
  ],
  2: [{ id: 201, title: '查看 BGP 邻居状态', model: 'claude-sonnet-4-6' }],
  3: [{ id: 301, title: '恢复前置检查', model: 'gpt-5.4' }],
}

export async function getMockHistoryByAsset(): Promise<Record<number, SessionRecord[]>> {
  return structuredClone(historyByAsset)
}
