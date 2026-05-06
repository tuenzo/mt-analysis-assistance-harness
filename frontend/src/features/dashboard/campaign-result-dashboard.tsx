'use client'

import type { ReactNode } from 'react'
import Image from 'next/image'
import {
  Activity,
  CheckCircle2,
  Database,
  LineChart,
  Scale,
  Target,
  TrendingUp,
  Users,
} from 'lucide-react'
import type { Artifact, LatestReport, ProjectState } from '@/lib/api-types'
import { Badge } from '@/components/ui/badge'
import { Card, CardContent } from '@/components/ui/card'
import type {
  CampaignDashboardSnapshot,
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

export function CampaignResultDashboard({
  snapshot,
  state,
  latestReport,
  loading,
  error,
}: CampaignResultDashboardProps) {
  const latestJob = state?.latest_jobs?.[0]
  const summary = snapshot.artifactSummary

  return (
    <div className="mx-auto max-w-none space-y-2 px-4 py-3">
      <div className="flex flex-col gap-2 min-[760px]:flex-row min-[760px]:items-start min-[760px]:justify-between">
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

      <Card className="border-amber-200">
        <CardContent className="grid grid-cols-2 gap-2 p-3">
          <DecisionSection snapshot={snapshot} loading={loading} />
          <DidSection did={snapshot.did} latestReport={latestReport} totalArtifacts={summary.total} />
          <PeriodSection periods={snapshot.periods} points={snapshot.trend.points} metricLabel={snapshot.trend.metricLabel} />
          <UpliftSection quadrants={snapshot.quadrants} />
        </CardContent>
      </Card>
    </div>
  )
}

function DecisionSection({
  snapshot,
  loading,
}: {
  snapshot: CampaignDashboardSnapshot
  loading: boolean
}) {
  return (
    <section className="min-h-36 rounded-md border bg-white p-2.5">
      <SectionTitle
        icon={<Target className="h-4 w-4" />}
        tone="good"
        title="决策建议"
        subtitle={snapshot.decisionLabel}
        badge={loading ? '刷新中' : '一屏决策'}
      />
      <div className="mt-2 space-y-1.5">
        {snapshot.recommendations.slice(0, 2).map((recommendation, index) => (
          <div key={`${recommendation}-${index}`} className="flex gap-1.5 rounded border bg-amber-50/45 px-2 py-1.5">
            <CheckCircle2 className="mt-0.5 h-3.5 w-3.5 shrink-0 text-amber-700" />
            <p className="max-h-9 overflow-hidden text-xs leading-[18px]">{recommendation}</p>
          </div>
        ))}
        <div className="flex items-center gap-2 rounded border bg-secondary/25 px-2 py-1.5">
          <TrendingUp className="h-3.5 w-3.5 shrink-0 text-emerald-700" />
          <p className="max-h-5 overflow-hidden text-xs leading-5 text-muted-foreground">{snapshot.conclusions[0]}</p>
          <Image
            src="/illustrations/promo-strategy-map.svg"
            alt="促销分析策略示意图"
            width={420}
            height={176}
            className="ml-auto hidden h-10 w-24 shrink-0 rounded object-cover min-[980px]:block"
          />
        </div>
      </div>
    </section>
  )
}

function DidSection({
  did,
  latestReport,
  totalArtifacts,
}: {
  did: DidEvaluationSnapshot
  latestReport: LatestReport | null
  totalArtifacts: number
}) {
  return (
    <section className="min-h-36 rounded-md border bg-white p-2.5">
      <SectionTitle
        icon={<Scale className="h-4 w-4" />}
        tone={did.tone}
        title="DID 评估"
        subtitle={did.verdict}
        badge={did.confidence}
      />
      <div className="mt-2 grid grid-cols-3 gap-1.5">
        <MiniMetric label="净效应" value={did.effect} tone={did.tone} />
        <MiniMetric label="增量规模" value={did.incrementalValue} tone="neutral" />
        <MiniMetric label="对照比较" value={did.baselineComparison} tone="neutral" />
      </div>
      <div className="mt-2 rounded border bg-secondary/25 px-2 py-1.5">
        <p className="max-h-9 overflow-hidden text-xs leading-[18px]">{did.interpretation}</p>
        <p className="mt-1 truncate text-[11px] text-muted-foreground">
          {did.significance} / {latestReport ? '报告证据已接入' : 'MVP 快照'} / {totalArtifacts} 个产物
        </p>
      </div>
    </section>
  )
}

function PeriodSection({
  periods,
  points,
  metricLabel,
}: {
  periods: CampaignPeriodSnapshot[]
  points: TrendPoint[]
  metricLabel: string
}) {
  const max = Math.max(...points.map((point) => point.value), 1)

  return (
    <section className="min-h-36 rounded-md border bg-white p-2.5">
      <SectionTitle
        icon={<LineChart className="h-4 w-4" />}
        tone="neutral"
        title="活动前中后"
        subtitle={metricLabel}
      />
      <div className="mt-2 grid grid-cols-3 gap-1.5">
        {periods.map((period, index) => {
          const point = points[index]
          const Icon = period.id === 'before' ? Database : period.id === 'during' ? Activity : TrendingUp

          return (
            <div key={period.id} className="rounded border bg-background px-2 py-1.5">
              <div className="flex items-center gap-1">
                <Icon className="h-3.5 w-3.5 shrink-0 text-muted-foreground" />
                <p className="truncate text-xs font-semibold">{period.label}</p>
              </div>
              <p className="mt-1 break-words text-base font-semibold leading-tight">{period.primary.value}</p>
              <p className="mt-0.5 truncate text-[11px] text-muted-foreground">
                {period.primary.delta ?? period.windowLabel}
              </p>
              <div className="mt-1.5 h-1.5 rounded-full bg-secondary">
                <div
                  className={`h-1.5 rounded-full ${trendBarClass(point?.tone ?? period.primary.tone ?? 'neutral')}`}
                  style={{ width: `${Math.max(((point?.value ?? 1) / max) * 100, 8)}%` }}
                />
              </div>
            </div>
          )
        })}
      </div>
    </section>
  )
}

function UpliftSection({ quadrants }: { quadrants: UpliftQuadrantSnapshot[] }) {
  return (
    <section className="min-h-36 rounded-md border bg-white p-2.5">
      <SectionTitle
        icon={<Users className="h-4 w-4" />}
        tone="good"
        title="Uplift 四象限"
        subtitle="分群含义与下一步动作"
      />
      <div className="mt-2 grid grid-cols-2 gap-1.5">
        {quadrants.map((quadrant) => (
          <div
            key={quadrant.id}
            className={`rounded border px-2 py-1.5 ${
              quadrant.emphasis ? 'border-amber-300 bg-amber-50/60' : 'bg-background'
            }`}
            title={`${quadrant.meaning} ${quadrant.action}`}
          >
            <div className="flex items-start justify-between gap-1">
              <p className="truncate text-xs font-semibold">{quadrant.label}</p>
              <TonePill tone={quadrant.tone}>{quadrant.countLabel}</TonePill>
            </div>
            <p className="mt-0.5 truncate text-[11px] text-muted-foreground">{quadrant.shareLabel}</p>
            <p className="mt-1 max-h-8 overflow-hidden text-xs font-medium leading-4">{quadrant.action}</p>
          </div>
        ))}
      </div>
    </section>
  )
}

function SectionTitle({
  icon,
  tone,
  title,
  subtitle,
  badge,
}: {
  icon: ReactNode
  tone: MetricTone
  title: string
  subtitle: string
  badge?: string
}) {
  return (
    <div className="flex items-start justify-between gap-2">
      <div className="flex min-w-0 items-start gap-2">
        <IconTile tone={tone}>{icon}</IconTile>
        <div className="min-w-0">
          <p className="truncate text-sm font-semibold">{title}</p>
          <p className="truncate text-xs text-muted-foreground">{subtitle}</p>
        </div>
      </div>
      {badge && <TonePill tone={tone}>{badge}</TonePill>}
    </div>
  )
}

function MiniMetric({ label, value, tone }: { label: string; value: string; tone: MetricTone }) {
  return (
    <div className="rounded border bg-background px-2 py-1.5">
      <p className="truncate text-[11px] text-muted-foreground">{label}</p>
      <p className={`mt-1 max-h-8 overflow-hidden text-xs font-semibold leading-4 ${toneTextClass(tone)}`}>{value}</p>
    </div>
  )
}

function IconTile({ tone, children }: { tone: MetricTone; children: ReactNode }) {
  return <div className={`rounded-md p-2 ${toneTileClass(tone)}`}>{children}</div>
}

function TonePill({ tone, children }: { tone: MetricTone; children: ReactNode }) {
  return (
    <span className={`shrink-0 rounded-full px-2 py-0.5 text-[11px] font-semibold ${tonePillClass(tone)}`}>
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
