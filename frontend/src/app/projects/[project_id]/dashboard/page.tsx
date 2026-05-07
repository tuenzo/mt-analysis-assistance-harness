'use client'

import { useCallback, useEffect, useMemo, useState } from 'react'
import { useParams } from 'next/navigation'
import { api } from '@/lib/api-client'
import type { Artifact, LatestReport, ProjectState } from '@/lib/api-types'
import { CampaignResultDashboard } from '@/features/dashboard/campaign-result-dashboard'
import { buildCampaignDashboardSnapshot } from '@/features/dashboard/campaign-snapshot'

export default function DashboardPage() {
  const params = useParams<{ project_id: string }>()
  const projectId = params.project_id
  const [state, setState] = useState<ProjectState | null>(null)
  const [artifacts, setArtifacts] = useState<Artifact[]>([])
  const [report, setReport] = useState<LatestReport | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  const loadDashboard = useCallback(async () => {
    setLoading(true)
    setError(null)

    try {
      const [stateResponse, artifactResponse, reportResponse] = await Promise.all([
        api.getProjectState(projectId),
        api.listArtifacts(projectId),
        api.getLatestReport(projectId),
      ])

      if (!stateResponse.ok || !stateResponse.data) {
        setState(null)
        setError(stateResponse.error || 'Unable to load project state.')
      } else {
        setState(stateResponse.data)
      }

      setArtifacts(artifactResponse.ok && artifactResponse.data ? artifactResponse.data : [])
      setReport(reportResponse.ok && reportResponse.data ? reportResponse.data : null)
    } catch (loadError) {
      setState(null)
      setArtifacts([])
      setReport(null)
      setError(loadError instanceof Error ? loadError.message : 'Unable to load dashboard data.')
    } finally {
      setLoading(false)
    }
  }, [projectId])

  useEffect(() => {
    const timeout = window.setTimeout(() => {
      void loadDashboard()
    }, 0)

    return () => window.clearTimeout(timeout)
  }, [loadDashboard])

  const snapshot = useMemo(
    () => buildCampaignDashboardSnapshot({ state, artifacts, report }),
    [artifacts, report, state]
  )

  return (
    <CampaignResultDashboard
      projectId={projectId}
      snapshot={snapshot}
      state={state}
      artifacts={artifacts}
      latestReport={report}
      loading={loading}
      error={error}
      onRefresh={loadDashboard}
    />
  )
}
