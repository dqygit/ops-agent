import { requestJson } from './client'

export type SerialPort = {
  device: string
  description: string
}

export async function getSerialPorts(signal?: AbortSignal): Promise<SerialPort[]> {
  return requestJson<SerialPort[]>('/api/system/serial-ports', { signal })
}
