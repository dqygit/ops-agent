import type { EventItem } from '../types/ops'

const modelOptions = ['claude-sonnet-4-6', 'claude-opus-4-7', 'gpt-5.5', 'gpt-5.4']

const initialPrompt = '检查该资产当前负载，并总结是否存在明显异常。'

const terminalOutput = [
  'Connected · session term-10023',
  '',
  '$ hostname',
  'prod-linux-01',
  '',
  '$ uptime',
  '10:42:11 up 21 days, load average: 0.42, 0.51, 0.49',
  '',
  '$ free -m',
  'Mem: 7980 total, 5120 used, 2860 free',
].join('\n')

const initialEvents: EventItem[] = [
  { id: '1', kind: 'status', text: '状态: idle' },
  {
    id: '2',
    kind: 'plan',
    steps: [
      { title: '确认目标主机与服务', command: 'hostname && systemctl status nginx' },
      { title: '采集基础资源数据', command: 'uptime && free -m && df -h' },
    ],
  },
  { id: '3', kind: 'approval', text: '等待审批后再执行命令。' },
]

export async function getMockAssistantState(): Promise<{
  modelOptions: string[]
  initialPrompt: string
  terminalOutput: string
  initialEvents: EventItem[]
}> {
  return structuredClone({
    modelOptions,
    initialPrompt,
    terminalOutput,
    initialEvents,
  })
}

export async function runMockAgent(prompt: string, currentEvents: EventItem[]): Promise<EventItem[]> {
  const nextIndex = currentEvents.length + 1
  return [
    ...currentEvents,
    { id: String(nextIndex), kind: 'status', text: '状态: running' },
    { id: String(nextIndex + 1), kind: 'output', text: `执行任务: ${prompt}` },
    {
      id: String(nextIndex + 2),
      kind: 'final',
      text: '已完成示例运行。下一步可接入真实 API 与流式事件。',
    },
  ]
}
