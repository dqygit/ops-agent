import type { ConsoleBootstrap } from './types/api'
import type { EventItem } from './types/ops'

export { getAssets } from './api_modules/assets'

export async function getConsoleBootstrap(): Promise<ConsoleBootstrap> {
  throw new Error('Real API bootstrap is not implemented yet.')
}

export async function runAgent(_prompt: string, _currentEvents: EventItem[]): Promise<EventItem[]> {
  throw new Error('Real API runAgent is not implemented yet.')
}
