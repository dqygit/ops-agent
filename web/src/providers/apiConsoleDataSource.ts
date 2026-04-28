import { getConsoleBootstrap, runAgent } from '../api'
import type { ConsoleDataSource } from '../types/dataSource'

export const apiConsoleDataSource: ConsoleDataSource = {
  getConsoleBootstrap,
  runAgent,
}
