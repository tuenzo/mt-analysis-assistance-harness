'use client'

import { useEffect, useState } from 'react'
import type { ReactNode } from 'react'
import Link from 'next/link'
import { useParams } from 'next/navigation'
import { BarChart3, FileText, RefreshCw, TableProperties } from 'lucide-react'
import { api } from '@/lib/api-client'
import type { Artifact, ProjectState } from '@/lib/api-types'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'

export default function DashboardPage() {
  const params = useParams<{ project_id: string }>()
  const projectId = params.project_id
  const [state, setState] = useState<ProjectState | null>(null)
  const [artifacts, setArtifacts] = useState<Artifact[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  async function loadDashboard() {
    setLoading(true)
    setError(null)
    const [stateResponse, artifactResponse] = await Promise.all([
      api.getProjectState(projectId),
      api.listArtifacts(projectId),
    ])
    setLoading(false)

    if (!stateResponse.ok || !stateResponse.data) {
      setError(stateResponse.error || 'Failed to load dashboard state.')
      return
    }
    setState(stateResponse.data)
    setArtifacts(artifactResponse.ok && artifactResponse.data ? artifactResponse.data : [])
  }

  useEffect(() => {
    void loadDashboard()
  }, [projectId])

  const latestJob = state?.latest_jobs?.[0]
  const chartCount = artifacts.filter((artifact) => artifact.type === 'chart').length
  const reportCount = artifacts.filter((artifact) => artifact.type === 'report').length

  return (
    <div className="container mx-auto max-w-6xl px-4 py-8 space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-semibold">Results Dashboard</h1>
          <p className="text-sm text-muted-foreground">Latest pipeline status and generated analysis outputs.</p>
        </div>
        <Button type="button" variant="outline" onClick={loadDashboard} disabled={loading}>
          <RefreshCw className={`mr-2 h-4 w-4 ${loading ? 'animate-spin' : ''}`} />
          Refresh
        </Button>
      </div>

      {error && (
        <div className="rounded-md border border-destructive/30 bg-destructive/10 px-3 py-2 text-sm text-destructive">
          {error}
        </div>
      )}

      <div className="grid gap-4 md:grid-cols-4">
        <MetricCard title="Stage" value={state?.current_stage || 'loading'} icon={<BarChart3 className="h-4 w-4" />} />
        <MetricCard title="Latest Job" value={latestJob?.status || 'none'} icon={<RefreshCw className="h-4 w-4" />} />
        <MetricCard title="Charts" value={String(chartCount)} icon={<BarChart3 className="h-4 w-4" />} />
        <MetricCard title="Reports" value={String(reportCount || state?.reports_count || 0)} icon={<FileText className="h-4 w-4" />} />
      </div>

      <div className="grid gap-4 lg:grid-cols-[1.4fr_1fr]">
        <Card>
          <CardHeader>
            <CardTitle className="text-base">Generated Artifacts</CardTitle>
          </CardHeader>
          <CardContent>
            {artifacts.length === 0 ? (
              <p className="text-sm text-muted-foreground">No generated artifacts yet.</p>
            ) : (
              <div className="space-y-2">
                {artifacts.slice(0, 12).map((artifact) => (
                  <div key={artifact.id} className="flex items-center justify-between rounded-md border px-3 py-2">
                    <div className="flex min-w-0 items-center gap-2">
                      <TableProperties className="h-4 w-4 text-muted-foreground" />
                      <div className="min-w-0">
                        <div className="truncate text-sm font-medium">{artifact.title}</div>
                        <div className="truncate text-xs text-muted-foreground">{artifact.type} · {artifact.path}</div>
                      </div>
                    </div>
                    <span className="text-xs text-muted-foreground">{new Date(artifact.created_at).toLocaleTimeString()}</span>
                  </div>
                ))}
              </div>
            )}
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle className="text-base">Report</CardTitle>
          </CardHeader>
          <CardContent className="space-y-3">
            <p className="text-sm text-muted-foreground">
              {state?.latest_report
                ? 'The latest generated report is ready for review.'
                : 'Run the approved pipeline to generate a report.'}
            </p>
            <Link href={`/projects/${projectId}/reports`} className="block">
              <Button className="w-full">
                <FileText className="mr-2 h-4 w-4" />
                Open Report
              </Button>
            </Link>
          </CardContent>
        </Card>
      </div>
    </div>
  )
}

function MetricCard({ title, value, icon }: { title: string; value: string; icon: ReactNode }) {
  return (
    <Card>
      <CardContent className="flex items-center justify-between p-4">
        <div>
          <p className="text-xs text-muted-foreground">{title}</p>
          <p className="mt-1 text-lg font-semibold">{value}</p>
        </div>
        <div className="rounded-md bg-primary/10 p-2 text-primary">{icon}</div>
      </CardContent>
    </Card>
  )
}
