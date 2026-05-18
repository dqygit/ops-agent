import { getDesktopApiBaseUrl } from '../desktop'

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL ?? ''
let runtimeApiBaseUrl: string | null = null
let runtimeApiBaseUrlLoaded = false

async function resolveApiBaseUrl() {
  if (runtimeApiBaseUrlLoaded) {
    return runtimeApiBaseUrl ?? API_BASE_URL
  }
  runtimeApiBaseUrlLoaded = true
  runtimeApiBaseUrl = await getDesktopApiBaseUrl()
  return runtimeApiBaseUrl ?? API_BASE_URL
}

async function buildRequest(path: string, init?: RequestInit) {
  const baseUrl = await resolveApiBaseUrl()
  return fetch(`${baseUrl}${path}`, {
    headers: {
      'Content-Type': 'application/json',
      ...(init?.headers ?? {}),
    },
    ...init,
  })
}

async function getErrorMessage(response: Response) {
  const fallback = `Request failed: ${response.status}`
  try {
    const payload = (await response.json()) as { detail?: unknown; message?: unknown }
    if (typeof payload.detail === 'string') {
      return payload.detail
    }
    if (payload.detail && typeof payload.detail === 'object') {
      const detail = payload.detail as { failureReason?: unknown; status?: unknown }
      if (typeof detail.failureReason === 'string') {
        return detail.failureReason
      }
      if (typeof detail.status === 'string') {
        return detail.status
      }
    }
    if (typeof payload.message === 'string') {
      return payload.message
    }
  } catch {
    return fallback
  }
  return fallback
}

export async function requestEventStream(path: string, init?: RequestInit): Promise<Response> {
  const response = await buildRequest(path, {
    ...init,
    headers: {
      Accept: 'text/event-stream',
      ...(init?.headers ?? {}),
    },
  })

  if (!response.ok) {
    throw new Error(await getErrorMessage(response))
  }

  return response
}

export async function requestJson<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await buildRequest(path, init)

  if (!response.ok) {
    throw new Error(await getErrorMessage(response))
  }

  return (await response.json()) as T
}

export async function requestVoid(path: string, init?: RequestInit): Promise<void> {
  const response = await buildRequest(path, init)

  if (!response.ok) {
    throw new Error(await getErrorMessage(response))
  }
}
