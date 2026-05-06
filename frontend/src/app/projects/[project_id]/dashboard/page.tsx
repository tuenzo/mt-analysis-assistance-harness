'use client'

import { useCallback, useEffect, useMemo, useState } from 'react'
import type { ReactNode } from 'react'
import Link from 'next/link'
import { useParams } from 'next/navigation'
import {
  Activity,
  ArrowRight,
  BarChart3,
  CheckCircle2,
  Clipboard,
  Database,
  FileText,
  Gauge,
  LineChart,
  Link2,
  RefreshCw,
  Scale,
  ShieldAlert,
  TableProperties,
  TrendingUp,
} from 'lucide-react'
import { api } from '@/lib/api-client'
import type { Artifact, LatestReport, ProjectState } from '@/lib/api-types'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { MarkdownView } from '@/components/markdown-view'

type ReportSection = {
  heading: string
  content: string
  level: number
}

type EvidenceStatus = 'complete' | 'partial' | 'pending'

type KpiTone = 'default' | 'good' | 'watch' | 'neutral'

export default function DashboardPage() {
  const params = useParams<{ project_id: string }>()
  const projectId = params.project_id
  const [state, setState] = useState<ProjectState | null>(null)
  const [artifacts, setArtifacts] = useState<Artifact[]>([])
  const [report, setReport] = useState<LatestReport | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [copiedArtifactId, setCopiedArtifactId] = useState<string | null>(null)

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
      setState(null)
    } else {
      setState(stateResponse.data)
    }

    setArtifacts(artifactResponse.ok && artifactResponse.data ? artifactResponse.data : [])
    setReport(reportResponse.ok && reportResponse.data ? reportResponse.data : null)
  }, [projectId])

  useEffect(() => {
    const timeout = setTimeout(() => {
      void loadDashboard()
    }, 0)
    return () => clearTimeout(timeout)
  }, [loadDashboard])

  const reportContent = report?.content ?? ''
  const sections = useMemo(() => parseMarkdownSections(reportContent), [reportContent])
  const executiveSection = useMemo(() => pickSection(sections, ['summary', 'conclusion', 'executive', 'one-page', 'one page', '摘要', '结论', '一页']), [sections])
  const localGapSection = useMemo(() => pickSection(sections, ['localgap', 'increment', 'decomposition', '增量', '分解']), [sections])
  const causalSection = useMemo(() => pickSection(sections, ['psm', 'did', 'causal', '因果']), [sections])
  const limitationItems = useMemo(() => buildLimitations(sections, artifacts, state, report), [artifacts, report, sections, state])
  const nextActions = useMemo(() => buildNextActions(projectId, state, artifacts, report), [artifacts, projectId, report, state])
  const kpis = useMemo(() => buildKpis(state, artifacts, reportContent), [artifacts, reportContent, state])
  const evidenceSteps = useMemo(() => buildEvidenceSteps(state, artifacts, report), [artifacts, report, state])
  const groupedArtifacts = useMemo(() => groupArtifacts(artifacts), [artifacts])
  const latestJob = state?.latest_jobs?.[0]

  async function copyArtifactPath(artifact: Artifact) {
    try {
      await navigator.clipboard.writeText(artifact.path)
      setCopiedArtifactId(artifact.id)
      window.setTimeout(() => setCopiedArtifactId(null), 1600)
    } catch {
      setCopiedArtifactId(null)
    }
  }

  return (
    <div className="container mx-auto max-w-7xl px-4 py-8 space-y-6">
      <div className="flex flex-col gap-4 lg:flex-row lg:items-start lg:justify-between">
        <div className="min-w-0">
          <div className="flex flex-wrap items-center gap-2">
            <h1 className="text-2xl font-semibold">Results Dashboard</h1>
            <Badge variant={report ? 'default' : 'secondary'}>{report ? 'report ready' : 'awaiting report'}</Badge>
            {latestJob?.status && <Badge variant="outline">{latestJob.status}</Badge>}
          </div>
          <p className="mt-2 max-w-3xl text-sm text-muted-foreground">
            A business-facing readout of KPIs, method evidence, artifacts, limitations, and the next decisions to make.
          </p>
        </div>
        <div className="flex flex-wrap gap-2">
          <Link href={`/projects/${projectId}/agent`}>
            <Button type="button" variant="outline">
              <Activity className="mr-2 h-4 w-4" />
              Agent
            </Button>
          </Link>
          <Link href={`/projects/${projectId}/reports`}>
            <Button type="button" variant="outline">
              <FileText className="mr-2 h-4 w-4" />
              Report Review
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
        {kpis.map((kpi) => (
          <KpiCard key={kpi.title} {...kpi} />
        ))}
      </div>

      <div className="grid gap-4 xl:grid-cols-[1.25fr_0.75fr]">
        <Card>
          <CardHeader className="pb-3">
            <div className="flex items-center justify-between gap-3">
              <div>
                <CardTitle className="text-base">Executive Readout</CardTitle>
                <CardDescription>What a business reviewer can act on first.</CardDescription>
              </div>
              <Badge variant={executiveSection ? 'default' : 'secondary'}>{executiveSection ? 'from report' : 'fallback'}</Badge>
            </div>
          </CardHeader>
          <CardContent>
            {loading && <p className="text-sm text-muted-foreground">Loading results...</p>}
            {!loading && executiveSection && (
              <MarkdownView content={executiveSection.content} className="rounded-md bg-secondary/30 p-4" />
            )}
            {!loading && !executiveSection && (
              <div className="rounded-md border bg-secondary/25 p-4">
                <p className="text-sm font-medium">No executive summary has been published yet.</p>
                <p className="mt-1 text-sm text-muted-foreground">
                  The dashboard can still show workspace coverage and generated artifacts. Ask the agent to run or refresh the full analysis pipeline when the input data is ready.
                </p>
              </div>
            )}
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="pb-3">
            <CardTitle className="text-base">Evidence Chain</CardTitle>
            <CardDescription>Data-to-decision coverage inferred from state and artifacts.</CardDescription>
          </CardHeader>
          <CardContent className="space-y-3">
            {evidenceSteps.map((step) => (
              <EvidenceRow key={step.label} {...step} />
            ))}
          </CardContent>
        </Card>
      </div>

      <div className="grid gap-4 xl:grid-cols-2">
        <ResultSection
          title="Increment Evidence"
          description="LocalGap or increment decomposition signals."
          content={localGapSection?.content ?? ''}
          empty="No increment decomposition section is available in the latest report."
          icon={<BarChart3 className="h-4 w-4" />}
        />
        <ResultSection
          title="Causal Direction"
          description="PSM-DID or other directional causal evidence."
          content={causalSection?.content ?? ''}
          empty="No causal direction section is available in the latest report."
          icon={<Scale className="h-4 w-4" />}
        />
      </div>

      <div className="grid gap-4 xl:grid-cols-[0.85fr_1.15fr]">
        <Card>
          <CardHeader className="pb-3">
            <CardTitle className="text-base">Limitations To Review</CardTitle>
            <CardDescription>Known gaps before this becomes decision-grade.</CardDescription>
          </CardHeader>
          <CardContent>
            <div className="space-y-3">
              {limitationItems.map((item) => (
                <div key={item} className="flex gap-3 rounded-md border px-3 py-3 text-sm">
                  <ShieldAlert className="mt-0.5 h-4 w-4 shrink-0 text-amber-600" />
                  <span>{item}</span>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="pb-3">
            <CardTitle className="text-base">Next Actions</CardTitle>
            <CardDescription>Practical handoffs for the next analysis turn.</CardDescription>
          </CardHeader>
          <CardContent className="space-y-3">
            {nextActions.map((action) => (
              <Link
                key={action.label}
                href={action.href}
                className="flex items-start justify-between gap-3 rounded-md border px-3 py-3 text-sm transition-colors hover:border-primary/50 hover:bg-secondary/30"
              >
                <div className="min-w-0">
                  <div className="font-medium">{action.label}</div>
                  <div className="mt-1 text-xs text-muted-foreground">{action.detail}</div>
                </div>
                <ArrowRight className="mt-0.5 h-4 w-4 shrink-0 text-muted-foreground" />
              </Link>
            ))}
          </CardContent>
        </Card>
      </div>

      <Card>
        <CardHeader className="pb-3">
          <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
            <div>
              <CardTitle className="text-base">Artifact Index</CardTitle>
              <CardDescription>Generated files that support the current readout.</CardDescription>
            </div>
            <Badge variant="outline">{artifacts.length} artifact{artifacts.length === 1 ? '' : 's'}</Badge>
          </div>
        </CardHeader>
        <CardContent>
          {artifacts.length === 0 ? (
            <p className="rounded-md border bg-secondary/25 p-4 text-sm text-muted-foreground">
              No generated artifacts are registered yet.
            </p>
          ) : (
            <div className="grid gap-4 xl:grid-cols-2">
              {Object.entries(groupedArtifacts).map(([group, items]) => (
                <div key={group} className="space-y-2">
                  <div className="flex items-center gap-2 text-xs font-semibold uppercase text-muted-foreground">
                    <Link2 className="h-3.5 w-3.5" />
                    {group}
                  </div>
                  <div className="space-y-2">
                    {items.map((artifact) => (
                      <ArtifactRow
                        key={artifact.id}
                        artifact={artifact}
                        projectId={projectId}
                        copied={copiedArtifactId === artifact.id}
                        onCopy={() => void copyArtifactPath(artifact)}
                      />
                    ))}
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

function KpiCard({
  title,
  value,
  detail,
  icon,
  tone,
}: {
  title: string
  value: string
  detail: string
  icon: ReactNode
  tone: KpiTone
}) {
  const toneClass = {
    default: 'bg-primary/10 text-primary',
    good: 'bg-green-500/10 text-green-700',
    watch: 'bg-amber-500/10 text-amber-700',
    neutral: 'bg-secondary text-muted-foreground',
  }[tone]

  return (
    <Card>
      <CardContent className="flex min-h-32 items-start justify-between gap-4 p-4">
        <div className="min-w-0">
          <p className="text-xs text-muted-foreground">{title}</p>
          <p className="mt-2 break-words text-xl font-semibold leading-tight">{value}</p>
          <p className="mt-2 text-xs leading-5 text-muted-foreground">{detail}</p>
        </div>
        <div className={`rounded-md p-2 ${toneClass}`}>{icon}</div>
      </CardContent>
    </Card>
  )
}

function EvidenceRow({
  label,
  detail,
  status,
}: {
  label: string
  detail: string
  status: EvidenceStatus
}) {
  const icon =
    status === 'complete' ? (
      <CheckCircle2 className="mt-0.5 h-4 w-4 shrink-0 text-green-600" />
    ) : status === 'partial' ? (
      <Activity className="mt-0.5 h-4 w-4 shrink-0 text-amber-600" />
    ) : (
      <Gauge className="mt-0.5 h-4 w-4 shrink-0 text-muted-foreground" />
    )
  const badgeVariant = status === 'complete' ? 'default' : status === 'partial' ? 'outline' : 'secondary'

  return (
    <div className="flex gap-3 rounded-md border px-3 py-3">
      {icon}
      <div className="min-w-0 flex-1">
        <div className="flex items-center justify-between gap-3">
          <p className="truncate text-sm font-medium">{label}</p>
          <Badge variant={badgeVariant}>{status}</Badge>
        </div>
        <p className="mt-1 text-xs leading-5 text-muted-foreground">{detail}</p>
      </div>
    </div>
  )
}

function ResultSection({
  title,
  description,
  content,
  empty,
  icon,
}: {
  title: string
  description: string
  content: string
  empty: string
  icon: ReactNode
}) {
  return (
    <Card>
      <CardHeader className="pb-3">
        <div className="flex items-start gap-3">
          <div className="rounded-md bg-primary/10 p-2 text-primary">{icon}</div>
          <div>
            <CardTitle className="text-base">{title}</CardTitle>
            <CardDescription>{description}</CardDescription>
          </div>
        </div>
      </CardHeader>
      <CardContent>
        {content ? (
          <MarkdownView content={content} className="rounded-md bg-secondary/30 p-4" />
        ) : (
          <p className="rounded-md border bg-secondary/25 p-4 text-sm text-muted-foreground">{empty}</p>
        )}
      </CardContent>
    </Card>
  )
}

function ArtifactRow({
  artifact,
  projectId,
  copied,
  onCopy,
}: {
  artifact: Artifact
  projectId: string
  copied: boolean
  onCopy: () => void
}) {
  const isReport = artifact.type === 'report' || artifact.path.toLowerCase().endsWith('.md')
  const metadata = parseArtifactMetadata(artifact.metadata_json)

  return (
    <div id={`artifact-${artifact.id}`} className="flex items-start justify-between gap-3 rounded-md border px-3 py-3">
      <div className="flex min-w-0 items-start gap-2">
        {artifact.type === 'chart' ? (
          <LineChart className="mt-0.5 h-4 w-4 shrink-0 text-primary" />
        ) : artifact.type === 'table' ? (
          <TableProperties className="mt-0.5 h-4 w-4 shrink-0 text-primary" />
        ) : (
          <FileText className="mt-0.5 h-4 w-4 shrink-0 text-primary" />
        )}
        <div className="min-w-0">
          {isReport ? (
            <Link href={`/projects/${projectId}/reports`} className="block truncate text-sm font-medium text-primary underline-offset-2 hover:underline">
              {artifact.title}
            </Link>
          ) : (
            <p className="truncate text-sm font-medium">{artifact.title}</p>
          )}
          <p className="mt-1 break-all font-mono text-xs text-muted-foreground">{artifact.path}</p>
          {metadata && <p className="mt-1 text-xs text-muted-foreground">{metadata}</p>}
        </div>
      </div>
      <div className="flex shrink-0 flex-col items-end gap-2">
        <Badge variant={artifact.type === 'report' ? 'default' : 'secondary'}>{artifact.type}</Badge>
        <button
          type="button"
          onClick={onCopy}
          className="inline-flex items-center gap-1 rounded-md border px-2 py-1 text-xs transition-colors hover:bg-secondary"
          title="Copy artifact path"
        >
          <Clipboard className="h-3.5 w-3.5" />
          {copied ? 'Copied' : 'Path'}
        </button>
        <span className="text-xs text-muted-foreground">{formatTime(artifact.created_at)}</span>
      </div>
    </div>
  )
}

function buildKpis(state: ProjectState | null, artifacts: Artifact[], reportContent: string) {
  const latestStatus = state?.latest_jobs?.[0]?.status
  const totalGmv = extractMetric(reportContent, [
    /total[_\s-]*gmv\s*[:=]\s*([0-9,.+-]+)/i,
    /total\s+gmv\s*[:=]\s*([0-9,.+-]+)/i,
    /总\s*GMV\s*[:：]\s*([0-9,.+-]+)/,
  ])
  const increment = extractMetric(reportContent, [
    /total[_\s-]*local[_\s-]*gap\s*[:=]\s*([0-9,.+-]+)/i,
    /localgap\s*[:=]\s*([0-9,.+-]+)/i,
    /总\s*增量\s*[:：]\s*([0-9,.+-]+)/,
  ])
  const didEstimate = extractMetric(reportContent, [
    /did[_\s-]*estimate\s*[:=]\s*([0-9,.+-]+)/i,
    /did\s*(?:estimate|effect)?\s*[:=]\s*([0-9,.+-]+)/i,
    /净效应\s*[:：]?\s*([0-9,.+-]+)/,
  ])

  return [
    {
      title: 'Analysis Stage',
      value: humanize(state?.current_stage || 'unknown'),
      detail: latestStatus ? `Latest job: ${humanize(latestStatus)}` : 'No recent pipeline job is registered.',
      icon: <Gauge className="h-4 w-4" />,
      tone: state?.current_stage === 'report_ready' ? 'good' as const : 'neutral' as const,
    },
    {
      title: 'Data Coverage',
      value: `${state?.files_count ?? 0} files`,
      detail: `${artifacts.length || state?.artifacts_count || 0} artifacts available for review.`,
      icon: <Database className="h-4 w-4" />,
      tone: (state?.files_count ?? 0) >= 3 ? 'good' as const : 'watch' as const,
    },
    {
      title: 'GMV Signal',
      value: totalGmv ? formatNumberText(totalGmv) : 'Not reported',
      detail: totalGmv ? 'Parsed from the latest report.' : 'Run diagnostics or refresh the report to expose this KPI.',
      icon: <TrendingUp className="h-4 w-4" />,
      tone: totalGmv ? 'default' as const : 'neutral' as const,
    },
    {
      title: 'Increment / DID',
      value: increment ? formatNumberText(increment) : didEstimate ? formatNumberText(didEstimate) : 'Pending',
      detail: increment ? 'LocalGap increment surfaced in report.' : didEstimate ? 'DID estimate surfaced in report.' : 'No increment or DID value found yet.',
      icon: <BarChart3 className="h-4 w-4" />,
      tone: increment || didEstimate ? 'default' as const : 'watch' as const,
    },
  ]
}

function buildEvidenceSteps(state: ProjectState | null, artifacts: Artifact[], report: LatestReport | null) {
  const filesCount = state?.files_count ?? 0
  const hasPanel = hasArtifact(artifacts, ['panel', 'category_day_panel', 'category_date_panel'])
  const hasDiagnostics = hasArtifact(artifacts, ['diagnostics', 'gmv_trend', 'category_concentration'])
  const hasCausal = hasArtifact(artifacts, ['psm', 'did', 'causal'])
  const hasLocalGap = hasArtifact(artifacts, ['localgap', 'local_gap'])
  const hasReport = Boolean(report)

  return [
    {
      label: 'Input data',
      status: filesCount >= 3 ? 'complete' as const : filesCount > 0 ? 'partial' as const : 'pending' as const,
      detail: filesCount >= 3 ? `${filesCount} registered files cover the expected intake set.` : `${filesCount} registered file${filesCount === 1 ? '' : 's'} found; order, exposure, and activity data may be incomplete.`,
    },
    {
      label: 'Panel build',
      status: hasPanel ? 'complete' as const : filesCount > 0 ? 'partial' as const : 'pending' as const,
      detail: hasPanel ? 'A category-day panel artifact is available.' : 'No panel artifact is registered in the current artifact index.',
    },
    {
      label: 'Diagnostics',
      status: hasDiagnostics ? 'complete' as const : hasPanel ? 'partial' as const : 'pending' as const,
      detail: hasDiagnostics ? 'Trend, concentration, or diagnostics artifacts are available.' : 'Descriptive evidence has not been surfaced as an artifact yet.',
    },
    {
      label: 'Causal direction',
      status: hasCausal ? 'complete' as const : hasDiagnostics ? 'partial' as const : 'pending' as const,
      detail: hasCausal ? 'A PSM-DID or causal-direction artifact is available.' : 'Treat causal claims as directional until a method artifact is registered.',
    },
    {
      label: 'Increment decomposition',
      status: hasLocalGap ? 'complete' as const : hasDiagnostics ? 'partial' as const : 'pending' as const,
      detail: hasLocalGap ? 'LocalGap evidence is available for contribution review.' : 'No LocalGap artifact is registered yet.',
    },
    {
      label: 'Report and handoff',
      status: hasReport ? 'complete' as const : hasLocalGap ? 'partial' as const : 'pending' as const,
      detail: hasReport ? 'The latest Markdown report is ready for review.' : 'Generate a report after the core analysis artifacts are ready.',
    },
  ]
}

function buildLimitations(
  sections: ReportSection[],
  artifacts: Artifact[],
  state: ProjectState | null,
  report: LatestReport | null,
) {
  const limitationSection = pickSection(sections, ['limitation', 'limits', 'caveat', 'assumption', 'risk', '局限', '假设', '风险'])
  const fromReport = limitationSection ? extractBullets(limitationSection.content).slice(0, 4) : []
  if (fromReport.length > 0) return fromReport

  const items: string[] = []
  if ((state?.files_count ?? 0) < 3) {
    items.push('The expected order, exposure, and activity timeline files are not all registered yet.')
  }
  if (!hasArtifact(artifacts, ['psm', 'did', 'causal'])) {
    items.push('No causal-direction artifact is registered, so lift claims should stay directional.')
  }
  if (!hasArtifact(artifacts, ['localgap', 'local_gap'])) {
    items.push('No LocalGap artifact is registered, so increment attribution is not yet auditable.')
  }
  if (!report) {
    items.push('No latest report is available, so conclusions have not been packaged for business review.')
  }
  if (items.length === 0) {
    items.push('Current outputs should still be checked for margin, stockout, campaign calendar, and retention controls before production decisions.')
  }
  return items.slice(0, 4)
}

function buildNextActions(projectId: string, state: ProjectState | null, artifacts: Artifact[], report: LatestReport | null) {
  if ((state?.files_count ?? 0) === 0) {
    return [
      {
        label: 'Import source CSVs',
        detail: 'Start with order, exposure, and activity timeline data.',
        href: `/projects/${projectId}/data-intake`,
      },
      {
        label: 'Ask the agent to validate schema',
        detail: 'Route the next natural-language request through the message runtime.',
        href: `/projects/${projectId}/agent`,
      },
    ]
  }

  if (!hasArtifact(artifacts, ['panel', 'category_day_panel', 'category_date_panel'])) {
    return [
      {
        label: 'Build the category-day panel',
        detail: 'Ask the agent to run panel.build_category_day after schema checks.',
        href: `/projects/${projectId}/agent`,
      },
      {
        label: 'Review data intake',
        detail: 'Confirm each file role before analysis runs.',
        href: `/projects/${projectId}/data-intake`,
      },
    ]
  }

  if (!report) {
    return [
      {
        label: 'Generate a business report',
        detail: 'Ask the agent for an approved full pipeline or report refresh.',
        href: `/projects/${projectId}/agent`,
      },
      {
        label: 'Inspect run history',
        detail: 'Check jobs, approvals, and tool outputs for blockers.',
        href: `/projects/${projectId}/timeline`,
      },
    ]
  }

  return [
    {
      label: 'Review the full report',
      detail: 'Use the report review page to inspect claims, evidence, and gaps.',
      href: `/projects/${projectId}/reports`,
    },
    {
      label: 'Check the timeline',
      detail: 'Confirm which approved jobs produced the displayed outputs.',
      href: `/projects/${projectId}/timeline`,
    },
    {
      label: 'Promote durable conclusions',
      detail: 'Review memory candidates before keeping project-level takeaways.',
      href: `/projects/${projectId}/memory`,
    },
  ]
}

function groupArtifacts(artifacts: Artifact[]) {
  return artifacts.reduce<Record<string, Artifact[]>>((groups, artifact) => {
    const group = artifactGroupLabel(artifact)
    groups[group] = groups[group] ?? []
    groups[group].push(artifact)
    return groups
  }, {})
}

function artifactGroupLabel(artifact: Artifact) {
  const key = `${artifact.type} ${artifact.path} ${artifact.title}`.toLowerCase()
  if (key.includes('report')) return 'Reports'
  if (key.includes('chart') || key.includes('trend')) return 'Charts'
  if (key.includes('table') || key.includes('.csv')) return 'Tables'
  if (key.includes('localgap') || key.includes('diagnostics') || key.includes('psm') || key.includes('panel')) return 'Analysis outputs'
  return 'Other artifacts'
}

function hasArtifact(artifacts: Artifact[], needles: string[]) {
  return artifacts.some((artifact) => {
    const haystack = `${artifact.type} ${artifact.title} ${artifact.path}`.toLowerCase()
    return needles.some((needle) => haystack.includes(needle.toLowerCase()))
  })
}

function parseMarkdownSections(content: string): ReportSection[] {
  if (!content.trim()) return []
  const lines = content.split(/\r?\n/)
  const sections: ReportSection[] = []
  let current: ReportSection | null = null

  for (const line of lines) {
    const match = /^(#{1,3})\s+(.+?)\s*$/.exec(line.trim())
    if (match) {
      if (current) sections.push(current)
      current = {
        heading: match[2],
        level: match[1].length,
        content: line,
      }
      continue
    }

    if (current) {
      current.content += `\n${line}`
    }
  }

  if (current) sections.push(current)
  if (sections.length === 0) {
    return [{ heading: 'Latest report', level: 1, content }]
  }
  return sections
}

function pickSection(sections: ReportSection[], keywords: string[]) {
  const normalized = keywords.map((keyword) => keyword.toLowerCase())
  return sections.find((section) => {
    const heading = section.heading.toLowerCase()
    return normalized.some((keyword) => heading.includes(keyword))
  })
}

function extractBullets(content: string) {
  return content
    .split(/\r?\n/)
    .map((line) => line.trim())
    .filter((line) => /^[-*]\s+/.test(line) || /^\d+\.\s+/.test(line))
    .map((line) => line.replace(/^[-*]\s+/, '').replace(/^\d+\.\s+/, '').replace(/\*\*/g, '').trim())
    .filter(Boolean)
}

function extractMetric(content: string, patterns: RegExp[]) {
  for (const pattern of patterns) {
    const match = content.match(pattern)
    if (match?.[1]) return match[1]
  }
  return ''
}

function parseArtifactMetadata(value?: string) {
  if (!value) return ''
  try {
    const parsed = JSON.parse(value) as Record<string, unknown>
    const labels = Object.entries(parsed)
      .filter(([, item]) => typeof item === 'string' || typeof item === 'number' || typeof item === 'boolean')
      .slice(0, 2)
      .map(([key, item]) => `${humanize(key)}: ${String(item)}`)
    return labels.join(' | ')
  } catch {
    return ''
  }
}

function formatNumberText(value: string) {
  const cleaned = value.replace(/,/g, '')
  const parsed = Number(cleaned)
  if (!Number.isFinite(parsed)) return value
  return new Intl.NumberFormat(undefined, { maximumFractionDigits: 2 }).format(parsed)
}

function humanize(value: string) {
  return value
    .replace(/[_-]+/g, ' ')
    .replace(/\s+/g, ' ')
    .trim()
    .replace(/\b\w/g, (letter) => letter.toUpperCase()) || 'Unknown'
}

function formatTime(value: string) {
  const date = new Date(value)
  if (Number.isNaN(date.getTime())) return '--'
  return date.toLocaleDateString(undefined, { month: 'short', day: 'numeric' })
}
