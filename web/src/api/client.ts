const API_BASE_URL = import.meta.env.VITE_API_BASE_URL ?? ''

function buildRequest(path: string, init?: RequestInit) {
  return fetch(`${API_BASE_URL}${path}`, {
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
    if (typeof payload.message === 'string') {
      return payload.message
    }
  } catch {
    return fallback
  }
  return fallback
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
