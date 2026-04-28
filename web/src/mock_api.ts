import { getMockAssistantState, runMockAgent } from './mock_api_modules/assistant'
import { getMockAssets } from './mock_api_modules/assets'
import { getMockHistoryByAsset } from './mock_api_modules/history'
import type { ConsoleBootstrap } from './types/api'

export async function getConsoleBootstrap(): Promise<ConsoleBootstrap> {
  const [assets, historyByAsset, assistantState] = await Promise.all([
    getMockAssets(),
    getMockHistoryByAsset(),
    getMockAssistantState(),
  ])

  return {
    assets,
    historyByAsset,
    modelOptions: assistantState.modelOptions,
    initialPrompt: assistantState.initialPrompt,
    terminalOutput: assistantState.terminalOutput,
    initialEvents: assistantState.initialEvents,
  }
}

export { runMockAgent }
