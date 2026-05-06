'use client'

import { useState, type ReactNode } from 'react'
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
          <DecisionSection snapshot={snapshot} loading={loading} />
          <DidSection did={snapshot.did} latestReport={latestReport} totalArtifacts={summary.total} />
          <PeriodSection periods={snapshot.periods} metricLabel={snapshot.trend.metricLabel} />
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
        <ParetoMiniChart />
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
  did,
  latestReport,
  totalArtifacts,
}: {
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
        <LocalGapMiniChart />
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
  periods,
  metricLabel,
}: {
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
        <PeriodCompositeChart />
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

function UpliftSection({ quadrants }: { quadrants: UpliftQuadrantSnapshot[] }) {
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
        <UpliftBubbleMiniChart />
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

function ParetoMiniChart() {
  return (
    <ChartFrame title="品类 GMV Pareto" ariaLabel="品类GMV Pareto 小图">
      <svg className="h-full w-full" viewBox="0 0 220 76" role="img" aria-label="饮料、零食、生鲜、母婴、家清的 GMV 和累计占比">
        <text x="2" y="7" fontSize="7.5" fontWeight="600" fill="#1f2329">品类 GMV Pareto</text>
        <text x="2" y="15" fontSize="6.5" fill="#3f4652">GMV(万元)</text>
        <text x="164" y="15" fontSize="6.5" fill="#3f4652">累计占比(%)</text>
        {[22, 34, 46, 58].map((y) => (
          <line key={y} x1="28" y1={y} x2="188" y2={y} stroke="#e5e7eb" strokeDasharray="3 3" />
        ))}
        <line x1="28" y1="20" x2="28" y2="58" stroke="#9aa1aa" />
        <line x1="188" y1="20" x2="188" y2="58" stroke="#9aa1aa" />
        <line x1="28" y1="58" x2="188" y2="58" stroke="#9aa1aa" />
        <text x="13" y="60" fontSize="6" fill="#646a73">0</text>
        <text x="3" y="48" fontSize="6" fill="#646a73">800</text>
        <text x="0" y="24" fontSize="6" fill="#646a73">2,400</text>
        <text x="192" y="60" fontSize="6" fill="#646a73">0%</text>
        <text x="192" y="48" fontSize="6" fill="#646a73">40%</text>
        <text x="192" y="24" fontSize="6" fill="#646a73">100%</text>
        {[
          [42, 24, 34, '饮料'],
          [72, 32, 26, '零食'],
          [102, 42, 16, '生鲜'],
          [132, 51, 7, '母婴'],
          [162, 54, 4, '家清'],
        ].map(([x, y, h, label]) => (
          <g key={label}>
            <rect x={Number(x)} y={Number(y)} width="13" height={Number(h)} rx="1.5" fill="#3b82f6" opacity={label === '饮料' ? 1 : 0.82} />
            <text x={Number(x) - 1} y="66" fontSize="6.2" fill="#646a73">{label}</text>
          </g>
        ))}
        <polyline points="48,42 78,33 108,27 138,23 168,21" fill="none" stroke="#1d4ed8" strokeWidth="1.7" />
        {[48, 78, 108, 138, 168].map((x, index) => (
          <circle key={x} cx={x} cy={[42, 33, 27, 23, 21][index]} r="2" fill="#1d4ed8" />
        ))}
        <rect x="64" y="70" width="6" height="4" fill="#3b82f6" />
        <text x="73" y="74" fontSize="6" fill="#646a73">GMV</text>
        <line x1="111" y1="72" x2="124" y2="72" stroke="#1d4ed8" strokeWidth="1.4" />
        <circle cx="118" cy="72" r="1.7" fill="#1d4ed8" />
        <text x="128" y="74" fontSize="6" fill="#646a73">累计占比</text>
      </svg>
    </ChartFrame>
  )
}

function LocalGapMiniChart() {
  return (
    <ChartFrame title="LocalGap 增量拆解" ariaLabel="LocalGap 增量瀑布小图">
      <svg className="h-full w-full" viewBox="0 0 230 76" role="img" aria-label="基线 GMV 到实际 GMV 的增量瀑布">
        <text x="2" y="7" fontSize="7.5" fontWeight="600" fill="#1f2329">LocalGap 增量拆解</text>
        <text x="2" y="15" fontSize="6.5" fill="#3f4652">GMV(万元)</text>
        {[22, 34, 46, 58].map((y) => (
          <line key={y} x1="30" y1={y} x2="220" y2={y} stroke="#e5e7eb" strokeDasharray="3 3" />
        ))}
        <line x1="30" y1="20" x2="30" y2="58" stroke="#9aa1aa" />
        <line x1="30" y1="58" x2="220" y2="58" stroke="#9aa1aa" />
        <text x="14" y="60" fontSize="6" fill="#646a73">0</text>
        <text x="4" y="47" fontSize="6" fill="#646a73">700</text>
        <text x="0" y="24" fontSize="6" fill="#646a73">1,400</text>
        {[
          [45, 40, 18, '#a8adb5', '800', '基线'],
          [76, 31, 27, '#55b95b', '+300', '曝光'],
          [107, 26, 20, '#55b95b', '+180', '折扣'],
          [138, 23, 14, '#55b95b', '+120', '发薪'],
          [169, 25, 12, '#d92929', '-110', '交互'],
          [200, 24, 34, '#9aa1aa', '1,290', '实际'],
        ].map(([x, y, h, color, value, label]) => (
          <g key={label}>
            <rect x={Number(x)} y={Number(y)} width="18" height={Number(h)} rx="1.4" fill={String(color)} />
            <text x={Number(x) - 1} y={Number(y) - 3} fontSize="6.5" fill="#1f2329">{value}</text>
            <text x={Number(x) - 1} y="67" fontSize="6.2" fill="#646a73">{label}</text>
          </g>
        ))}
        <polyline
          points="63,40 76,40 94,31 107,31 125,26 138,26 156,23 169,23 187,25 200,25"
          fill="none"
          stroke="#1f2329"
          strokeDasharray="4 3"
        />
      </svg>
    </ChartFrame>
  )
}

function PeriodCompositeChart() {
  return (
    <ChartFrame title="GMV 趋势 + 活动/发薪日" ariaLabel="活动前中后复合业务图">
      <svg className="h-full w-full" viewBox="0 0 236 84" role="img" aria-label="GMV 趋势、活动发薪日和活动期对比">
        <text x="2" y="7" fontSize="7.5" fontWeight="600" fill="#1f2329">GMV 趋势 + 活动/发薪日</text>
        <text x="2" y="15" fontSize="6.5" fill="#3f4652">GMV(万元)</text>
        {[20, 30, 40, 50].map((y) => (
          <line key={y} x1="28" y1={y} x2="154" y2={y} stroke="#e5e7eb" strokeDasharray="3 3" />
        ))}
        <line x1="28" y1="18" x2="28" y2="50" stroke="#9aa1aa" />
        <line x1="28" y1="50" x2="154" y2="50" stroke="#9aa1aa" />
        <text x="13" y="52" fontSize="5.8" fill="#646a73">0</text>
        <text x="3" y="22" fontSize="5.8" fill="#646a73">1,200</text>
        {[48, 86, 124].map((x) => (
          <rect key={x} x={x} y="19" width="7" height="31" fill="#fde7cf" opacity="0.9" />
        ))}
        <polyline
          points="28,46 36,44 45,38 54,39 62,34 70,38 78,23 86,29 94,44 102,38 110,32 118,41 126,22 134,29 142,45 154,38"
          fill="none"
          stroke="#1d6ff2"
          strokeLinecap="round"
          strokeLinejoin="round"
          strokeWidth="1.6"
        />
        {[58, 102, 142].map((x) => (
          <circle key={x} cx={x} cy="48" r="1.9" fill="#d92929" />
        ))}
        <text x="28" y="58" fontSize="5.8" fill="#646a73">04-01</text>
        <text x="82" y="58" fontSize="5.8" fill="#646a73">04-29</text>
        <text x="132" y="58" fontSize="5.8" fill="#646a73">06-03</text>
        <rect x="170" y="13" width="7" height="7" fill="#fde7cf" stroke="#efc89e" />
        <text x="180" y="19" fontSize="6" fill="#646a73">活动期</text>
        <circle cx="173" cy="31" r="2" fill="#d92929" />
        <text x="180" y="34" fontSize="6" fill="#646a73">发薪日</text>
        <line x1="168" y1="44" x2="181" y2="44" stroke="#1d6ff2" strokeWidth="1.4" />
        <text x="184" y="47" fontSize="6" fill="#646a73">GMV</text>
        <text x="2" y="68" fontSize="7" fill="#3f4652">活动 vs 非活动</text>
        <line x1="70" y1="74" x2="225" y2="74" stroke="#9aa1aa" />
        {[
          [78, 59, 66, 'GMV'],
          [112, 62, 68, '订单'],
          [146, 65, 70, '转化'],
          [180, 56, 63, '曝光'],
        ].map(([x, blueTop, grayTop, label]) => (
          <g key={label}>
            <rect x={Number(x)} y={Number(blueTop)} width="9" height={74 - Number(blueTop)} rx="1.2" fill="#3b82f6" />
            <rect x={Number(x) + 11} y={Number(grayTop)} width="9" height={74 - Number(grayTop)} rx="1.2" fill="#c8ccd3" />
            <text x={Number(x) - 2} y="82" fontSize="5.8" fill="#646a73">{label}</text>
          </g>
        ))}
        <rect x="8" y="75" width="6" height="4" fill="#3b82f6" />
        <text x="17" y="79" fontSize="6" fill="#646a73">活动期</text>
        <rect x="43" y="75" width="6" height="4" fill="#c8ccd3" />
        <text x="52" y="79" fontSize="6" fill="#646a73">非活动期</text>
      </svg>
    </ChartFrame>
  )
}

function UpliftBubbleMiniChart() {
  return (
    <ChartFrame ariaLabel="品类策略四象限气泡图">
      <svg className="h-full w-full" viewBox="0 0 230 80" role="img" aria-label="增量贡献和效果改善四象限">
        <defs>
          <marker id="axisArrow" markerHeight="5" markerWidth="5" orient="auto" refX="4" refY="2.5">
            <path d="M0,0 L5,2.5 L0,5 Z" fill="#8a8f99" />
          </marker>
        </defs>
        <text x="2" y="7" fontSize="7.5" fontWeight="600" fill="#1f2329">品类策略四象限</text>
        <line x1="28" y1="60" x2="212" y2="60" stroke="#8a8f99" markerEnd="url(#axisArrow)" />
        <line x1="28" y1="60" x2="28" y2="13" stroke="#8a8f99" markerEnd="url(#axisArrow)" />
        <line x1="119" y1="15" x2="119" y2="60" stroke="#8a8f99" strokeDasharray="5 4" />
        <line x1="28" y1="37" x2="212" y2="37" stroke="#8a8f99" strokeDasharray="5 4" />
        <text x="6" y="38" fontSize="7" fill="#1f2329" transform="rotate(-90 6 38)">效果改善</text>
        <text x="100" y="77" fontSize="7" fill="#1f2329">增量贡献</text>
        <text x="24" y="70" fontSize="6.3" fill="#1f2329">低</text>
        <text x="116" y="70" fontSize="6.3" fill="#1f2329">中</text>
        <text x="204" y="70" fontSize="6.3" fill="#1f2329">高</text>
        <text x="17" y="58" fontSize="6.3" fill="#1f2329">低</text>
        <text x="17" y="36" fontSize="6.3" fill="#1f2329">中</text>
        <text x="17" y="14" fontSize="6.3" fill="#1f2329">高</text>
        <text x="45" y="22" fontSize="7" fill="#1d6ff2">小规模试验</text>
        <text x="45" y="51" fontSize="7" fill="#1d6ff2">减少投入</text>
        <text x="178" y="22" fontSize="7" fill="#1d6ff2">优先加码</text>
        <text x="178" y="51" fontSize="7" fill="#1d6ff2">保护盘</text>
        <circle cx="166" cy="24" r="18" fill="#60a5fa" opacity="0.82" stroke="#2563eb" />
        <circle cx="133" cy="30" r="10" fill="#bde27b" opacity="0.9" />
        <circle cx="151" cy="49" r="11" fill="#f6b75e" opacity="0.88" />
        <circle cx="72" cy="23" r="10" fill="#b7d5fb" opacity="0.9" />
        <text x="157" y="27" fontSize="8.5" fill="#0f172a">饮料</text>
        <text x="126" y="33" fontSize="7.5" fill="#0f172a">零食</text>
        <text x="144" y="52" fontSize="7.5" fill="#0f172a">生鲜</text>
        <text x="65" y="26" fontSize="7.5" fill="#0f172a">母婴</text>
      </svg>
    </ChartFrame>
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
