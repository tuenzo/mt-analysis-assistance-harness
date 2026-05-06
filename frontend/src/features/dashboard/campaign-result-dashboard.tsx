'use client'

import { useMemo, useState, type ReactNode } from 'react'
import Link from 'next/link'
import {
  Activity,
  AlertTriangle,
  BarChart3,
  CheckCircle2,
  Clipboard,
  Database,
  FileText,
  LineChart,
  PieChart,
  RefreshCw,
  Scale,
  ShieldAlert,
  Target,
  TrendingUp,
  Users,
} from 'lucide-react'
import type { Artifact, LatestReport, ProjectState } from '@/lib/api-types'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import type {
  CampaignDashboardSnapshot,
  CampaignMetric,
  CampaignPeriodSnapshot,
  DidEvaluationSnapshot,
  MetricTone,
  TrendPoint,
  UpliftQuadrantSnapshot,
} from './campaign-snapshot'

type CampaignResultDashboardProps = {
  projectId: string
  snapshot: CampaignDashboardSnapshot
  state: ProjectState | null
  artifacts: Artifact[]
  latestReport: LatestReport | null
  loading: boolean
  error: string | null
  onRefresh: () => void | Promise<void>
}

type ArtifactGroup = {
  label: string
  artifacts: Artifact[]
}

export function CampaignResultDashboard({
  projectId,
  snapshot,
  state,
  artifacts,
  latestReport,
  loading,
  error,
  onRefresh,
}: CampaignResultDashboardProps) {
  const artifactGroups = useMemo(() => groupArtifacts(artifacts), [artifacts])
  const chartArtifacts = useMemo(() => artifacts.filter(isChartArtifact).slice(0, 6), [artifacts])
  const latestJob = state?.latest_jobs?.[0]
  const [copiedArtifactId, setCopiedArtifactId] = useState<string | null>(null)

  async function copyArtifactPath(artifact: Artifact) {
    try {
      await navigator.clipboard.writeText(artifact.path)
      setCopiedArtifactId(artifact.id)
      window.setTimeout(() => setCopiedArtifactId(null), 1400)
    } catch {
      setCopiedArtifactId(null)
    }
  }

  return (
    <div className="container mx-auto max-w-7xl space-y-5 px-4 py-6">
      <div className="flex flex-col gap-4 lg:flex-row lg:items-start lg:justify-between">
        <div className="min-w-0">
          <div className="flex flex-wrap items-center gap-2">
            <h1 className="text-2xl font-semibold tracking-normal">{snapshot.title}</h1>
            <Badge variant={latestReport ? 'default' : 'secondary'}>{snapshot.statusLabel}</Badge>
            {latestJob?.status && <Badge variant="outline">{humanize(latestJob.status)}</Badge>}
          </div>
          <div className="mt-2 flex flex-wrap gap-2 text-xs text-muted-foreground">
            <span>{snapshot.stageLabel}</span>
            <span aria-hidden="true">/</span>
            <span>{snapshot.sourceLabel}</span>
            <span aria-hidden="true">/</span>
            <span>更新 {snapshot.updatedAtLabel}</span>
          </div>
        </div>

        <div className="flex flex-wrap gap-2">
          <Link href={`/projects/${projectId}/agent`}>
            <Button type="button" variant="outline">
              <Activity className="mr-2 h-4 w-4" />
              Agent 分析
            </Button>
          </Link>
          <Link href={`/projects/${projectId}/reports`}>
            <Button type="button" variant="outline">
              <FileText className="mr-2 h-4 w-4" />
              报告
            </Button>
          </Link>
          <Button type="button" variant="outline" onClick={() => void onRefresh()} disabled={loading}>
            <RefreshCw className={`mr-2 h-4 w-4 ${loading ? 'animate-spin' : ''}`} />
            刷新
          </Button>
        </div>
      </div>

      {error && (
        <div className="rounded-lg border border-destructive/30 bg-destructive/10 px-3 py-2 text-sm text-destructive">
          {error}
        </div>
      )}

      <div className="grid gap-4 xl:grid-cols-[1.05fr_0.95fr]">
        <ExecutiveRecommendationCard snapshot={snapshot} loading={loading} />
        <DidEvaluationCard did={snapshot.did} />
      </div>

      <div className="grid gap-4 lg:grid-cols-3">
        {snapshot.periods.map((period) => (
          <PeriodMetricCard key={period.id} period={period} />
        ))}
      </div>

      <TrendComparisonCard metricLabel={snapshot.trend.metricLabel} points={snapshot.trend.points} />

      <UpliftQuadrantGrid quadrants={snapshot.quadrants} />

      <ConclusionsAndCaveats conclusions={snapshot.conclusions} caveats={snapshot.caveats} />

      <DashboardEvidencePanel
        projectId={projectId}
        summary={snapshot.artifactSummary}
        latestReport={latestReport}
        artifactGroups={artifactGroups}
        chartArtifacts={chartArtifacts}
        copiedArtifactId={copiedArtifactId}
        onCopyArtifact={(artifact) => void copyArtifactPath(artifact)}
      />
    </div>
  )
}

function ExecutiveRecommendationCard({
  snapshot,
  loading,
}: {
  snapshot: CampaignDashboardSnapshot
  loading: boolean
}) {
  return (
    <Card className="border-amber-200">
      <CardHeader className="pb-3">
        <div className="flex items-start justify-between gap-3">
          <div className="flex min-w-0 items-start gap-3">
            <IconTile tone="good">
              <Target className="h-4 w-4" />
            </IconTile>
            <div className="min-w-0">
              <CardTitle className="text-base">决策建议</CardTitle>
              <CardDescription>{snapshot.decisionLabel}</CardDescription>
            </div>
          </div>
          <Badge variant="outline">{loading ? '刷新中' : '决策视图'}</Badge>
        </div>
      </CardHeader>
      <CardContent className="space-y-4">
        <div className="grid gap-3 md:grid-cols-2">
          {snapshot.recommendations.slice(0, 4).map((recommendation, index) => (
            <div key={`${recommendation}-${index}`} className="flex min-h-20 gap-3 rounded-lg border bg-amber-50/45 p-3">
              <CheckCircle2 className="mt-0.5 h-4 w-4 shrink-0 text-amber-700" />
              <p className="text-sm leading-6">{recommendation}</p>
            </div>
          ))}
        </div>
        <div className="rounded-lg border bg-background p-3">
          <div className="mb-2 flex items-center gap-2 text-sm font-medium">
            <TrendingUp className="h-4 w-4 text-emerald-700" />
            组合层面结论
          </div>
          <p className="text-sm leading-6 text-muted-foreground">{snapshot.conclusions[0]}</p>
        </div>
      </CardContent>
    </Card>
  )
}

function DidEvaluationCard({ did }: { did: DidEvaluationSnapshot }) {
  return (
    <Card>
      <CardHeader className="pb-3">
        <div className="flex items-start justify-between gap-3">
          <div className="flex min-w-0 items-start gap-3">
            <IconTile tone={did.tone}>
              <Scale className="h-4 w-4" />
            </IconTile>
            <div className="min-w-0">
              <CardTitle className="text-base">DID 评估结果</CardTitle>
              <CardDescription>{did.verdict}</CardDescription>
            </div>
          </div>
          <ToneBadge tone={did.tone}>{did.confidence}</ToneBadge>
        </div>
      </CardHeader>
      <CardContent className="space-y-4">
        <div className="grid gap-3 sm:grid-cols-3">
          <MetricBlock label="净效应" value={did.effect} tone={did.tone} />
          <MetricBlock label="增量规模" value={did.incrementalValue} tone="neutral" />
          <MetricBlock label="对照比较" value={did.baselineComparison} tone="neutral" />
        </div>
        <div className="rounded-lg border bg-secondary/25 p-3">
          <p className="text-sm leading-6">{did.interpretation}</p>
          <p className="mt-2 text-xs leading-5 text-muted-foreground">{did.significance}</p>
          <p className="mt-1 text-xs leading-5 text-muted-foreground">{did.methodNote}</p>
        </div>
      </CardContent>
    </Card>
  )
}

function PeriodMetricCard({ period }: { period: CampaignPeriodSnapshot }) {
  const Icon = period.id === 'before' ? Database : period.id === 'during' ? Activity : TrendingUp

  return (
    <Card>
      <CardHeader className="pb-3">
        <div className="flex items-start justify-between gap-3">
          <div className="flex min-w-0 items-start gap-3">
            <IconTile tone={period.primary.tone ?? 'neutral'}>
              <Icon className="h-4 w-4" />
            </IconTile>
            <div className="min-w-0">
              <CardTitle className="text-base">{period.label}</CardTitle>
              <CardDescription>{period.windowLabel}</CardDescription>
            </div>
          </div>
          {period.primary.delta && <ToneBadge tone={period.primary.tone ?? 'neutral'}>{period.primary.delta}</ToneBadge>}
        </div>
      </CardHeader>
      <CardContent className="space-y-4">
        <div className="min-h-20 rounded-lg border bg-background p-3">
          <p className="text-xs text-muted-foreground">{period.primary.label}</p>
          <p className="mt-2 break-words text-2xl font-semibold leading-tight">{period.primary.value}</p>
        </div>
        <div className="grid gap-2 sm:grid-cols-2 lg:grid-cols-1 2xl:grid-cols-2">
          {period.secondary.map((metric) => (
            <MetricBlock key={metric.label} label={metric.label} value={metric.value} delta={metric.delta} tone={metric.tone} />
          ))}
        </div>
        <p className="min-h-16 text-sm leading-6 text-muted-foreground">{period.interpretation}</p>
      </CardContent>
    </Card>
  )
}

function TrendComparisonCard({ metricLabel, points }: { metricLabel: string; points: TrendPoint[] }) {
  const max = Math.max(...points.map((point) => point.value), 1)

  return (
    <Card>
      <CardHeader className="pb-3">
        <div className="flex items-start gap-3">
          <IconTile tone="neutral">
            <LineChart className="h-4 w-4" />
          </IconTile>
          <div>
            <CardTitle className="text-base">活动前中后趋势对比</CardTitle>
            <CardDescription>{metricLabel}</CardDescription>
          </div>
        </div>
      </CardHeader>
      <CardContent>
        <div className="grid gap-3 lg:grid-cols-3">
          {points.map((point) => (
            <div key={point.label} className="min-h-32 rounded-lg border p-3">
              <div className="flex items-center justify-between gap-3">
                <div>
                  <p className="text-sm font-medium">{point.label}</p>
                  <p className="mt-1 text-xs text-muted-foreground">{point.caption}</p>
                </div>
                <ToneBadge tone={point.tone}>{point.displayValue}</ToneBadge>
              </div>
              <div className="mt-5 h-3 rounded-full bg-secondary">
                <div
                  className={`h-3 rounded-full ${trendBarClass(point.tone)}`}
                  style={{ width: `${Math.max((point.value / max) * 100, 8)}%` }}
                />
              </div>
            </div>
          ))}
        </div>
      </CardContent>
    </Card>
  )
}

function UpliftQuadrantGrid({ quadrants }: { quadrants: UpliftQuadrantSnapshot[] }) {
  return (
    <Card>
      <CardHeader className="pb-3">
        <div className="flex items-start gap-3">
          <IconTile tone="good">
            <Users className="h-4 w-4" />
          </IconTile>
          <div>
            <CardTitle className="text-base">Uplift 四象限策略</CardTitle>
            <CardDescription>按响应类型拆分人群 / 品类含义与下一步处理。</CardDescription>
          </div>
        </div>
      </CardHeader>
      <CardContent>
        <div className="grid gap-4 lg:grid-cols-2">
          {quadrants.map((quadrant) => (
            <div
              key={quadrant.id}
              className={`min-h-56 rounded-lg border p-4 ${quadrant.emphasis ? 'border-amber-300 bg-amber-50/60' : 'bg-background'}`}
            >
              <div className="flex items-start justify-between gap-3">
                <div className="min-w-0">
                  <p className="text-base font-semibold">{quadrant.label}</p>
                  <p className="mt-1 text-xs text-muted-foreground">{quadrant.shareLabel}</p>
                </div>
                <ToneBadge tone={quadrant.tone}>{quadrant.countLabel}</ToneBadge>
              </div>
              <div className="mt-4 space-y-3">
                <QuadrantLine label="业务含义" value={quadrant.meaning} />
                <QuadrantLine label="建议动作" value={quadrant.action} />
              </div>
            </div>
          ))}
        </div>
      </CardContent>
    </Card>
  )
}

function ConclusionsAndCaveats({ conclusions, caveats }: { conclusions: string[]; caveats: string[] }) {
  return (
    <div className="grid gap-4 xl:grid-cols-2">
      <Card>
        <CardHeader className="pb-3">
          <div className="flex items-start gap-3">
            <IconTile tone="good">
              <CheckCircle2 className="h-4 w-4" />
            </IconTile>
            <div>
              <CardTitle className="text-base">结论</CardTitle>
              <CardDescription>先给业务判断，再承接证据细节。</CardDescription>
            </div>
          </div>
        </CardHeader>
        <CardContent className="space-y-3">
          {conclusions.map((conclusion, index) => (
            <ListRow key={`${conclusion}-${index}`} icon={<CheckCircle2 className="h-4 w-4 text-emerald-700" />}>
              {conclusion}
            </ListRow>
          ))}
        </CardContent>
      </Card>

      <Card>
        <CardHeader className="pb-3">
          <div className="flex items-start gap-3">
            <IconTile tone="watch">
              <ShieldAlert className="h-4 w-4" />
            </IconTile>
            <div>
              <CardTitle className="text-base">限制与复核点</CardTitle>
              <CardDescription>预算或运营策略调整前需要先确认的事项。</CardDescription>
            </div>
          </div>
        </CardHeader>
        <CardContent className="space-y-3">
          {caveats.map((caveat, index) => (
            <ListRow key={`${caveat}-${index}`} icon={<AlertTriangle className="h-4 w-4 text-amber-700" />}>
              {caveat}
            </ListRow>
          ))}
        </CardContent>
      </Card>
    </div>
  )
}

function DashboardEvidencePanel({
  projectId,
  summary,
  latestReport,
  artifactGroups,
  chartArtifacts,
  copiedArtifactId,
  onCopyArtifact,
}: {
  projectId: string
  summary: CampaignDashboardSnapshot['artifactSummary']
  latestReport: LatestReport | null
  artifactGroups: ArtifactGroup[]
  chartArtifacts: Artifact[]
  copiedArtifactId: string | null
  onCopyArtifact: (artifact: Artifact) => void
}) {
  return (
    <Card>
      <CardHeader className="pb-3">
        <div className="flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
          <div className="flex items-start gap-3">
            <IconTile tone="neutral">
              <BarChart3 className="h-4 w-4" />
            </IconTile>
            <div>
              <CardTitle className="text-base">产物与报告证据</CardTitle>
              <CardDescription>支撑当前判断的图表、表格、报告和已注册输出。</CardDescription>
            </div>
          </div>
          <div className="flex flex-wrap gap-2">
            <Badge variant="outline">{summary.total} 个产物</Badge>
            <Badge variant="secondary">{summary.charts} 张图</Badge>
            <Badge variant="secondary">{summary.tables} 张表</Badge>
            <Badge variant="secondary">{summary.reports} 份报告</Badge>
          </div>
        </div>
      </CardHeader>
      <CardContent className="space-y-5">
        <div className="grid gap-4 xl:grid-cols-[0.95fr_1.05fr]">
          <div className="rounded-lg border p-4">
            <div className="flex items-start justify-between gap-3">
              <div>
                <p className="text-sm font-medium">最新报告证据</p>
                <p className="mt-1 text-xs leading-5 text-muted-foreground">
                  {latestReport ? latestReport.path : '暂无已注册报告'}
                </p>
              </div>
              <Link href={`/projects/${projectId}/reports`}>
                <Button type="button" variant="outline" size="sm">
                  <FileText className="mr-2 h-4 w-4" />
                  打开
                </Button>
              </Link>
            </div>
            <p className="mt-4 text-sm leading-6 text-muted-foreground">最新产物：{summary.latestTitle}</p>
          </div>

          <div className="rounded-lg border p-4">
            <div className="flex items-center justify-between gap-3">
              <p className="text-sm font-medium">图表产物概览</p>
              <Badge variant={chartArtifacts.length > 0 ? 'default' : 'secondary'}>{chartArtifacts.length} 个可用</Badge>
            </div>
            {chartArtifacts.length === 0 ? (
              <p className="mt-4 min-h-20 rounded-lg bg-secondary/25 p-3 text-sm leading-6 text-muted-foreground">
                暂无来自 diagnostics、LocalGap、DID 或报告的图表产物。
              </p>
            ) : (
              <div className="mt-4 grid gap-3 md:grid-cols-2">
                {chartArtifacts.map((artifact) => (
                  <ChartArtifactTile key={artifact.id} artifact={artifact} />
                ))}
              </div>
            )}
          </div>
        </div>

        {artifactGroups.length === 0 ? (
          <div className="rounded-lg border bg-secondary/25 p-4 text-sm text-muted-foreground">
            暂无已注册产物。
          </div>
        ) : (
          <div className="grid gap-4 xl:grid-cols-2">
            {artifactGroups.map((group) => (
              <div key={group.label} className="space-y-2">
                <div className="flex items-center gap-2 text-xs font-semibold uppercase text-muted-foreground">
                  <PieChart className="h-3.5 w-3.5" />
                  {group.label}
                </div>
                <div className="space-y-2">
                  {group.artifacts.map((artifact) => (
                    <ArtifactEvidenceRow
                      key={artifact.id}
                      artifact={artifact}
                      projectId={projectId}
                      copied={copiedArtifactId === artifact.id}
                      onCopy={() => onCopyArtifact(artifact)}
                    />
                  ))}
                </div>
              </div>
            ))}
          </div>
        )}
      </CardContent>
    </Card>
  )
}

function ChartArtifactTile({ artifact }: { artifact: Artifact }) {
  return (
    <div className="min-h-24 rounded-lg border bg-background p-3">
      <div className="flex items-start gap-2">
        <LineChart className="mt-0.5 h-4 w-4 shrink-0 text-primary" />
        <div className="min-w-0">
          <p className="truncate text-sm font-medium">{artifact.title}</p>
          <p className="mt-1 break-all font-mono text-xs text-muted-foreground">{artifact.path}</p>
          <p className="mt-2 text-xs text-muted-foreground">{formatTime(artifact.created_at)}</p>
        </div>
      </div>
    </div>
  )
}

function ArtifactEvidenceRow({
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
  const isReport = isReportArtifact(artifact)
  const Icon = isChartArtifact(artifact) ? LineChart : isTableArtifact(artifact) ? BarChart3 : FileText

  return (
    <div className="flex min-h-24 items-start justify-between gap-3 rounded-lg border px-3 py-3">
      <div className="flex min-w-0 items-start gap-2">
        <Icon className="mt-0.5 h-4 w-4 shrink-0 text-primary" />
        <div className="min-w-0">
          {isReport ? (
            <Link href={`/projects/${projectId}/reports`} className="block truncate text-sm font-medium text-primary underline-offset-2 hover:underline">
              {artifact.title}
            </Link>
          ) : (
            <p className="truncate text-sm font-medium">{artifact.title}</p>
          )}
          <p className="mt-1 break-all font-mono text-xs text-muted-foreground">{artifact.path}</p>
          <p className="mt-2 text-xs text-muted-foreground">{formatTime(artifact.created_at)}</p>
        </div>
      </div>
      <div className="flex shrink-0 flex-col items-end gap-2">
        <Badge variant={isReport ? 'default' : 'secondary'}>{artifact.type}</Badge>
        <button
          type="button"
          onClick={onCopy}
          className="inline-flex h-8 w-8 items-center justify-center rounded-md border transition-colors hover:bg-secondary"
          title={copied ? '已复制路径' : '复制产物路径'}
        >
          <Clipboard className="h-3.5 w-3.5" />
          <span className="sr-only">{copied ? '已复制路径' : '复制产物路径'}</span>
        </button>
      </div>
    </div>
  )
}

function MetricBlock({ label, value, delta, tone = 'neutral' }: CampaignMetric) {
  return (
    <div className="min-h-20 rounded-lg border bg-background p-3">
      <p className="text-xs text-muted-foreground">{label}</p>
      <p className="mt-2 break-words text-sm font-semibold leading-tight">{value}</p>
      {delta && <p className={`mt-1 text-xs ${toneTextClass(tone)}`}>{delta}</p>}
    </div>
  )
}

function QuadrantLine({ label, value }: { label: string; value: string }) {
  return (
    <div>
      <p className="text-xs font-semibold uppercase text-muted-foreground">{label}</p>
      <p className="mt-1 text-sm leading-6">{value}</p>
    </div>
  )
}

function ListRow({ icon, children }: { icon: ReactNode; children: ReactNode }) {
  return (
    <div className="flex min-h-14 gap-3 rounded-lg border bg-background p-3 text-sm leading-6">
      <span className="mt-0.5 shrink-0">{icon}</span>
      <span>{children}</span>
    </div>
  )
}

function IconTile({ tone, children }: { tone: MetricTone; children: ReactNode }) {
  return <div className={`rounded-md p-2 ${toneTileClass(tone)}`}>{children}</div>
}

function ToneBadge({ tone, children }: { tone: MetricTone; children: ReactNode }) {
  const variant = tone === 'risk' ? 'destructive' : tone === 'neutral' ? 'outline' : tone === 'watch' ? 'secondary' : 'default'
  return (
    <Badge variant={variant} className={tone === 'watch' ? 'border-amber-200 bg-amber-100 text-amber-900 hover:bg-amber-100' : ''}>
      {children}
    </Badge>
  )
}

function toneTileClass(tone: MetricTone) {
  const classes: Record<MetricTone, string> = {
    good: 'bg-emerald-50 text-emerald-700',
    neutral: 'bg-secondary text-muted-foreground',
    watch: 'bg-amber-100 text-amber-800',
    risk: 'bg-rose-50 text-rose-700',
  }
  return classes[tone]
}

function toneTextClass(tone: MetricTone) {
  const classes: Record<MetricTone, string> = {
    good: 'text-emerald-700',
    neutral: 'text-muted-foreground',
    watch: 'text-amber-700',
    risk: 'text-rose-700',
  }
  return classes[tone]
}

function trendBarClass(tone: MetricTone) {
  const classes: Record<MetricTone, string> = {
    good: 'bg-emerald-600',
    neutral: 'bg-slate-500',
    watch: 'bg-amber-500',
    risk: 'bg-rose-600',
  }
  return classes[tone]
}

function groupArtifacts(artifacts: Artifact[]): ArtifactGroup[] {
  const groups = artifacts.reduce<Record<string, Artifact[]>>((acc, artifact) => {
    const label = artifactGroupLabel(artifact)
    acc[label] = acc[label] ?? []
    acc[label].push(artifact)
    return acc
  }, {})

  return Object.entries(groups).map(([label, groupArtifacts]) => ({
    label,
    artifacts: groupArtifacts.slice(0, 6),
  }))
}

function artifactGroupLabel(artifact: Artifact) {
  if (isReportArtifact(artifact)) return '报告'
  if (isChartArtifact(artifact)) return '图表'
  if (isTableArtifact(artifact)) return '表格'
  return '其他输出'
}

function isChartArtifact(artifact: Artifact) {
  const haystack = `${artifact.type} ${artifact.title} ${artifact.path}`.toLowerCase()
  return artifact.type === 'chart' || haystack.includes('/charts/') || haystack.includes('chart')
}

function isTableArtifact(artifact: Artifact) {
  const haystack = `${artifact.type} ${artifact.title} ${artifact.path}`.toLowerCase()
  return artifact.type === 'table' || haystack.endsWith('.csv') || haystack.includes('/tables/')
}

function isReportArtifact(artifact: Artifact) {
  const haystack = `${artifact.type} ${artifact.title} ${artifact.path}`.toLowerCase()
  return artifact.type === 'report' || haystack.endsWith('.md') || haystack.includes('/reports/')
}

function humanize(value: string) {
  const labels: Record<string, string> = {
    succeeded: '成功',
    completed: '完成',
    failed: '失败',
    running: '运行中',
    pending: '等待中',
  }
  if (labels[value]) return labels[value]
  return value
    .replace(/[_-]+/g, ' ')
    .replace(/\s+/g, ' ')
    .trim()
    .replace(/\b\w/g, (letter) => letter.toUpperCase())
}

function formatTime(value: string) {
  const date = new Date(value)
  if (Number.isNaN(date.getTime())) return '--'
  return new Intl.DateTimeFormat('zh-CN', { month: 'short', day: 'numeric' }).format(date)
}
