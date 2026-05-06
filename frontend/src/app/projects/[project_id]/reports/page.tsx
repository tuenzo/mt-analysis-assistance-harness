'use client'

import { useCallback, useEffect, useMemo, useState } from 'react'
import type { ReactNode } from 'react'
import Link from 'next/link'
import { useParams } from 'next/navigation'
import {
  ArrowRight,
  CheckCircle2,
  Clipboard,
  Download,
  FileCheck2,
  FileText,
  Gauge,
  Link2,
  ListChecks,
  RefreshCw,
  ShieldAlert,
  TableProperties,
  XCircle,
} from 'lucide-react'
import { api } from '@/lib/api-client'
import type { ApiResponse, Artifact, LatestReport, ProjectState } from '@/lib/api-types'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { MarkdownView } from '@/components/markdown-view'

type ReportSection = {
  heading: string
  content: string
  level: number
}

type QualityStatus = 'ready' | 'review' | 'missing'

type ExportState = {
  type: 'success' | 'error'
  message: string
} | null

export default function ReportsPage() {
  const params = useParams<{ project_id: string }>()
  const projectId = params.project_id
  const [report, setReport] = useState<LatestReport | null>(null)
  const [state, setState] = useState<ProjectState | null>(null)
  const [artifacts, setArtifacts] = useState<Artifact[]>([])
  const [activeSectionIndex, setActiveSectionIndex] = useState(0)
  const [loading, setLoading] = useState(true)
  const [generating, setGenerating] = useState(false)
  const [exporting, setExporting] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [notice, setNotice] = useState<string | null>(null)
  const [exportState, setExportState] = useState<ExportState>(null)
  const [copiedValue, setCopiedValue] = useState<string | null>(null)

  const loadReport = useCallback(async () => {
    setLoading(true)
    setError(null)
    setNotice(null)
    setExportState(null)
    const [reportResponse, stateResponse, artifactResponse] = await Promise.all([
      api.getLatestReport(projectId),
      api.getProjectState(projectId),
      api.listArtifacts(projectId),
    ])
    setLoading(false)

    if (reportResponse.ok && reportResponse.data) {
      setReport(reportResponse.data)
      setActiveSectionIndex(0)
    } else {
      setReport(null)
      setNotice(reportResponse.error || 'No latest report is available yet.')
    }

    if (stateResponse.ok && stateResponse.data) {
      setState(stateResponse.data)
    } else {
      setState(null)
    }

    if (artifactResponse.ok && artifactResponse.data) {
      setArtifacts(artifactResponse.data)
    } else {
      setArtifacts([])
    }

    const supportErrors = [stateResponse, artifactResponse]
      .filter((response) => !response.ok)
      .map((response) => response.error)
      .filter(Boolean)
    if (supportErrors.length > 0) {
      setError(`Report loaded with limited context: ${supportErrors.join('; ')}`)
    }
  }, [projectId])

  useEffect(() => {
    const timeout = setTimeout(() => {
      void loadReport()
    }, 0)
    return () => clearTimeout(timeout)
  }, [loadReport])

  const reportContent = report?.content ?? ''
  const sections = useMemo(() => parseMarkdownSections(reportContent), [reportContent])
  const activeSection = sections[Math.min(activeSectionIndex, Math.max(sections.length - 1, 0))]
  const reportTitle = useMemo(() => extractReportTitle(reportContent) || 'Latest Analysis Report', [reportContent])
  const qualityCues = useMemo(() => buildQualityCues(sections, artifacts, report, state), [artifacts, report, sections, state])
  const reviewNotes = useMemo(() => buildReviewNotes(sections, artifacts, report, state), [artifacts, report, sections, state])
  const referencedArtifacts = useMemo(() => rankReportArtifacts(artifacts), [artifacts])
  const metadata = useMemo(() => buildMetadata(report, state, artifacts), [artifacts, report, state])

  async function exportMarkdown() {
    setExporting(true)
    setExportState(null)
    const response = await api.exportReport(projectId, '', 'md')
    setExporting(false)

    if (!response.ok) {
      setExportState({ type: 'error', message: response.error || 'Markdown export failed.' })
      return
    }

    setExportState({ type: 'success', message: summarizeExportResponse(response) })
  }

  async function generateReport() {
    setGenerating(true)
    setError(null)
    setNotice(null)
    setExportState(null)
    const response = await api.generateReport(projectId, 'md')
    setGenerating(false)

    if (!response.ok) {
      setError(normalizeError(response.error, 'Report generation failed.'))
      return
    }

    await loadReport()
    setNotice('Report regenerated from the latest workspace artifacts.')
  }

  async function copyValue(value: string, key: string) {
    try {
      await navigator.clipboard.writeText(value)
      setCopiedValue(key)
      window.setTimeout(() => setCopiedValue(null), 1600)
    } catch {
      setCopiedValue(null)
    }
  }

  return (
    <div className="container mx-auto max-w-7xl px-4 py-8 space-y-6">
      <div className="flex flex-col gap-4 lg:flex-row lg:items-start lg:justify-between">
        <div className="min-w-0">
          <div className="flex flex-wrap items-center gap-2">
            <h1 className="text-2xl font-semibold">Report Studio</h1>
            <Badge variant={report ? 'default' : 'secondary'}>{report ? 'latest report' : 'not generated'}</Badge>
            {state?.current_stage && <Badge variant="outline">{humanize(state.current_stage)}</Badge>}
          </div>
          <p className="mt-2 max-w-3xl text-sm text-muted-foreground">
            Review the report structure, evidence quality, artifact references, and caveats before using outputs in a business decision.
          </p>
        </div>
        <div className="flex flex-wrap gap-2">
          <Link href={`/projects/${projectId}/dashboard`}>
            <Button type="button" variant="outline">
              <Gauge className="mr-2 h-4 w-4" />
              Dashboard
            </Button>
          </Link>
          <Button type="button" variant="outline" onClick={generateReport} disabled={loading || generating}>
            <FileCheck2 className={`mr-2 h-4 w-4 ${generating ? 'animate-pulse' : ''}`} />
            Generate
          </Button>
          <Button type="button" variant="outline" onClick={exportMarkdown} disabled={loading || exporting || !report}>
            <Download className={`mr-2 h-4 w-4 ${exporting ? 'animate-pulse' : ''}`} />
            Export MD
          </Button>
          <Button type="button" variant="outline" onClick={loadReport} disabled={loading}>
            <RefreshCw className={`mr-2 h-4 w-4 ${loading ? 'animate-spin' : ''}`} />
            Refresh
          </Button>
        </div>
      </div>

      {error && (
        <div className="rounded-md border border-amber-500/30 bg-amber-500/10 px-3 py-2 text-sm text-amber-800">
          {error}
        </div>
      )}
      {notice && !loading && (
        <div className="rounded-md border bg-secondary/30 px-3 py-2 text-sm text-muted-foreground">
          {notice}
        </div>
      )}
      {exportState && (
        <div
          className={`rounded-md border px-3 py-2 text-sm ${
            exportState.type === 'success'
              ? 'border-green-500/30 bg-green-500/10 text-green-800'
              : 'border-destructive/30 bg-destructive/10 text-destructive'
          }`}
        >
          {exportState.message}
        </div>
      )}

      <div className="grid gap-4 lg:grid-cols-[0.8fr_1.2fr] xl:grid-cols-[0.7fr_1.3fr]">
        <div className="space-y-4">
          <Card>
            <CardHeader className="pb-3">
              <CardTitle className="text-base">Report Metadata</CardTitle>
              <CardDescription>Workspace source and coverage context.</CardDescription>
            </CardHeader>
            <CardContent className="space-y-3">
              {metadata.map((item) => (
                <div key={item.label} className="flex items-start justify-between gap-3 rounded-md border px-3 py-2">
                  <div className="min-w-0">
                    <p className="text-xs text-muted-foreground">{item.label}</p>
                    <p className="mt-1 break-words text-sm font-medium">{item.value}</p>
                  </div>
                  {item.copyValue && (
                    <button
                      type="button"
                      onClick={() => void copyValue(item.copyValue ?? '', `metadata-${item.label}`)}
                      className="shrink-0 rounded-md border p-1.5 transition-colors hover:bg-secondary"
                      title={`Copy ${item.label}`}
                    >
                      <Clipboard className="h-3.5 w-3.5" />
                    </button>
                  )}
                </div>
              ))}
            </CardContent>
          </Card>

          <Card>
            <CardHeader className="pb-3">
              <CardTitle className="text-base">Section Outline</CardTitle>
              <CardDescription>Jump through the latest Markdown report.</CardDescription>
            </CardHeader>
            <CardContent>
              {sections.length === 0 ? (
                <p className="text-sm text-muted-foreground">No report sections are available.</p>
              ) : (
                <div className="space-y-2">
                  {sections.map((section, index) => (
                    <button
                      key={`${section.heading}-${index}`}
                      type="button"
                      onClick={() => setActiveSectionIndex(index)}
                      className={`flex w-full items-start justify-between gap-3 rounded-md border px-3 py-2 text-left text-sm transition-colors ${
                        index === activeSectionIndex ? 'border-primary bg-primary/5' : 'hover:bg-secondary/40'
                      }`}
                    >
                      <span className={section.level > 2 ? 'pl-4 text-muted-foreground' : ''}>{section.heading}</span>
                      <ArrowRight className="mt-0.5 h-4 w-4 shrink-0 text-muted-foreground" />
                    </button>
                  ))}
                </div>
              )}
            </CardContent>
          </Card>

          <Card>
            <CardHeader className="pb-3">
              <CardTitle className="text-base">Quality Cues</CardTitle>
              <CardDescription>Signals that the report is ready for business review.</CardDescription>
            </CardHeader>
            <CardContent className="space-y-3">
              {qualityCues.map((cue) => (
                <QualityCue key={cue.label} {...cue} />
              ))}
            </CardContent>
          </Card>
        </div>

        <div className="space-y-4">
          <Card>
            <CardHeader className="pb-3">
              <div className="flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
                <div>
                  <CardTitle className="text-base">{reportTitle}</CardTitle>
                  <CardDescription>{activeSection?.heading || 'Report preview'}</CardDescription>
                </div>
                {report?.path && (
                  <button
                    type="button"
                    onClick={() => void copyValue(report.path, 'report-path')}
                    className="inline-flex items-center gap-1 rounded-md border px-2 py-1 text-xs transition-colors hover:bg-secondary"
                    title="Copy report path"
                  >
                    <Clipboard className="h-3.5 w-3.5" />
                    {copiedValue === 'report-path' ? 'Copied' : 'Path'}
                  </button>
                )}
              </div>
            </CardHeader>
            <CardContent>
              {loading && <p className="text-sm text-muted-foreground">Loading report...</p>}
              {!loading && report && activeSection && (
                <div className="max-h-[72vh] overflow-auto rounded-md border bg-secondary/20 p-4">
                  <MarkdownView content={activeSection.content} />
                </div>
              )}
              {!loading && !report && (
                <div className="rounded-md border bg-secondary/25 p-5">
                  <div className="flex items-start gap-3">
                    <FileText className="mt-0.5 h-5 w-5 text-muted-foreground" />
                    <div>
                      <p className="text-sm font-medium">No report has been generated for this project.</p>
                      <p className="mt-1 text-sm text-muted-foreground">
                        Use the agent to run or refresh the analysis pipeline once data intake and schema mapping are ready.
                      </p>
                      <Link href={`/projects/${projectId}/agent`} className="mt-3 inline-flex text-sm font-medium text-primary underline-offset-2 hover:underline">
                        Open Agent Command Center
                      </Link>
                    </div>
                  </div>
                </div>
              )}
            </CardContent>
          </Card>

          <div className="grid gap-4 xl:grid-cols-2">
            <Card>
              <CardHeader className="pb-3">
                <CardTitle className="text-base">Review Notes</CardTitle>
                <CardDescription>Caveats to check before sharing the report.</CardDescription>
              </CardHeader>
              <CardContent className="space-y-3">
                {reviewNotes.map((note) => (
                  <div key={note} className="flex gap-3 rounded-md border px-3 py-3 text-sm">
                    <ShieldAlert className="mt-0.5 h-4 w-4 shrink-0 text-amber-600" />
                    <span>{note}</span>
                  </div>
                ))}
              </CardContent>
            </Card>

            <Card>
              <CardHeader className="pb-3">
                <CardTitle className="text-base">Artifact References</CardTitle>
                <CardDescription>Files that support or package this report.</CardDescription>
              </CardHeader>
              <CardContent>
                {referencedArtifacts.length === 0 ? (
                  <p className="rounded-md border bg-secondary/25 p-4 text-sm text-muted-foreground">
                    No supporting artifacts are registered yet.
                  </p>
                ) : (
                  <div className="space-y-2">
                    {referencedArtifacts.slice(0, 8).map((artifact) => (
                      <ReportArtifactReference
                        key={artifact.id}
                        artifact={artifact}
                        copied={copiedValue === artifact.id}
                        onCopy={() => void copyValue(artifact.path, artifact.id)}
                      />
                    ))}
                  </div>
                )}
              </CardContent>
            </Card>
          </div>
        </div>
      </div>
    </div>
  )
}

function QualityCue({
  label,
  detail,
  status,
}: {
  label: string
  detail: string
  status: QualityStatus
}) {
  const iconByStatus: Record<QualityStatus, ReactNode> = {
    ready: <CheckCircle2 className="mt-0.5 h-4 w-4 shrink-0 text-green-600" />,
    review: <ShieldAlert className="mt-0.5 h-4 w-4 shrink-0 text-amber-600" />,
    missing: <XCircle className="mt-0.5 h-4 w-4 shrink-0 text-muted-foreground" />,
  }
  const badgeVariant = status === 'ready' ? 'default' : status === 'review' ? 'outline' : 'secondary'

  return (
    <div className="flex gap-3 rounded-md border px-3 py-3">
      {iconByStatus[status]}
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

function ReportArtifactReference({
  artifact,
  copied,
  onCopy,
}: {
  artifact: Artifact
  copied: boolean
  onCopy: () => void
}) {
  const isTable = artifact.type === 'table' || artifact.path.toLowerCase().endsWith('.csv')

  return (
    <div className="flex items-start justify-between gap-3 rounded-md border px-3 py-3">
      <div className="flex min-w-0 items-start gap-2">
        {isTable ? (
          <TableProperties className="mt-0.5 h-4 w-4 shrink-0 text-primary" />
        ) : (
          <Link2 className="mt-0.5 h-4 w-4 shrink-0 text-primary" />
        )}
        <div className="min-w-0">
          <p className="truncate text-sm font-medium">{artifact.title}</p>
          <p className="mt-1 break-all font-mono text-xs text-muted-foreground">{artifact.path}</p>
          <p className="mt-1 text-xs text-muted-foreground">
            {artifact.type} {artifact.mime_type ? `| ${artifact.mime_type}` : ''}
          </p>
        </div>
      </div>
      <button
        type="button"
        onClick={onCopy}
        className="shrink-0 rounded-md border px-2 py-1 text-xs transition-colors hover:bg-secondary"
        title="Copy artifact path"
      >
        {copied ? 'Copied' : 'Path'}
      </button>
    </div>
  )
}

function buildMetadata(report: LatestReport | null, state: ProjectState | null, artifacts: Artifact[]) {
  return [
    {
      label: 'Report source',
      value: report?.path ? trimPath(report.path) : 'Not generated',
      copyValue: report?.path,
    },
    {
      label: 'Project stage',
      value: humanize(state?.current_stage || 'unknown'),
    },
    {
      label: 'Latest activity',
      value: formatDateTime(state?.last_activity),
    },
    {
      label: 'Coverage',
      value: `${state?.files_count ?? 0} files | ${artifacts.length || state?.artifacts_count || 0} artifacts | ${state?.reports_count ?? (report ? 1 : 0)} reports`,
    },
  ]
}

function buildQualityCues(
  sections: ReportSection[],
  artifacts: Artifact[],
  report: LatestReport | null,
  state: ProjectState | null,
) {
  const hasSummary = Boolean(pickSection(sections, ['summary', 'conclusion', 'executive', '一页', '摘要', '结论']))
  const hasKpi = Boolean(report?.content.match(/gmv|localgap|did|lift|增量|净效应/i))
  const hasMethodEvidence = hasArtifact(artifacts, ['diagnostics', 'localgap', 'psm', 'did', 'panel'])
  const hasLimits = Boolean(pickSection(sections, ['limitation', 'caveat', 'assumption', 'risk', '局限', '假设', '风险']))
  const hasArtifactReferences = artifacts.length > 0

  return [
    {
      label: 'Executive answer',
      status: hasSummary ? 'ready' as const : report ? 'review' as const : 'missing' as const,
      detail: hasSummary ? 'A summary or conclusion section is present.' : 'No explicit summary section was found.',
    },
    {
      label: 'KPI traceability',
      status: hasKpi ? 'ready' as const : report ? 'review' as const : 'missing' as const,
      detail: hasKpi ? 'The report includes KPI or effect-size terms.' : 'KPI values are not obvious in the report text.',
    },
    {
      label: 'Method evidence',
      status: hasMethodEvidence ? 'ready' as const : (state?.files_count ?? 0) > 0 ? 'review' as const : 'missing' as const,
      detail: hasMethodEvidence ? 'Panel, diagnostics, LocalGap, or causal artifacts are registered.' : 'Method artifacts are not registered yet.',
    },
    {
      label: 'Limitations',
      status: hasLimits ? 'ready' as const : report ? 'review' as const : 'missing' as const,
      detail: hasLimits ? 'A caveat or limitations section is present.' : 'Add explicit caveats before sharing externally.',
    },
    {
      label: 'Artifact references',
      status: hasArtifactReferences ? 'ready' as const : 'missing' as const,
      detail: hasArtifactReferences ? `${artifacts.length} registered artifact${artifacts.length === 1 ? '' : 's'} can support review.` : 'No artifact index is available for this report.',
    },
  ]
}

function buildReviewNotes(
  sections: ReportSection[],
  artifacts: Artifact[],
  report: LatestReport | null,
  state: ProjectState | null,
) {
  const limitationSection = pickSection(sections, ['limitation', 'caveat', 'assumption', 'risk', '局限', '假设', '风险'])
  const reportNotes = limitationSection ? extractBullets(limitationSection.content).slice(0, 3) : []
  if (reportNotes.length > 0) return reportNotes

  const notes: string[] = []
  if (!report) notes.push('A report has not been generated, so there is no narrative package to review.')
  if ((state?.files_count ?? 0) < 3) notes.push('Input coverage may be incomplete; confirm order, exposure, and activity timeline files.')
  if (!hasArtifact(artifacts, ['localgap', 'psm', 'did', 'diagnostics'])) notes.push('Effect claims should remain cautious until method artifacts are registered.')
  if (notes.length === 0) notes.push('Before business rollout, validate margin, stockout, channel allocation, and calendar controls outside the current report.')
  return notes
}

function rankReportArtifacts(artifacts: Artifact[]) {
  return [...artifacts].sort((a, b) => artifactRank(a) - artifactRank(b))
}

function artifactRank(artifact: Artifact) {
  const text = `${artifact.type} ${artifact.title} ${artifact.path}`.toLowerCase()
  if (text.includes('report')) return 0
  if (text.includes('localgap')) return 1
  if (text.includes('diagnostics') || text.includes('gmv_trend')) return 2
  if (text.includes('psm') || text.includes('did')) return 3
  if (text.includes('panel')) return 4
  return 5
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

    if (current) current.content += `\n${line}`
  }

  if (current) sections.push(current)
  return sections.length > 0 ? sections : [{ heading: 'Report body', level: 1, content }]
}

function pickSection(sections: ReportSection[], keywords: string[]) {
  const normalized = keywords.map((keyword) => keyword.toLowerCase())
  return sections.find((section) => {
    const heading = section.heading.toLowerCase()
    return normalized.some((keyword) => heading.includes(keyword))
  })
}

function extractReportTitle(content: string) {
  return content.match(/^#\s+(.+?)\s*$/m)?.[1] ?? ''
}

function extractBullets(content: string) {
  return content
    .split(/\r?\n/)
    .map((line) => line.trim())
    .filter((line) => /^[-*]\s+/.test(line) || /^\d+\.\s+/.test(line))
    .map((line) => line.replace(/^[-*]\s+/, '').replace(/^\d+\.\s+/, '').replace(/\*\*/g, '').trim())
    .filter(Boolean)
}

function summarizeExportResponse(response: ApiResponse<unknown>) {
  const data = response.data
  if (typeof data === 'string') return data || 'Markdown export is ready.'
  if (isRecord(data) && typeof data.summary === 'string') return data.summary
  if (isRecord(data) && Array.isArray(data.artifacts) && data.artifacts.length > 0) return 'Markdown export is ready and referenced in artifacts.'
  return 'Markdown export is ready.'
}

function normalizeError(error: unknown, fallback: string) {
  if (!error) return fallback
  if (typeof error === 'string') return error
  if (isRecord(error) && typeof error.message === 'string') return error.message
  return fallback
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return Boolean(value && typeof value === 'object' && !Array.isArray(value))
}

function trimPath(value: string) {
  const normalized = value.replace(/\\/g, '/')
  const parts = normalized.split('/')
  if (parts.length <= 3) return value
  return `.../${parts.slice(-3).join('/')}`
}

function humanize(value: string) {
  return value
    .replace(/[_-]+/g, ' ')
    .replace(/\s+/g, ' ')
    .trim()
    .replace(/\b\w/g, (letter) => letter.toUpperCase()) || 'Unknown'
}

function formatDateTime(value?: string | null) {
  if (!value) return 'No activity yet'
  const date = new Date(value)
  if (Number.isNaN(date.getTime())) return value
  return date.toLocaleString()
}
