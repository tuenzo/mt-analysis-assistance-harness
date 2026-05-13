'use client'

import { useCallback, useEffect, useMemo, useState } from 'react'
import { useParams } from 'next/navigation'
import { api } from '@/lib/api-client'
import type { Artifact, LatestReport, ProjectState } from '@/lib/api-types'
import { ResultDashboardPage } from '@/features/dashboard/result-dashboard-page'
import {
  buildDashboardInitialFilters,
  buildDashboardSummary,
  buildDashboardTimeRangeLabel,
} from '@/features/dashboard/dashboard-data'
import { isKeemartPromoProject } from '@/features/demo/keemart-demo-data'
import { KeemartDemoDashboardPage } from '@/features/demo/keemart-demo-dashboard-page'

export default function DashboardPage() {
  const params = useParams<{ project_id: string }>()
  const projectId = params.project_id

  if (isKeemartPromoProject(projectId)) {
    return <KeemartDemoDashboardPage />
  }

  return <ApiBackedDashboardPage projectId={projectId} />
}

function ApiBackedDashboardPage({ projectId }: { projectId: string }) {
  const [state, setState] = useState<ProjectState | null>(null)
  const [artifacts, setArtifacts] = useState<Artifact[]>([])
  const [report, setReport] = useState<LatestReport | null>(null)
  const [latestResult, setLatestResult] = useState<unknown>(null)
  const [panelSummary, setPanelSummary] = useState<unknown>(null)

  const loadDashboard = useCallback(async () => {
    try {
      const [stateResponse, artifactResponse, reportResponse, latestResultResponse, panelSummaryResponse] = await Promise.all([
        api.getProjectState(projectId),
        api.listArtifacts(projectId),
        api.getLatestReport(projectId),
        api.getArtifactContentByPath(projectId, '.analysis/latest_result.json'),
        api.getArtifactContentByPath(projectId, '.analysis/panel_summary.json'),
      ])
      setState(stateResponse.ok && stateResponse.data ? stateResponse.data : null)
      setArtifacts(artifactResponse.ok && artifactResponse.data ? artifactResponse.data : [])
      setReport(reportResponse.ok && reportResponse.data ? reportResponse.data : null)
      setLatestResult(latestResultResponse.ok && latestResultResponse.data?.encoding === 'json' ? latestResultResponse.data.data : null)
      setPanelSummary(panelSummaryResponse.ok && panelSummaryResponse.data?.encoding === 'json' ? panelSummaryResponse.data.data : null)
    } catch {
      setState(null)
      setArtifacts([])
      setReport(null)
      setLatestResult(null)
      setPanelSummary(null)
    }
  }, [projectId])

  useEffect(() => {
    const timeout = window.setTimeout(() => {
      void loadDashboard()
    }, 0)

    return () => window.clearTimeout(timeout)
  }, [loadDashboard])

  const summary = useMemo(
    () => buildDashboardSummary({ state, artifacts, report, latestResult, panelSummary }),
    [artifacts, latestResult, panelSummary, report, state],
  )
  const initialFilters = useMemo(() => buildDashboardInitialFilters(summary), [summary])
  const timeRangeLabel = useMemo(() => buildDashboardTimeRangeLabel(summary), [summary])

  return (
    <ResultDashboardPage
      key={timeRangeLabel}
      summary={summary}
      initialFilters={initialFilters}
      timeRangeLabel={timeRangeLabel}
      preserveLocalGap
    />
  )
}
