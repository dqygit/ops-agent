/// <reference types="vite/client" />

interface ImportMetaEnv {
  readonly VITE_CONSOLE_DATA_SOURCE?: 'api'
  readonly VITE_API_BASE_URL?: string
}

interface ImportMeta {
  readonly env: ImportMetaEnv
}
