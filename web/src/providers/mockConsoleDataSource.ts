import { getConsoleBootstrap, runMockAgent } from '../mock_api'
import type { ConsoleDataSource } from '../types/dataSource'

export const mockConsoleDataSource: ConsoleDataSource = {
  getConsoleBootstrap,
  runAgent: runMockAgent,
}
