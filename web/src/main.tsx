import React from 'react'
import ReactDOM from 'react-dom/client'
import { App } from './App'
import { AppearanceProvider } from './hooks/useAppearance'
import './index.css'

ReactDOM.createRoot(document.getElementById('root')!).render(
  <AppearanceProvider>
    <App />
  </AppearanceProvider>,
)
