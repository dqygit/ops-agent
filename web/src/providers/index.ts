import { apiConsoleDataSource } from './apiConsoleDataSource'
import { mockConsoleDataSource } from './mockConsoleDataSource'
import type { ConsoleDataSource } from '../types/dataSource'

const sourceName = import.meta.env.VITE_CONSOLE_DATA_SOURCE ?? 'mock'

const dataSources: Record<string, ConsoleDataSource> = {
  api: apiConsoleDataSource,
  mock: mockConsoleDataSource,
}

export const consoleDataSource = dataSources[sourceName] ?? mockConsoleDataSource
