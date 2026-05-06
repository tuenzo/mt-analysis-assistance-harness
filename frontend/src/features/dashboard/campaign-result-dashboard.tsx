'use client'

import type { ReactNode } from 'react'
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
    <div className="mx-auto max-w-none space-y-2 px-4 py-2">
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
        <CardContent className="grid grid-cols-[repeat(auto-fit,minmax(320px,1fr))] gap-2 p-2.5">
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
    <section className="min-h-52 rounded-md border bg-white p-2.5">
      <SectionTitle
        icon={<Target className="h-4 w-4" />}
        tone="good"
        title="决策建议"
        subtitle={snapshot.decisionLabel}
        badge={loading ? '刷新中' : '一屏决策'}
      />
      <div className="mt-2 grid grid-cols-[minmax(0,0.86fr)_minmax(140px,0.42fr)] gap-2">
        <div className="space-y-1.5">
          {snapshot.recommendations.slice(0, 2).map((recommendation, index) => (
            <div key={`${recommendation}-${index}`} className="flex gap-1.5 rounded border bg-amber-50/45 px-2 py-1.5">
              <CheckCircle2 className="mt-0.5 h-3.5 w-3.5 shrink-0 text-amber-700" />
              <p className="max-h-10 overflow-hidden text-xs leading-5">{recommendation}</p>
            </div>
          ))}
          <div className="flex items-center gap-2 rounded border bg-secondary/25 px-2 py-1.5">
            <TrendingUp className="h-3.5 w-3.5 shrink-0 text-emerald-700" />
            <p className="max-h-5 overflow-hidden text-xs leading-5 text-muted-foreground">{snapshot.conclusions[0]}</p>
          </div>
        </div>
        <ParetoMiniChart />
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
    <section className="min-h-52 rounded-md border bg-white p-2.5">
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
      <div className="mt-2 grid grid-cols-[minmax(0,0.54fr)_minmax(0,1.46fr)] gap-2">
        <MiniInsight
          primary={did.interpretation}
          secondary={`${did.significance} / ${latestReport ? '报告已接入' : '快照'} / ${totalArtifacts} 产物`}
        />
        <LocalGapMiniChart />
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
    <section className="min-h-52 rounded-md border bg-white p-2.5">
      <SectionTitle
        icon={<LineChart className="h-4 w-4" />}
        tone="neutral"
        title="活动前中后"
        subtitle={metricLabel}
      />
      <div className="mt-2 grid grid-cols-[minmax(0,1.15fr)_minmax(0,0.85fr)] gap-2">
        <GmvTrendMiniChart />
        <ActivityLiftMiniBars />
      </div>
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
              <p className="mt-1 break-words text-xs font-semibold leading-tight">{period.primary.value}</p>
              <p className="mt-0.5 truncate text-[11px] text-muted-foreground">
                {period.primary.delta ?? period.windowLabel}
              </p>
              <div className="mt-1 h-1.5 rounded-full bg-secondary">
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
    <section className="min-h-52 rounded-md border bg-white p-2.5">
      <SectionTitle
        icon={<Users className="h-4 w-4" />}
        tone="good"
        title="Uplift 四象限"
        subtitle="分群含义与下一步动作"
      />
      <div className="mt-2 grid grid-cols-[minmax(0,1fr)_96px] gap-2">
        <UpliftBubbleMiniChart />
        <div className="grid grid-cols-1 gap-1.5">
          {quadrants.slice(0, 4).map((quadrant) => (
            <div
              key={quadrant.id}
              className={`rounded border px-2 py-1 ${
                quadrant.emphasis ? 'border-amber-300 bg-amber-50/60' : 'bg-background'
              }`}
              title={`${quadrant.meaning} ${quadrant.action}`}
            >
              <div className="flex items-center justify-between gap-1">
                <p className="text-[11px] font-semibold leading-4">{quadrantActionLabel(quadrant.id)}</p>
                <TonePill tone={quadrant.tone}>{quadrant.countLabel}</TonePill>
              </div>
            </div>
          ))}
        </div>
      </div>
    </section>
  )
}

function ParetoMiniChart() {
  return (
    <div className="rounded border bg-background px-2 py-1.5" aria-label="品类GMV Pareto 小图">
      <p className="truncate text-[11px] font-semibold">品类 GMV Pareto</p>
      <svg className="mt-1 h-28 w-full" viewBox="0 0 108 86" role="img" aria-label="饮料、零食、生鲜、母婴、家清的 GMV 累计占比">
        <line x1="8" y1="70" x2="104" y2="70" stroke="#d9dde3" />
        <rect x="14" y="18" width="12" height="52" rx="2" fill="#3b82f6" />
        <rect x="34" y="34" width="12" height="36" rx="2" fill="#3b82f6" opacity="0.9" />
        <rect x="54" y="48" width="12" height="22" rx="2" fill="#3b82f6" opacity="0.82" />
        <rect x="74" y="58" width="12" height="12" rx="2" fill="#3b82f6" opacity="0.72" />
        <rect x="94" y="64" width="8" height="6" rx="2" fill="#3b82f6" opacity="0.62" />
        <polyline points="20,46 40,32 60,23 80,17 98,13" fill="none" stroke="#1d4ed8" strokeWidth="2" />
        <circle cx="20" cy="46" r="2.5" fill="#1d4ed8" />
        <circle cx="40" cy="32" r="2.5" fill="#1d4ed8" />
        <circle cx="60" cy="23" r="2.5" fill="#1d4ed8" />
        <circle cx="80" cy="17" r="2.5" fill="#1d4ed8" />
        <circle cx="98" cy="13" r="2.5" fill="#1d4ed8" />
        <text x="8" y="82" fontSize="8" fill="#646a73">饮料</text>
        <text x="34" y="82" fontSize="8" fill="#646a73">零食</text>
        <text x="58" y="82" fontSize="8" fill="#646a73">生鲜</text>
      </svg>
    </div>
  )
}

function LocalGapMiniChart() {
  return (
    <div className="rounded border bg-background px-2 py-1.5" aria-label="LocalGap 增量瀑布小图">
      <p className="truncate text-[11px] font-semibold">LocalGap 增量拆解</p>
      <svg className="mt-1 h-20 w-full" viewBox="0 0 206 64" role="img" aria-label="基线 GMV 到实际 GMV 的增量瀑布">
        <line x1="7" y1="50" x2="198" y2="50" stroke="#d9dde3" />
        <rect x="8" y="32" width="22" height="18" rx="1.5" fill="#a8adb5" />
        <rect x="44" y="22" width="22" height="28" rx="1.5" fill="#55b95b" />
        <rect x="78" y="16" width="22" height="22" rx="1.5" fill="#55b95b" />
        <rect x="112" y="12" width="22" height="15" rx="1.5" fill="#55b95b" />
        <rect x="146" y="14" width="22" height="13" rx="1.5" fill="#d92929" />
        <rect x="180" y="10" width="18" height="40" rx="1.5" fill="#9aa1aa" />
        <polyline
          points="30,32 44,32 66,22 78,22 100,16 112,16 134,12 146,12 168,14 180,14"
          fill="none"
          stroke="#1f2329"
          strokeDasharray="4 3"
        />
        <text x="5" y="61" fontSize="8" fill="#646a73">基线</text>
        <text x="42" y="17" fontSize="8" fill="#1f2329">+300</text>
        <text x="77" y="12" fontSize="8" fill="#1f2329">+180</text>
        <text x="111" y="9" fontSize="8" fill="#1f2329">+120</text>
        <text x="146" y="10" fontSize="8" fill="#1f2329">-110</text>
        <text x="177" y="8" fontSize="8" fill="#1f2329">1,290</text>
        <text x="178" y="61" fontSize="8" fill="#646a73">实际</text>
      </svg>
    </div>
  )
}

function GmvTrendMiniChart() {
  return (
    <div className="rounded border bg-background px-2 py-1.5" aria-label="GMV 趋势与活动发薪日小图">
      <p className="truncate text-[11px] font-semibold">GMV 趋势 + 活动/发薪日</p>
      <svg className="mt-1 h-[72px] w-full" viewBox="0 0 190 54" role="img" aria-label="GMV 趋势线，含活动期和发薪日标记">
        <line x1="8" y1="42" x2="182" y2="42" stroke="#d9dde3" />
        <line x1="8" y1="30" x2="182" y2="30" stroke="#eef0f3" strokeDasharray="4 3" />
        <line x1="8" y1="18" x2="182" y2="18" stroke="#eef0f3" strokeDasharray="4 3" />
        {[28, 72, 116, 160].map((x) => (
          <rect key={x} x={x} y="8" width="10" height="34" fill="#fde7cf" opacity="0.9" />
        ))}
        <polyline
          points="8,39 20,37 31,29 42,31 54,25 66,32 78,17 90,22 102,35 114,28 126,21 138,33 150,18 162,25 174,36 182,31"
          fill="none"
          stroke="#1d6ff2"
          strokeLinecap="round"
          strokeLinejoin="round"
          strokeWidth="2"
        />
        {[52, 96, 144].map((x) => (
          <circle key={x} cx={x} cy="41" r="2.5" fill="#d92929" />
        ))}
      </svg>
    </div>
  )
}

function ActivityLiftMiniBars() {
  return (
    <div className="rounded border bg-background px-2 py-1.5" aria-label="活动期与非活动期对比小图">
      <p className="truncate text-[11px] font-semibold">活动期 vs 非活动期</p>
      <svg className="mt-1 h-[72px] w-full" viewBox="0 0 142 54" role="img" aria-label="活动期 GMV、订单、转化、曝光高于非活动期">
        <line x1="8" y1="42" x2="134" y2="42" stroke="#d9dde3" />
        {[
          [16, 15, 29],
          [47, 22, 35],
          [78, 26, 33],
          [109, 8, 21],
        ].map(([x, blueTop, grayTop]) => (
          <g key={x}>
            <rect x={x} y={blueTop} width="10" height={42 - blueTop} rx="1.5" fill="#3b82f6" />
            <rect x={x + 12} y={grayTop} width="10" height={42 - grayTop} rx="1.5" fill="#c8ccd3" />
          </g>
        ))}
        <text x="13" y="52" fontSize="8" fill="#646a73">GMV</text>
        <text x="46" y="52" fontSize="8" fill="#646a73">订单</text>
        <text x="76" y="52" fontSize="8" fill="#646a73">转化</text>
        <text x="108" y="52" fontSize="8" fill="#646a73">曝光</text>
      </svg>
    </div>
  )
}

function UpliftBubbleMiniChart() {
  return (
    <div className="rounded border bg-background px-2 py-1.5" aria-label="品类策略四象限气泡图">
      <svg className="h-[156px] w-full" viewBox="0 0 210 124" role="img" aria-label="增量贡献和效果改善四象限">
        <line x1="18" y1="104" x2="198" y2="104" stroke="#8a8f99" />
        <line x1="18" y1="104" x2="18" y2="14" stroke="#8a8f99" />
        <line x1="102" y1="14" x2="102" y2="104" stroke="#8a8f99" strokeDasharray="5 4" />
        <line x1="18" y1="58" x2="198" y2="58" stroke="#8a8f99" strokeDasharray="5 4" />
        <text x="36" y="32" fontSize="10" fill="#1d6ff2">小规模试验</text>
        <text x="36" y="86" fontSize="10" fill="#1d6ff2">减少投入</text>
        <text x="164" y="32" fontSize="10" fill="#1d6ff2">优先加码</text>
        <text x="164" y="86" fontSize="10" fill="#1d6ff2">保护盘</text>
        <circle cx="158" cy="36" r="22" fill="#60a5fa" opacity="0.82" stroke="#2563eb" />
        <circle cx="124" cy="44" r="13" fill="#bde27b" opacity="0.9" />
        <circle cx="140" cy="75" r="14" fill="#f6b75e" opacity="0.88" />
        <circle cx="62" cy="39" r="12" fill="#b7d5fb" opacity="0.9" />
        <text x="148" y="40" fontSize="11" fill="#0f172a">饮料</text>
        <text x="116" y="48" fontSize="10" fill="#0f172a">零食</text>
        <text x="132" y="79" fontSize="10" fill="#0f172a">生鲜</text>
        <text x="54" y="43" fontSize="10" fill="#0f172a">母婴</text>
      </svg>
    </div>
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
          <p className="max-h-8 overflow-hidden text-xs leading-4 text-muted-foreground">{subtitle}</p>
        </div>
      </div>
      {badge && <TonePill tone={tone}>{badge}</TonePill>}
    </div>
  )
}

function MiniMetric({ label, value, tone }: { label: string; value: string; tone: MetricTone }) {
  return (
    <div className="rounded border bg-background px-2 py-1">
      <p className="truncate text-[11px] text-muted-foreground">{label}</p>
      <p className={`mt-0.5 max-h-7 overflow-hidden text-xs font-semibold leading-[14px] ${toneTextClass(tone)}`}>{value}</p>
    </div>
  )
}

function MiniInsight({ primary, secondary }: { primary: string; secondary: string }) {
  return (
    <div className="rounded border bg-secondary/25 px-2 py-1.5">
      <p className="max-h-14 overflow-hidden text-xs leading-[18px]">{primary}</p>
      <p className="mt-1 truncate text-[11px] text-muted-foreground">{secondary}</p>
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
