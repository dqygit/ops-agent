import type { ConsoleBootstrap } from './api'
import type { EventItem } from './ops'

export type ConsoleDataSource = {
  getConsoleBootstrap: () => Promise<ConsoleBootstrap>
  runAgent: (prompt: string, currentEvents: EventItem[]) => Promise<EventItem[]>
}
