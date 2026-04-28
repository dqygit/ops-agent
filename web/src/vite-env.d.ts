/// <reference types="vite/client" />

interface ImportMetaEnv {
  readonly VITE_CONSOLE_DATA_SOURCE?: 'mock' | 'api'
}

interface ImportMeta {
  readonly env: ImportMetaEnv
}
