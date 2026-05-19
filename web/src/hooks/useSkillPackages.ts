import { useCallback, useState } from 'react'
import { getSkills } from '../api'
import type { SkillPackage } from '../types/ops'

let cachedSkillPackages: SkillPackage[] | null = null
let pendingSkillPackagesRequest: Promise<SkillPackage[]> | null = null

export function useSkillPackages() {
  const [skillPackages, setSkillPackages] = useState<SkillPackage[] | null>(cachedSkillPackages)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const loadSkillPackages = useCallback(async (forceRefresh = false) => {
    if (!forceRefresh && cachedSkillPackages) {
      setSkillPackages(cachedSkillPackages)
      setError(null)
      return cachedSkillPackages
    }

    if (!forceRefresh && pendingSkillPackagesRequest) {
      setLoading(true)
      try {
        const packages = await pendingSkillPackagesRequest
        setSkillPackages(packages)
        setError(null)
        return packages
      } finally {
        setLoading(false)
      }
    }

    setLoading(true)
    setError(null)
    const request = getSkills()
    pendingSkillPackagesRequest = request

    try {
      const packages = await request
      cachedSkillPackages = packages
      setSkillPackages(packages)
      return packages
    } catch (loadError) {
      setError(loadError instanceof Error ? loadError.message : 'Failed to load skills')
      setSkillPackages([])
      return []
    } finally {
      if (pendingSkillPackagesRequest === request) {
        pendingSkillPackagesRequest = null
      }
      setLoading(false)
    }
  }, [])

  return { skillPackages, loading, error, loadSkillPackages }
}
