import { useEffect, useMemo, useState } from 'react'

import { consoleDataSource } from '../providers'
import type { ConsoleBootstrap } from '../types/api'
import type { EventItem } from '../types/ops'

const emptyBootstrap: ConsoleBootstrap = {
  assets: [],
  historyByAsset: {},
  modelOptions: [],
  initialPrompt: '',
  terminalOutput: '',
  initialEvents: [],
}

export function useConsoleData() {
  const [tab, setTab] = useState<'assets' | 'history'>('assets')
  const [bootstrap, setBootstrap] = useState<ConsoleBootstrap>(emptyBootstrap)
  const [selectedAssetId, setSelectedAssetId] = useState<number | null>(null)
  const [selectedModel, setSelectedModel] = useState<string>('')
  const [prompt, setPrompt] = useState('')
  const [events, setEvents] = useState<EventItem[]>([])

  useEffect(() => {
    let active = true

    void consoleDataSource.getConsoleBootstrap().then((data) => {
      if (!active) {
        return
      }
      setBootstrap(data)
      setSelectedAssetId(data.assets[0]?.id ?? null)
      setSelectedModel(data.modelOptions[0] ?? '')
      setPrompt(data.initialPrompt)
      setEvents(data.initialEvents)
    })

    return () => {
      active = false
    }
  }, [])

  const selectedAsset = useMemo(
    () => bootstrap.assets.find((asset) => asset.id === selectedAssetId) ?? bootstrap.assets[0] ?? null,
    [bootstrap.assets, selectedAssetId],
  )

  const history = selectedAsset ? bootstrap.historyByAsset[selectedAsset.id] ?? [] : []

  const runAgent = async () => {
    const nextEvents = await consoleDataSource.runAgent(prompt, events)
    setEvents(nextEvents)
  }

  return {
    tab,
    setTab,
    bootstrap,
    selectedAsset,
    selectedModel,
    setSelectedModel,
    prompt,
    setPrompt,
    events,
    history,
    setSelectedAssetId,
    runAgent,
  }
}
