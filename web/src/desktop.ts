type TauriCoreModule = {
  invoke: (command: string, args?: Record<string, unknown>) => Promise<unknown>
}

export async function getDesktopApiBaseUrl(): Promise<string | null> {
  const isTauri = typeof window !== 'undefined' && '__TAURI_INTERNALS__' in window
  if (!isTauri) {
    return null
  }
  try {
    const tauriCore = (await import('@tauri-apps/api/core')) as TauriCoreModule
    const baseUrl = await tauriCore.invoke('backend_base_url')
    return typeof baseUrl === 'string' ? baseUrl : null
  } catch {
    return null
  }
}
