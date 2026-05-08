'use client'

import { useCallback, useEffect, useMemo, useState } from 'react'
import { useParams } from 'next/navigation'
import { api } from '@/lib/api-client'
import type { Artifact, LatestReport, ProjectState } from '@/lib/api-types'
import { ResultDashboardPage } from '@/features/dashboard/result-dashboard-page'
import { buildDashboardSummary } from '@/features/dashboard/dashboard-data'

export default function DashboardPage() {
  const params = useParams<{ project_id: string }>()
  const projectId = params.project_id
  const [state, setState] = useState<ProjectState | null>(null)
  const [artifacts, setArtifacts] = useState<Artifact[]>([])
  const [report, setReport] = useState<LatestReport | null>(null)

  const loadDashboard = useCallback(async () => {
    try {
      const [stateResponse, artifactResponse, reportResponse] = await Promise.all([
        api.getProjectState(projectId),
        api.listArtifacts(projectId),
        api.getLatestReport(projectId),
      ])
      setState(stateResponse.ok && stateResponse.data ? stateResponse.data : null)
      setArtifacts(artifactResponse.ok && artifactResponse.data ? artifactResponse.data : [])
      setReport(reportResponse.ok && reportResponse.data ? reportResponse.data : null)
    } catch {
      setState(null)
      setArtifacts([])
      setReport(null)
    }
  }, [projectId])

  useEffect(() => {
    const timeout = window.setTimeout(() => {
      void loadDashboard()
    }, 0)

    return () => window.clearTimeout(timeout)
  }, [loadDashboard])

  const summary = useMemo(
    () => buildDashboardSummary({ state, artifacts, report }),
    [artifacts, report, state],
  )

  return <ResultDashboardPage summary={summary} />
}
