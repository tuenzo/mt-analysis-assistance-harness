'use client'

import { useEffect, useState, type ReactNode } from 'react'
import {
  Activity,
  CheckCircle2,
  Database,
  Info,
  LineChart,
  Scale,
  Target,
  TrendingUp,
  Users,
} from 'lucide-react'
import { api } from '@/lib/api-client'
import type { Artifact, LatestReport, ProjectState } from '@/lib/api-types'
import { Badge } from '@/components/ui/badge'
import { Card, CardContent } from '@/components/ui/card'
import type {
  CampaignDashboardSnapshot,
  CampaignPeriodSnapshot,
  DidEvaluationSnapshot,
  MetricTone,
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

export function CampaignResultDashboard({
  projectId,
  snapshot,
  state,
  latestReport,
  loading,
  error,
}: CampaignResultDashboardProps) {
  const latestJob = state?.latest_jobs?.[0]
  const summary = snapshot.artifactSummary

  return (
    <div className="mx-auto flex h-[calc(100dvh-158px)] min-h-[380px] max-w-none flex-col gap-2 px-4 py-2 max-[540px]:h-auto max-[540px]:min-h-0">
      <div className="shrink-0">
        <div className="min-w-0">
          <div className="flex flex-wrap items-center gap-2">
            <h1 className="text-xl font-semibold tracking-normal">{snapshot.title}</h1>
            <Badge variant={latestReport ? 'default' : 'secondary'}>{snapshot.statusLabel}</Badge>
            {latestJob?.status && <Badge variant="outline">{humanize(latestJob.status)}</Badge>}
          </div>
          <div className="mt-1 flex flex-wrap gap-2 text-xs text-muted-foreground">
            <span>{snapshot.stageLabel}</span>
            <span aria-hidden="true">/</span>
            <span>{snapshot.sourceLabel}</span>
            <span aria-hidden="true">/</span>
            <span>更新 {snapshot.updatedAtLabel}</span>
            <span aria-hidden="true">/</span>
            <span>{summary.reports} 报告 · {summary.charts} 图 · {summary.tables} 表</span>
          </div>
        </div>
      </div>

      {error && (
        <div className="rounded-md border border-destructive/30 bg-destructive/10 px-3 py-2 text-sm text-destructive">
          {error}
        </div>
      )}

      <Card className="min-h-0 flex-1 border-amber-200">
        <CardContent className="grid h-full min-h-0 grid-cols-2 grid-rows-2 gap-2 p-2.5 max-[540px]:h-auto max-[540px]:grid-cols-1 max-[540px]:grid-rows-none">
          <DecisionSection projectId={projectId} snapshot={snapshot} loading={loading} />
          <DidSection projectId={projectId} did={snapshot.did} latestReport={latestReport} totalArtifacts={summary.total} />
          <PeriodSection projectId={projectId} periods={snapshot.periods} metricLabel={snapshot.trend.metricLabel} />
          <UpliftSection projectId={projectId} quadrants={snapshot.quadrants} />
        </CardContent>
      </Card>
    </div>
  )
}

function DecisionSection({
  projectId,
  snapshot,
  loading,
}: {
  projectId: string
  snapshot: CampaignDashboardSnapshot
  loading: boolean
}) {
  return (
    <section className="relative flex min-h-0 flex-col rounded-md border bg-white p-2.5 shadow-sm">
      <SectionTitle
        icon={<Target className="h-4 w-4" />}
        tone="good"
        title="决策建议"
        subtitle={snapshot.decisionLabel}
        badge={loading ? '刷新中' : '一屏决策'}
        info={
          <InfoCopy
            lines={[
              '优先看左侧 Pareto，判断预算主要影响哪些品类。',
              snapshot.recommendations[0],
              snapshot.conclusions[0],
            ]}
          />
        }
      />
      <div className="mt-2 grid min-h-0 flex-1 grid-cols-[minmax(0,1.62fr)_minmax(78px,0.48fr)] gap-2 max-[720px]:grid-cols-[minmax(0,1.35fr)_minmax(74px,0.65fr)]">
        <ParetoMiniChart projectId={projectId} />
        <div className="grid min-h-0 content-start gap-1.5 overflow-hidden">
          {snapshot.recommendations.slice(0, 1).map((recommendation, index) => (
            <div key={`${recommendation}-${index}`} className="flex gap-1.5 rounded border bg-amber-50/45 px-2 py-1.5">
              <CheckCircle2 className="mt-0.5 h-3.5 w-3.5 shrink-0 text-amber-700" />
              <p className="line-clamp-2 text-xs leading-5">{recommendation}</p>
            </div>
          ))}
        </div>
      </div>
    </section>
  )
}

function DidSection({
  projectId,
  did,
  latestReport,
  totalArtifacts,
}: {
  projectId: string
  did: DidEvaluationSnapshot
  latestReport: LatestReport | null
  totalArtifacts: number
}) {
  return (
    <section className="relative flex min-h-0 flex-col rounded-md border bg-white p-2.5 shadow-sm">
      <SectionTitle
        icon={<Scale className="h-4 w-4" />}
        tone={did.tone}
        title="DID 评估"
        subtitle={did.verdict}
        badge={did.confidence}
        info={
          <InfoCopy
            lines={[
              did.interpretation,
              did.significance,
              did.methodNote,
            ]}
          />
        }
      />
      <div className="mt-2 grid min-h-0 flex-1 grid-cols-[minmax(0,1.62fr)_minmax(78px,0.48fr)] gap-2 max-[720px]:grid-cols-[minmax(0,1.35fr)_minmax(74px,0.65fr)]">
        <LocalGapMiniChart projectId={projectId} />
        <div className="grid min-h-0 content-start gap-1 overflow-hidden">
          <MiniMetric label="净效应" value={did.effect} tone={did.tone} />
          <MiniMetric label="增量规模" value={did.incrementalValue} tone="neutral" />
          <MiniMetric label={latestReport ? '报告' : '快照'} value={`${totalArtifacts} 产物`} tone="neutral" />
        </div>
      </div>
    </section>
  )
}

function PeriodSection({
  projectId,
  periods,
  metricLabel,
}: {
  projectId: string
  periods: CampaignPeriodSnapshot[]
  metricLabel: string
}) {
  return (
    <section className="relative flex min-h-0 flex-col rounded-md border bg-white p-2.5 shadow-sm">
      <SectionTitle
        icon={<LineChart className="h-4 w-4" />}
        tone="neutral"
        title="活动前中后"
        subtitle={metricLabel}
        info={
        <InfoCopy
            lines={[
              '左侧复合图同时看 GMV 波动、活动期、发薪日和活动/非活动对比。',
              ...periods.map((period) => `${period.label}: ${period.interpretation}`),
            ]}
          />
        }
      />
      <div className="mt-2 grid min-h-0 flex-1 grid-cols-[minmax(0,1.62fr)_minmax(78px,0.48fr)] gap-2 max-[720px]:grid-cols-[minmax(0,1.35fr)_minmax(74px,0.65fr)]">
        <PeriodChartStack projectId={projectId} />
        <div className="grid min-h-0 content-start gap-1 overflow-hidden">
          {periods.map((period) => {
            const Icon = period.id === 'before' ? Database : period.id === 'during' ? Activity : TrendingUp

            return (
              <div
                key={period.id}
                className="flex items-center justify-between gap-1.5 rounded border bg-background px-1.5 py-1"
                title={period.primary.delta ?? period.windowLabel}
              >
                <div className="flex min-w-0 items-center gap-1">
                  <Icon className="h-3 w-3 shrink-0 text-muted-foreground" />
                  <p className="truncate text-[11px] font-semibold">{period.label}</p>
                </div>
                <p className="shrink-0 truncate text-[11px] font-semibold leading-tight">{period.primary.value}</p>
              </div>
            )
          })}
        </div>
      </div>
    </section>
  )
}

function UpliftSection({ projectId, quadrants }: { projectId: string; quadrants: UpliftQuadrantSnapshot[] }) {
  return (
    <section className="relative flex min-h-0 flex-col rounded-md border bg-white p-2.5 shadow-sm">
      <SectionTitle
        icon={<Users className="h-4 w-4" />}
        tone="good"
        title="Uplift 四象限"
        subtitle="分群含义与下一步动作"
        info={
          <InfoCopy
            lines={quadrants.map((quadrant) => `${quadrantActionLabel(quadrant.id)}: ${quadrant.meaning} ${quadrant.action}`)}
          />
        }
      />
      <div className="mt-2 grid min-h-0 flex-1 grid-cols-[minmax(0,1.62fr)_minmax(78px,0.48fr)] gap-2 max-[720px]:grid-cols-[minmax(0,1.35fr)_minmax(74px,0.65fr)]">
        <UpliftBubbleMiniChart projectId={projectId} />
        <div className="grid min-h-0 content-start gap-1 overflow-hidden">
          {quadrants.slice(0, 2).map((quadrant) => (
            <div
              key={quadrant.id}
              className={`rounded border px-1.5 py-1 ${
                quadrant.emphasis ? 'border-amber-300 bg-amber-50/60' : 'bg-background'
              }`}
              title={`${quadrant.meaning} ${quadrant.action}`}
            >
              <div className="flex items-center justify-between gap-1.5">
                <p className="truncate text-[11px] font-semibold leading-4">{quadrantActionLabel(quadrant.id)}</p>
                <TonePill tone={quadrant.tone}>{quadrant.countLabel}</TonePill>
              </div>
            </div>
          ))}
        </div>
      </div>
    </section>
  )
}

type DashboardChartId = 'gmv_trend' | 'pareto' | 'activity_comparison' | 'localgap' | 'uplift_quadrant'

function ParetoMiniChart({ projectId }: { projectId: string }) {
  return (
    <ChartFrame ariaLabel="品类GMV Pareto 后端图">
      <BackendChartImage projectId={projectId} chartId="pareto" alt="品类 GMV Pareto，含坐标轴、累计占比和图例" />
    </ChartFrame>
  )
}

function LocalGapMiniChart({ projectId }: { projectId: string }) {
  return (
    <ChartFrame ariaLabel="LocalGap 增量瀑布后端图">
      <BackendChartImage projectId={projectId} chartId="localgap" alt="LocalGap 增量分解瀑布图" />
    </ChartFrame>
  )
}

function PeriodChartStack({ projectId }: { projectId: string }) {
  return (
    <div className="grid min-h-0 grid-rows-2 gap-1.5">
      <ChartFrame ariaLabel="GMV趋势后端图">
        <BackendChartImage projectId={projectId} chartId="gmv_trend" alt="GMV 趋势，含活动期和发薪日标记" />
      </ChartFrame>
      <ChartFrame ariaLabel="活动期对比后端图">
        <BackendChartImage projectId={projectId} chartId="activity_comparison" alt="活动期和非活动期指标对比" />
      </ChartFrame>
    </div>
  )
}

function UpliftBubbleMiniChart({ projectId }: { projectId: string }) {
  return (
    <ChartFrame ariaLabel="品类策略四象限后端图">
      <BackendChartImage projectId={projectId} chartId="uplift_quadrant" alt="品类策略四象限气泡图" />
    </ChartFrame>
  )
}

function BackendChartImage({ projectId, chartId, alt }: { projectId: string; chartId: DashboardChartId; alt: string }) {
  const [failed, setFailed] = useState(false)
  const [src, setSrc] = useState<string | null>(null)

  useEffect(() => {
    setFailed(false)
    setSrc(`${api.getBaseUrl()}/api/projects/${encodeURIComponent(projectId)}/dashboard-charts/${chartId}.png`)
  }, [chartId, projectId])

  if (failed) {
    return (
      <div className="flex h-full min-h-0 items-center justify-center rounded bg-secondary/40 px-2 text-center text-[11px] text-muted-foreground">
        图表加载失败
      </div>
    )
  }

  if (!src) {
    return <div className="h-full min-h-0 rounded bg-secondary/40" />
  }

  return (
    <img
      src={src}
      alt={alt}
      className="h-full w-full object-contain"
      draggable={false}
      onError={() => setFailed(true)}
    />
  )
}

function SectionTitle({
  icon,
  tone,
  title,
  subtitle,
  badge,
  info,
}: {
  icon: ReactNode
  tone: MetricTone
  title: string
  subtitle: string
  badge?: string
  info?: ReactNode
}) {
  return (
    <div className="flex items-start justify-between gap-2">
      <div className="flex min-w-0 items-start gap-2">
        <IconTile tone={tone}>{icon}</IconTile>
        <div className="min-w-0">
          <p className="truncate text-sm font-semibold">{title}</p>
          <p className="max-h-8 overflow-hidden text-xs leading-4 text-muted-foreground">{subtitle}</p>
        </div>
      </div>
      <div className="flex shrink-0 items-center gap-1">
        {badge && <TonePill tone={tone}>{badge}</TonePill>}
        {info && <InfoPopover label={title}>{info}</InfoPopover>}
      </div>
    </div>
  )
}

function ChartFrame({ ariaLabel, children }: {
  title?: string
  ariaLabel: string
  children: ReactNode
}) {
  return (
    <div className="flex min-h-0 flex-col rounded border bg-background px-1.5 py-1" aria-label={ariaLabel}>
      <div className="min-h-0 flex-1">{children}</div>
    </div>
  )
}

function InfoPopover({ label, children }: { label: string; children: ReactNode }) {
  const [open, setOpen] = useState(false)

  return (
    <div className="relative">
      <button
        type="button"
        aria-label={`${label}说明`}
        aria-expanded={open}
        onClick={() => setOpen((current) => !current)}
        className="inline-flex h-6 w-6 items-center justify-center rounded-full border border-amber-200 bg-amber-50 text-amber-800 transition hover:bg-amber-100"
      >
        <Info className="h-3.5 w-3.5" />
      </button>
      {open && (
        <div className="absolute right-0 top-7 z-30 w-64 rounded-md border border-amber-200 bg-white p-2.5 text-xs leading-5 text-foreground shadow-lg">
          {children}
        </div>
      )}
    </div>
  )
}

function InfoCopy({ lines }: { lines: string[] }) {
  return (
    <div className="space-y-1.5">
      {lines.filter(Boolean).map((line, index) => (
        <p key={`${line}-${index}`}>{line}</p>
      ))}
    </div>
  )
}

function MiniMetric({ label, value, tone }: { label: string; value: string; tone: MetricTone }) {
  return (
    <div className="rounded border bg-background px-1.5 py-1">
      <p className="truncate text-[10px] leading-3 text-muted-foreground">{label}</p>
      <p className={`mt-0.5 line-clamp-2 text-[11px] font-semibold leading-[13px] ${toneTextClass(tone)}`}>{value}</p>
    </div>
  )
}

function MiniInsight({ primary, secondary }: { primary: string; secondary: string }) {
  return (
    <div className="rounded border bg-secondary/25 px-1.5 py-1">
      <p className="truncate text-[11px] font-semibold leading-4">{primary}</p>
      <p className="truncate text-[10px] text-muted-foreground">{secondary}</p>
    </div>
  )
}

function IconTile({ tone, children }: { tone: MetricTone; children: ReactNode }) {
  return <div className={`rounded-md p-1.5 ${toneTileClass(tone)}`}>{children}</div>
}

function TonePill({ tone, children }: { tone: MetricTone; children: ReactNode }) {
  return (
    <span className={`inline-flex max-w-[74px] shrink-0 truncate rounded-full px-2 py-0.5 text-[11px] font-semibold ${tonePillClass(tone)}`}>
      {children}
    </span>
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

function tonePillClass(tone: MetricTone) {
  const classes: Record<MetricTone, string> = {
    good: 'bg-primary text-primary-foreground',
    neutral: 'border border-border bg-background text-foreground',
    watch: 'border border-amber-200 bg-amber-100 text-amber-900',
    risk: 'bg-destructive text-destructive-foreground',
  }
  return classes[tone]
}

function toneTextClass(tone: MetricTone) {
  const classes: Record<MetricTone, string> = {
    good: 'text-emerald-700',
    neutral: 'text-foreground',
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

function quadrantActionLabel(id: UpliftQuadrantSnapshot['id']) {
  const labels: Record<UpliftQuadrantSnapshot['id'], string> = {
    persuadables: '优先加码',
    sure_things: '控折护盘',
    lost_causes: '先诊断',
    do_not_disturb: '减曝光',
  }
  return labels[id]
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
