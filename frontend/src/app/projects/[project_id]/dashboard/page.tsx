'use client'

import { useCallback, useEffect, useMemo, useState } from 'react'
import type { ReactNode } from 'react'
import Link from 'next/link'
import { useParams } from 'next/navigation'
import {
  Activity,
  BarChart3,
  FileText,
  Gauge,
  Layers,
  RefreshCw,
  TableProperties,
  TrendingUp,
} from 'lucide-react'
import { api } from '@/lib/api-client'
import type { Artifact, LatestReport, ProjectState } from '@/lib/api-types'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { MarkdownView } from '@/components/markdown-view'

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
    const [stateResponse, artifactResponse, reportResponse] = await Promise.all([
      api.getProjectState(projectId),
      api.listArtifacts(projectId),
      api.getLatestReport(projectId),
    ])
    setLoading(false)

    if (!stateResponse.ok || !stateResponse.data) {
      setError(stateResponse.error || 'Failed to load dashboard state.')
      return
    }
    setState(stateResponse.data)
    setArtifacts(artifactResponse.ok && artifactResponse.data ? artifactResponse.data : [])
    setReport(reportResponse.ok && reportResponse.data ? reportResponse.data : null)
  }, [projectId])

  useEffect(() => {
    const timeout = setTimeout(() => {
      void loadDashboard()
    }, 0)
    return () => clearTimeout(timeout)
  }, [loadDashboard])

  const latestJob = state?.latest_jobs?.[0]
  const reportContent = report?.content || ''
  const executiveSummary = useMemo(() => sectionMarkdown(reportContent, '摘要'), [reportContent])
  const localGapSection = useMemo(() => sectionMarkdown(reportContent, '增量分解'), [reportContent])
  const categorySection = useMemo(() => sectionMarkdown(reportContent, '品类集中度'), [reportContent])
  const metrics = useMemo(
    () => buildMetrics({
      state,
      latestJobStatus: latestJob?.status,
      artifacts,
      reportContent,
    }),
    [artifacts, latestJob?.status, reportContent, state]
  )

  return (
    <div className="container mx-auto max-w-7xl px-4 py-8 space-y-6">
      <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <h1 className="text-2xl font-semibold">Results Dashboard</h1>
          <p className="text-sm text-muted-foreground">核心指标、报告结论和产物状态在这里直接查看。</p>
        </div>
        <div className="flex gap-2">
          <Link href={`/projects/${projectId}/reports`}>
            <Button type="button" variant="outline">
              <FileText className="mr-2 h-4 w-4" />
              Full Report
            </Button>
          </Link>
          <Button type="button" variant="outline" onClick={loadDashboard} disabled={loading}>
            <RefreshCw className={`mr-2 h-4 w-4 ${loading ? 'animate-spin' : ''}`} />
            Refresh
          </Button>
        </div>
      </div>

      {error && (
        <div className="rounded-md border border-destructive/30 bg-destructive/10 px-3 py-2 text-sm text-destructive">
          {error}
        </div>
      )}

      <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
        <MetricCard
          title="Current Stage"
          value={metrics.stage}
          hint="Project state"
          icon={<Gauge className="h-4 w-4" />}
        />
        <MetricCard
          title="Pipeline"
          value={metrics.pipelineStatus}
          hint="Latest job"
          icon={<Activity className="h-4 w-4" />}
        />
        <MetricCard
          title="Total GMV"
          value={metrics.totalGmv}
          hint="From latest report"
          icon={<TrendingUp className="h-4 w-4" />}
        />
        <MetricCard
          title="LocalGap"
          value={metrics.localGap}
          hint="Increment estimate"
          icon={<BarChart3 className="h-4 w-4" />}
        />
      </div>

      <div className="grid gap-4 xl:grid-cols-[1.25fr_0.75fr]">
        <Card>
          <CardHeader className="pb-3">
            <div className="flex items-center justify-between gap-3">
              <CardTitle className="text-base">Executive Snapshot</CardTitle>
              <Badge variant={report ? 'default' : 'secondary'}>{report ? 'report ready' : 'no report'}</Badge>
            </div>
          </CardHeader>
          <CardContent>
            {loading && <p className="text-sm text-muted-foreground">Loading results...</p>}
            {!loading && report && (
              <MarkdownView
                content={executiveSummary || reportContent.slice(0, 1200)}
                className="rounded-md bg-secondary/30 p-4"
              />
            )}
            {!loading && !report && (
              <p className="rounded-md bg-secondary/40 p-4 text-sm text-muted-foreground">
                No report is available yet. Run the approved analysis pipeline to populate this summary.
              </p>
            )}
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="pb-3">
            <CardTitle className="text-base">Result Coverage</CardTitle>
          </CardHeader>
          <CardContent className="space-y-3">
            <CoverageRow label="Files" value={String(state?.files_count ?? 0)} />
            <CoverageRow label="Artifacts" value={String(artifacts.length || state?.artifacts_count || 0)} />
            <CoverageRow label="Charts" value={String(artifacts.filter((artifact) => artifact.type === 'chart').length)} />
            <CoverageRow label="Reports" value={String(state?.reports_count ?? (report ? 1 : 0))} />
            <div className="rounded-md border bg-secondary/25 px-3 py-2 text-xs text-muted-foreground">
              Latest activity: {state?.last_activity ? new Date(state.last_activity).toLocaleString() : '--'}
            </div>
          </CardContent>
        </Card>
      </div>

      <div className="grid gap-4 xl:grid-cols-2">
        <ResultSection
          title="Increment Decomposition"
          empty="No LocalGap section found in the latest report."
          content={localGapSection}
        />
        <ResultSection
          title="Category Concentration"
          empty="No category section found in the latest report."
          content={categorySection}
        />
      </div>

      <Card>
        <CardHeader className="pb-3">
          <div className="flex items-center justify-between gap-3">
            <CardTitle className="text-base">Latest Artifacts</CardTitle>
            <Badge variant="outline">{artifacts.length}</Badge>
          </div>
        </CardHeader>
        <CardContent>
          {artifacts.length === 0 ? (
            <p className="text-sm text-muted-foreground">No generated artifacts yet.</p>
          ) : (
            <div className="grid gap-2 lg:grid-cols-2">
              {artifacts.slice(0, 10).map((artifact) => (
                <div key={artifact.id} className="flex items-start justify-between gap-3 rounded-md border px-3 py-2">
                  <div className="flex min-w-0 items-start gap-2">
                    <TableProperties className="mt-0.5 h-4 w-4 shrink-0 text-muted-foreground" />
                    <div className="min-w-0">
                      <div className="truncate text-sm font-medium">{artifact.title}</div>
                      <div className="truncate text-xs text-muted-foreground">{artifact.path}</div>
                    </div>
                  </div>
                  <div className="flex shrink-0 flex-col items-end gap-1">
                    <Badge variant={artifact.type === 'report' ? 'default' : 'secondary'}>{artifact.type}</Badge>
                    <span className="text-xs text-muted-foreground">{formatTime(artifact.created_at)}</span>
                  </div>
                </div>
              ))}
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  )
}

function MetricCard({
  title,
  value,
  hint,
  icon,
}: {
  title: string
  value: string
  hint: string
  icon: ReactNode
}) {
  return (
    <Card>
      <CardContent className="flex items-center justify-between gap-4 p-4">
        <div className="min-w-0">
          <p className="text-xs text-muted-foreground">{title}</p>
          <p className="mt-1 truncate text-xl font-semibold">{value}</p>
          <p className="mt-1 text-xs text-muted-foreground">{hint}</p>
        </div>
        <div className="rounded-md bg-primary/10 p-2 text-primary">{icon}</div>
      </CardContent>
    </Card>
  )
}

function CoverageRow({ label, value }: { label: string; value: string }) {
  return (
    <div className="flex items-center justify-between rounded-md border px-3 py-2">
      <div className="flex items-center gap-2 text-sm">
        <Layers className="h-4 w-4 text-muted-foreground" />
        {label}
      </div>
      <span className="font-semibold">{value}</span>
    </div>
  )
}

function ResultSection({ title, content, empty }: { title: string; content: string; empty: string }) {
  return (
    <Card>
      <CardHeader className="pb-3">
        <CardTitle className="text-base">{title}</CardTitle>
      </CardHeader>
      <CardContent>
        {content ? (
          <MarkdownView content={content} className="rounded-md bg-secondary/30 p-4" />
        ) : (
          <p className="rounded-md bg-secondary/40 p-4 text-sm text-muted-foreground">{empty}</p>
        )}
      </CardContent>
    </Card>
  )
}

function buildMetrics({
  state,
  latestJobStatus,
  artifacts,
  reportContent,
}: {
  state: ProjectState | null
  latestJobStatus?: string
  artifacts: Artifact[]
  reportContent: string
}) {
  return {
    stage: state?.current_stage || 'loading',
    pipelineStatus: latestJobStatus || 'none',
    totalGmv: extractValue(reportContent, [/总\s*GMV[:：]\s*([0-9,.]+)/, /Total\s+GMV[:：]\s*([0-9,.]+)/i]) || '--',
    localGap: extractValue(reportContent, [/总增量[:：]\s*([0-9,.+-]+)/, /LocalGap[:：]\s*([0-9,.+-]+)/i]) || '--',
    artifactCount: String(artifacts.length),
  }
}

function extractValue(content: string, patterns: RegExp[]) {
  for (const pattern of patterns) {
    const match = content.match(pattern)
    if (match?.[1]) return match[1]
  }
  return ''
}

function sectionMarkdown(content: string, heading: string) {
  if (!content) return ''
  const lines = content.split(/\r?\n/)
  const start = lines.findIndex((line) => {
    const trimmed = line.trim()
    return trimmed.startsWith('##') && trimmed.includes(heading)
  })
  if (start < 0) return ''
  const end = lines.findIndex((line, index) => index > start && /^##\s+/.test(line.trim()))
  return lines.slice(start, end > start ? end : undefined).join('\n').trim()
}

function formatTime(value: string) {
  const date = new Date(value)
  if (Number.isNaN(date.getTime())) return '--'
  return date.toLocaleTimeString()
}
