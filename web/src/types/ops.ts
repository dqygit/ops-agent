export type Asset = {
  id: number
  name: string
  assetType: 'linux' | 'huawei'
  host: string
  port: number
}

export type SessionRecord = {
  id: number
  title: string
  model: string
}

export type PlanStep = {
  title: string
  command: string
}

export type EventItem =
  | { id: string; kind: 'status'; text: string }
  | { id: string; kind: 'plan'; steps: PlanStep[] }
  | { id: string; kind: 'approval'; text: string }
  | { id: string; kind: 'output'; text: string }
  | { id: string; kind: 'final'; text: string }
  | { id: string; kind: 'error'; text: string }
