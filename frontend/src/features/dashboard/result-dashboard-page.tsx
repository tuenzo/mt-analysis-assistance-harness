'use client'

import { useEffect, useId, useMemo, useRef, useState, type ReactNode } from 'react'
import * as echarts from 'echarts'
import {
  ArrowUpRight,
  CalendarDays,
  Check,
  ChevronDown,
  Download,
  Eye,
  Info,
  Layers,
  RotateCcw,
  Tag,
  Target,
  X,
  Zap,
} from 'lucide-react'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { ScaledPageFrame } from '@/components/ui/scaled-page-frame'
import type {
  DashboardFilters,
  DashboardSummary,
  KpiCardData,
  ParetoDatum,
  QuadrantItem,
  RecommendationGroup,
  SparklinePoint,
  TrendDatum,
  WaterfallDatum,
} from '@/types/dashboard'

const initialFilters: DashboardFilters = {
  timeRange: ['2025-05-06', '2025-06-04'],
  activityWindow: 'all',
  categoryLevel: 'all',
  calendarType: 'all',
}

const colorClass = {
  green: {
    tile: 'bg-green-50 text-green-700',
    border: 'border-green-200',
    text: 'text-green-600',
    accent: '#22c55e',
  },
  blue: {
    tile: 'bg-blue-50 text-blue-700',
    border: 'border-blue-200',
    text: 'text-blue-600',
    accent: '#3b82f6',
  },
  orange: {
    tile: 'bg-orange-50 text-orange-700',
    border: 'border-orange-200',
    text: 'text-orange-600',
    accent: '#f97316',
  },
  purple: {
    tile: 'bg-purple-50 text-purple-700',
    border: 'border-purple-200',
    text: 'text-purple-600',
    accent: '#8b5cf6',
  },
}

const categoryLevelByName: Record<string, DashboardFilters['categoryLevel']> = {
  饮料: 'top',
  零食: 'top',
  生鲜: 'mid',
  母婴: 'mid',
  乳品: 'mid',
  个护: 'mid',
  酒水: 'longtail',
  家清: 'longtail',
  粮油: 'longtail',
  其他: 'longtail',
}

function applyDashboardFilters(summary: DashboardSummary, filters: DashboardFilters): DashboardSummary {
  const trend = summary.trend.filter(
    (item) => matchesActivityWindow(item, filters.activityWindow) && matchesCalendarType(item, filters.calendarType),
  )
  const pareto = recalculatePareto(summary.pareto.filter((item) => matchesCategoryLevel(item.category, filters.categoryLevel)))
  const quadrants = summary.quadrants.filter((item) => matchesCategoryLevel(item.category, filters.categoryLevel))
  const recommendations = summary.recommendations.map((group) => {
    const categories = group.categories.filter((category) => matchesCategoryLevel(category, filters.categoryLevel))

    return {
      ...group,
      categories,
      count: categories.length,
      countLabel: `${categories.length} 个品类`,
    }
  })

  return {
    ...summary,
    kpis: buildFilteredKpis(summary.kpis, trend, recommendations),
    pareto,
    localGap: buildFilteredLocalGap(trend),
    trend,
    quadrants,
    recommendations,
  }
}

function matchesActivityWindow(item: TrendDatum, activityWindow: DashboardFilters['activityWindow']) {
  return activityWindow === 'all' || item.period === activityWindow
}

function matchesCalendarType(item: TrendDatum, calendarType: DashboardFilters['calendarType']) {
  if (calendarType === 'payday') return Boolean(item.isPayday)
  if (calendarType === 'nonpayday') return !item.isPayday
  return true
}

function matchesCategoryLevel(category: string, categoryLevel: DashboardFilters['categoryLevel']) {
  return categoryLevel === 'all' || categoryLevelByName[category] === categoryLevel
}

function recalculatePareto(data: ParetoDatum[]): ParetoDatum[] {
  const total = data.reduce((sum, item) => sum + item.gmv, 0)

  if (total <= 0) return data.map((item) => ({ ...item, cumulativeRatio: 0 }))

  return data
    .reduce<{ running: number; items: ParetoDatum[] }>(
      (acc, item) => {
        const running = acc.running + item.gmv
        return {
          running,
          items: [
            ...acc.items,
            {
              ...item,
              cumulativeRatio: Math.min(100, Math.round((running / total) * 100)),
            },
          ],
        }
      },
      { running: 0, items: [] },
    )
    .items
}

function buildFilteredKpis(
  kpis: KpiCardData[],
  trend: TrendDatum[],
  recommendations: RecommendationGroup[],
): KpiCardData[] {
  const netSeries = trend.map((item) => ({ label: item.date, value: item.gmv - item.baselineGmv }))
  const exposureSeries = trend.map((item) => ({ label: item.date, value: item.exposure ?? 0 }))
  const discountSeries = trend.map((item) => ({ label: item.date, value: item.discount ?? 0 }))
  const baselineTotal = sumTrendValue(trend, (item) => item.baselineGmv)
  const netTotal = sumSparklineValues(netSeries)
  const exposureTotal = sumSparklineValues(exposureSeries)
  const discountTotal = sumSparklineValues(discountSeries)
  const boostCount = recommendations.find((group) => group.key === 'boost')?.categories.length ?? 0

  return kpis.map((kpi) => {
    if (kpi.key === 'gmv_increment') {
      return {
        ...kpi,
        value: formatPlainNumber(netTotal),
        subText: `较基线 ${formatSignedPercent(netTotal, baselineTotal)}`,
        trendDirection: toTrendDirection(netTotal),
        series: netSeries,
      }
    }

    if (kpi.key === 'exposure_contribution') {
      return {
        ...kpi,
        value: formatSignedNumber(exposureTotal),
        subText: `占净增量 ${formatSharePercent(exposureTotal, netTotal)}`,
        trendDirection: toTrendDirection(exposureTotal),
        series: exposureSeries,
      }
    }

    if (kpi.key === 'discount_contribution') {
      return {
        ...kpi,
        value: formatSignedNumber(discountTotal),
        subText: `占净增量 ${formatSharePercent(discountTotal, netTotal)}`,
        trendDirection: toTrendDirection(discountTotal),
        series: discountSeries,
      }
    }

    if (kpi.key === 'boost_categories') {
      return {
        ...kpi,
        value: `${boostCount}`,
        subText: `当前筛选 ${boostCount} 个品类`,
        series: scaleBoostSeries(kpi.series, boostCount),
      }
    }

    return kpi
  })
}

function buildFilteredLocalGap(trend: TrendDatum[]): WaterfallDatum[] {
  const baseline = Math.round(sumTrendValue(trend, (item) => item.baselineGmv))
  const actual = Math.round(sumTrendValue(trend, (item) => item.gmv))
  const exposure = Math.round(sumTrendValue(trend, (item) => item.exposure ?? 0))
  const discount = Math.round(sumTrendValue(trend, (item) => item.discount ?? 0))
  const payday = Math.round(
    trend
      .filter((item) => item.isPayday)
      .reduce((sum, item) => sum + Math.max(0, item.gmv - item.baselineGmv) * 0.18, 0),
  )
  const residual = actual - baseline - exposure - discount - payday

  return [
    { name: '基线GMV', value: baseline, type: 'baseline' },
    { name: '曝光贡献', value: exposure, type: exposure >= 0 ? 'positive' : 'negative' },
    { name: '折扣贡献', value: discount, type: discount >= 0 ? 'positive' : 'negative' },
    { name: '发薪日贡献', value: payday, type: payday >= 0 ? 'positive' : 'negative' },
    { name: '交互/渠道', value: residual, type: residual >= 0 ? 'positive' : 'negative' },
    { name: '实际GMV', value: actual, type: 'total' },
  ]
}

function scaleBoostSeries(series: SparklinePoint[], boostCount: number) {
  const latest = series.at(-1)?.value ?? boostCount
  if (latest <= 0) return series.map((item) => ({ ...item, value: boostCount }))

  return series.map((item) => ({
    ...item,
    value: Math.max(0, Math.round((item.value * boostCount) / latest)),
  }))
}

function sumTrendValue(data: TrendDatum[], getValue: (item: TrendDatum) => number) {
  return data.reduce((sum, item) => sum + getValue(item), 0)
}

function sumSparklineValues(data: SparklinePoint[]) {
  return data.reduce((sum, item) => sum + item.value, 0)
}

function formatPlainNumber(value: number) {
  return Math.round(value).toLocaleString('en-US')
}

function formatSignedNumber(value: number) {
  const rounded = Math.round(value)
  return `${rounded > 0 ? '+' : ''}${rounded.toLocaleString('en-US')}`
}

function formatSignedPercent(numerator: number, denominator: number) {
  if (denominator === 0) return '+0.0%'
  const percent = (numerator / denominator) * 100
  return `${percent >= 0 ? '+' : ''}${percent.toFixed(1)}%`
}

function formatSharePercent(part: number, total: number) {
  if (total === 0) return '0.0%'
  return `${((part / total) * 100).toFixed(1)}%`
}

function toTrendDirection(value: number): KpiCardData['trendDirection'] {
  if (value > 0) return 'up'
  if (value < 0) return 'down'
  return 'flat'
}

export function ResultDashboardPage({ summary }: { summary: DashboardSummary }) {
  const [filters, setFilters] = useState<DashboardFilters>(initialFilters)
  const [drilldown, setDrilldown] = useState<string | null>(null)
  const [exportOpen, setExportOpen] = useState(false)
  const filteredSummary = useMemo(() => applyDashboardFilters(summary, filters), [summary, filters])

  return (
    <div className="h-full bg-background">
      <ScaledPageFrame
        designWidth={1620}
        designHeight={940}
        minScale={0.25}
        contentClassName="h-full"
      >
        <div className="flex h-full flex-col bg-background px-6 py-4">
          <DashboardFilterBar
            filters={filters}
            onChange={setFilters}
            onReset={() => setFilters(initialFilters)}
            onExport={() => setExportOpen(true)}
          />
          <CoreConclusionBanner conclusion={filteredSummary.conclusion} onExplain={() => setDrilldown('核心结论')} />
          <KpiSummaryStrip kpis={filteredSummary.kpis} onOpen={setDrilldown} />
          <DashboardMainGrid summary={filteredSummary} onOpen={setDrilldown} />
        </div>
      </ScaledPageFrame>

      <DashboardDrilldownDrawer
        open={Boolean(drilldown)}
        title={drilldown || ''}
        summary={filteredSummary}
        onClose={() => setDrilldown(null)}
      />
      <DashboardExportModal open={exportOpen} onClose={() => setExportOpen(false)} />
    </div>
  )
}

function DashboardFilterBar({
  filters,
  onChange,
  onReset,
  onExport,
}: {
  filters: DashboardFilters
  onChange: (filters: DashboardFilters) => void
  onReset: () => void
  onExport: () => void
}) {
  return (
    <div className="flex items-center justify-between gap-3">
      <div className="grid flex-1 grid-cols-4 gap-3">
        <FilterButton icon={<CalendarDays className="h-4 w-4" />} label="时间范围" value="最近 30 天（05.06~06.04）" />
        <FilterSelect
          icon={<Target className="h-4 w-4" />}
          label="活动窗口"
          value={filters.activityWindow}
          options={[
            ['all', '全部'],
            ['pre', '活动前'],
            ['during', '活动期中'],
            ['post', '活动后'],
          ]}
          onChange={(value) => onChange({ ...filters, activityWindow: value as DashboardFilters['activityWindow'] })}
        />
        <FilterSelect
          icon={<Layers className="h-4 w-4" />}
          label="品类维度"
          value={filters.categoryLevel}
          options={[
            ['all', '全部'],
            ['top', '头部'],
            ['mid', '中腰部'],
            ['longtail', '长尾'],
          ]}
          onChange={(value) => onChange({ ...filters, categoryLevel: value as DashboardFilters['categoryLevel'] })}
        />
        <FilterSelect
          icon={<CalendarDays className="h-4 w-4" />}
          label="日历类型"
          value={filters.calendarType}
          options={[
            ['all', '全部'],
            ['payday', '发薪日'],
            ['nonpayday', '非发薪日'],
          ]}
          onChange={(value) => onChange({ ...filters, calendarType: value as DashboardFilters['calendarType'] })}
        />
      </div>
      <div className="flex shrink-0 gap-2">
        <Button variant="outline" onClick={onReset}>
          <RotateCcw className="mr-2 h-4 w-4" />
          重置
        </Button>
        <Button onClick={onExport}>
          <Download className="mr-2 h-4 w-4" />
          导出
        </Button>
      </div>
    </div>
  )
}

function FilterButton({ icon, label, value }: { icon: ReactNode; label: string; value: string }) {
  return (
    <button className="flex h-12 items-center gap-3 rounded-xl border border-border bg-white px-4 text-left shadow-sm">
      <span className="text-[#1f2937]">{icon}</span>
      <span className="min-w-0">
        <span className="block text-[11px] font-semibold text-muted-foreground">{label}</span>
        <span className="block truncate text-sm font-bold">{value}</span>
      </span>
    </button>
  )
}

function FilterSelect({
  icon,
  label,
  value,
  options,
  onChange,
}: {
  icon: ReactNode
  label: string
  value: string
  options: Array<[string, string]>
  onChange: (value: string) => void
}) {
  const [open, setOpen] = useState(false)
  const selectedLabel = options.find(([optionValue]) => optionValue === value)?.[1] ?? value

  return (
    <div className="relative">
      <button
        type="button"
        data-filter-select={label}
        onClick={() => setOpen((current) => !current)}
        onBlur={() => window.setTimeout(() => setOpen(false), 120)}
        className={`flex h-12 w-full items-center gap-3 rounded-xl border bg-white px-4 text-left shadow-sm transition ${
          open ? 'border-[#f2cf4a] ring-2 ring-[#fff1a8]' : 'border-border hover:border-[#f2cf4a]'
        }`}
      >
        <span className="text-[#1f2937]">{icon}</span>
        <span className="min-w-0 flex-1">
          <span className="block text-[11px] font-semibold text-muted-foreground">{label}</span>
          <span className="block truncate text-sm font-bold">{selectedLabel}</span>
        </span>
        <ChevronDown className={`h-4 w-4 text-muted-foreground transition ${open ? 'rotate-180' : ''}`} />
      </button>

      {open && (
        <div
          className="absolute left-0 right-0 top-[calc(100%+6px)] z-50 rounded-xl border border-border bg-white p-1 shadow-[0_16px_36px_rgba(15,23,42,0.16)]"
          onMouseDown={(event) => event.preventDefault()}
        >
          {options.map(([optionValue, optionLabel]) => (
            <button
              key={optionValue}
              type="button"
              data-filter-option={optionValue}
              onClick={() => {
                onChange(optionValue)
                setOpen(false)
              }}
              className={`flex w-full items-center justify-between rounded-lg px-3 py-2 text-sm font-semibold transition ${
                value === optionValue ? 'bg-secondary text-[#8a6a00]' : 'text-[#1f2937] hover:bg-[#f7f8fa]'
              }`}
            >
              <span>{optionLabel}</span>
              {value === optionValue && <Check className="h-4 w-4" />}
            </button>
          ))}
        </div>
      )}
    </div>
  )
}

function CoreConclusionBanner({ conclusion, onExplain }: { conclusion: string; onExplain: () => void }) {
  return (
    <section className="mt-4 flex items-center justify-between gap-3 rounded-xl border border-blue-200 bg-gradient-to-r from-blue-50 to-white px-5 py-3 text-blue-950">
      <div className="flex min-w-0 items-center gap-3">
        <span className="flex h-9 w-9 shrink-0 items-center justify-center rounded-full bg-blue-100 text-blue-600">
          <Target className="h-5 w-5" />
        </span>
        <p className="text-base font-bold">核心结论：{conclusion}</p>
      </div>
      <Button variant="outline" size="sm" className="bg-white" onClick={onExplain}>
        查看结论说明
      </Button>
    </section>
  )
}

function KpiSummaryStrip({ kpis, onOpen }: { kpis: KpiCardData[]; onOpen: (title: string) => void }) {
  return (
    <section className="mt-3 grid grid-cols-4 gap-3">
      {kpis.map((kpi) => (
        <KpiCard key={kpi.key} kpi={kpi} onClick={() => onOpen(kpi.label)} />
      ))}
    </section>
  )
}

function KpiCard({ kpi, onClick }: { kpi: KpiCardData; onClick: () => void }) {
  const color = colorClass[kpi.color]
  return (
    <button
      type="button"
      onClick={onClick}
      className={`min-h-[92px] rounded-2xl border ${color.border} bg-white px-4 py-3 text-left shadow-[var(--shadow-soft)] transition hover:-translate-y-0.5 hover:shadow-lg`}
    >
      <div className="flex items-center gap-3">
        <span className={`rounded-lg p-1.5 ${color.tile}`}>
          {kpi.color === 'green' ? <Zap className="h-4 w-4" /> : kpi.color === 'blue' ? <Eye className="h-4 w-4" /> : kpi.color === 'orange' ? <Tag className="h-4 w-4" /> : <ArrowUpRight className="h-4 w-4" />}
        </span>
        <div className="min-w-0 flex-1">
          <p className="truncate text-sm font-bold">{kpi.label}</p>
          <div className="mt-1 flex items-end gap-1">
            <span className="text-2xl font-bold tracking-normal">{kpi.value}</span>
            {kpi.unit && <span className="mb-1 text-sm font-semibold">{kpi.unit}</span>}
          </div>
          <p className={`mt-0.5 truncate text-xs font-semibold ${color.text}`}>{kpi.subText}</p>
        </div>
        <div className="flex w-32 shrink-0 items-center justify-end">
          <Sparkline
            data={kpi.series}
            color={kpi.color}
            type={kpi.chartType}
            signed={kpi.signed}
            showArea={kpi.chartType === 'line'}
          />
        </div>
      </div>
    </button>
  )
}

function DashboardMainGrid({ summary, onOpen }: { summary: DashboardSummary; onOpen: (title: string) => void }) {
  return (
    <section className="mt-3 grid flex-1 items-stretch gap-4 xl:grid-cols-[minmax(0,1.18fr)_minmax(0,1.18fr)_320px]">
      <div className="grid content-start gap-4">
        <ParetoChartCard data={summary.pareto} onOpen={onOpen} />
        <GmvTrendComparisonCard data={summary.trend} onOpen={onOpen} />
      </div>
      <div className="grid content-start gap-4">
        <LocalGapWaterfallCard data={summary.localGap} onOpen={onOpen} />
        <StrategyQuadrantCard data={summary.quadrants} onOpen={onOpen} />
      </div>
      <RecommendationPanel groups={summary.recommendations} onOpen={onOpen} className="h-full" />
    </section>
  )
}

function ChartCard({
  title,
  children,
  footer,
  onOpen,
}: {
  title: string
  children: ReactNode
  footer?: ReactNode
  onOpen?: () => void
}) {
  return (
    <article className="rounded-2xl border border-border bg-white p-3 shadow-[var(--shadow-soft)]">
      <ChartCardHeader title={title} onOpen={onOpen} />
      {children}
      {footer}
    </article>
  )
}

function ChartCardHeader({ title, onOpen }: { title: string; onOpen?: () => void }) {
  return (
    <div className="mb-3 flex items-center justify-between gap-3">
      <h2 className="text-base font-bold">{title}</h2>
      <button
        type="button"
        className="rounded-full p-1 text-muted-foreground hover:bg-[#f7f8fa] hover:text-blue-600"
        title={`${title} 明细`}
        aria-label={`${title} 明细`}
        onClick={onOpen}
      >
        <Info className="h-4 w-4" />
      </button>
    </div>
  )
}

function ParetoChartCard({ data, onOpen }: { data: ParetoDatum[]; onOpen: (title: string) => void }) {
  const chartTop = 16
  const chartBottom = 154
  const chartHeight = chartBottom - chartTop
  const plotLeft = 35
  const plotRight = 590
  const rightAxisX = 598
  const gmvAxisMax = Math.max(600, Math.ceil(Math.max(...data.map((item) => item.gmv), 1) / 600) * 600)
  const gmvTicks = Array.from({ length: 5 }, (_, index) => Math.round((gmvAxisMax / 4) * index))
  const xForIndex = (index: number) => {
    if (data.length <= 1) return (plotLeft + plotRight) / 2
    return plotLeft + 22 + (index / (data.length - 1)) * (plotRight - plotLeft - 44)
  }
  const barWidth = data.length <= 2 ? 42 : Math.max(18, Math.min(30, ((plotRight - plotLeft) / data.length) * 0.48))
  const points = data
    .map((item, index) => `${xForIndex(index)},${chartBottom - (item.cumulativeRatio / 100) * chartHeight}`)
    .join(' ')
  return (
    <ChartCard title="品类 GMV Pareto" onOpen={() => onOpen('品类 GMV Pareto')} footer={<InsightMiniPanel text="饮料和零食贡献接近 60% GMV，是活动资源优先验证对象。" />}>
      <svg viewBox="0 0 650 188" className="h-48 w-full" role="img" aria-label="品类 GMV Pareto">
        <text x="5" y="8" fontSize="11" fill="#374151">GMV（万元）</text>
        <text x="586" y="8" fontSize="11" fill="#374151">累计占比（%）</text>
        <line x1={plotLeft} y1={chartBottom} x2={plotRight} y2={chartBottom} stroke="#d9e1ec" />
        <line x1={rightAxisX} y1={chartTop} x2={rightAxisX} y2={chartBottom} stroke="#d9e1ec" />
        {gmvTicks.map((tick) => (
          <g key={tick}>
            <line x1={plotLeft} y1={chartBottom - (tick / gmvAxisMax) * chartHeight} x2={plotRight} y2={chartBottom - (tick / gmvAxisMax) * chartHeight} stroke="#eef2f7" />
            <text x="5" y={chartBottom + 4 - (tick / gmvAxisMax) * chartHeight} fontSize="10" fill="#6b7280">{tick}</text>
          </g>
        ))}
        {[0, 25, 50, 75, 100].map((tick) => {
          const y = chartBottom - (tick / 100) * chartHeight
          return (
            <g key={`ratio-${tick}`}>
              <line x1={rightAxisX} y1={y} x2={rightAxisX + 5} y2={y} stroke="#d9e1ec" />
              <text x={rightAxisX + 10} y={y + 4} fontSize="10" fill="#6b7280">{tick}%</text>
            </g>
          )
        })}
        {data.map((item, index) => {
          const height = (item.gmv / gmvAxisMax) * chartHeight
          const x = xForIndex(index) - barWidth / 2
          return (
            <g
              key={item.category}
              onClick={(event) => {
                event.stopPropagation()
                onOpen(item.category)
              }}
              className="cursor-pointer"
            >
              <rect x={x} y={chartBottom - height} width={barWidth} height={height} rx="4" fill="#60a5fa">
                <title>{`${item.category}: ${item.gmv} 万元`}</title>
              </rect>
              <text x={xForIndex(index)} y="180" textAnchor="middle" fontSize="11" fill="#374151">{item.category}</text>
            </g>
          )
        })}
        <polyline points={points} fill="none" stroke="#2563eb" strokeWidth="3" />
        {data.map((item, index) => (
          <circle key={`${item.category}-line`} cx={xForIndex(index)} cy={chartBottom - (item.cumulativeRatio / 100) * chartHeight} r="4" fill="#2563eb">
            <title>{`累计占比 ${item.cumulativeRatio}%`}</title>
          </circle>
        ))}
      </svg>
    </ChartCard>
  )
}

function LocalGapWaterfallCard({ data, onOpen }: { data: WaterfallDatum[]; onOpen: (title: string) => void }) {
  const chartTop = 14
  const chartBottom = 150
  const chartHeight = chartBottom - chartTop
  const barWidth = 70
  const step = 94
  const startX = 42
  const { bars } = data.reduce<{
    cumulative: number
    bars: Array<{
      item: WaterfallDatum
      x: number
      start: number
      end: number
    }>
  }>((acc, item, index) => {
    const x = startX + index * step
    const start = item.type === 'baseline' || item.type === 'total' ? 0 : acc.cumulative
    const end =
      item.type === 'baseline' || item.type === 'total'
        ? item.value
        : acc.cumulative + item.value

    return {
      cumulative: item.type === 'total' ? acc.cumulative : end,
      bars: [...acc.bars, { item, x, start, end }],
    }
  }, { cumulative: 0, bars: [] })
  const maxValue = Math.max(...bars.flatMap((bar) => [bar.start, bar.end]), 1)
  const chartMax = Math.ceil(maxValue / 400) * 400
  const scaleY = (value: number) => chartBottom - (value / chartMax) * chartHeight

  return (
    <ChartCard title="LocalGap 增量分解瀑布图" onOpen={() => onOpen('LocalGap 增量分解瀑布图')} footer={<InsightMiniPanel text="曝光贡献是主要增量来源，交互/渠道项提示需要复盘触达质量。" />}>
      <div className="mb-2 flex justify-end gap-3 text-xs text-muted-foreground">
        <Legend color="#22c55e" label="正向贡献" />
        <Legend color="#ef4444" label="负向贡献" />
        <Legend color="#9ca3af" label="基线/合计" />
      </div>
      <svg viewBox="0 0 635 188" className="h-48 w-full" role="img" aria-label="LocalGap 增量分解瀑布图">
        <text x="5" y="8" fontSize="11" fill="#374151">GMV（万元）</text>
        <line x1="34" y1={chartBottom} x2="610" y2={chartBottom} stroke="#d9e1ec" />
        {[0, 400, 800, 1200, 1600].map((tick) => {
          const y = scaleY(tick)
          return (
            <g key={tick}>
              <line x1="34" y1={y} x2="610" y2={y} stroke="#eef2f7" />
              <text x="5" y={y + 4} fontSize="10" fill="#6b7280">{tick}</text>
            </g>
          )
        })}
        {bars.slice(0, -1).map((bar, index) => {
          const nextBar = bars[index + 1]
          const y = scaleY(bar.end)
          return (
            <line
              key={`${bar.item.name}-connector`}
              x1={bar.x + barWidth}
              y1={y}
              x2={nextBar.x}
              y2={y}
              stroke="#94a3b8"
              strokeDasharray="4 4"
            />
          )
        })}
        {bars.map(({ item, x, start, end }) => {
          const top = Math.min(scaleY(start), scaleY(end))
          const height = Math.max(6, Math.abs(scaleY(start) - scaleY(end)))
          const color = item.type === 'positive' ? '#22c55e' : item.type === 'negative' ? '#ef4444' : '#9ca3af'
          const label = item.type === 'positive' ? `+${item.value}` : `${item.value}`
          return (
            <g
              key={item.name}
              onClick={(event) => {
                event.stopPropagation()
                onOpen(item.name)
              }}
              className="cursor-pointer"
            >
              <rect
                x={x}
                y={top}
                width={barWidth}
                height={height}
                rx="6"
                fill={color}
                className="transition hover:opacity-80"
              >
                <title>{`${item.name}: ${item.value}`}</title>
              </rect>
              <text x={x + barWidth / 2} y={top - 7} textAnchor="middle" fontSize="12" fontWeight="700" fill="#111827">
                {label}
              </text>
              <text x={x + barWidth / 2} y="177" textAnchor="middle" fontSize="11" fill="#374151">
                {item.name}
              </text>
            </g>
          )
        })}
      </svg>
    </ChartCard>
  )
}

function GmvTrendComparisonCard({ data, onOpen }: { data: TrendDatum[]; onOpen: (title: string) => void }) {
  const chartRef = useRef<HTMLDivElement>(null)
  const periodSummaries = buildPeriodSummaries(data)

  useEffect(() => {
    if (!chartRef.current) return

    const chart = echarts.init(chartRef.current, undefined, { renderer: 'svg' })
    chart.setOption(buildGmvTrendOption(data))
    const frame = window.requestAnimationFrame(() => chart.resize())

    return () => {
      window.cancelAnimationFrame(frame)
      chart.dispose()
    }
  }, [data])

  return (
    <ChartCard title="活动前中后：GMV 趋势与活动期对比" onOpen={() => onOpen('活动前中后：GMV 趋势与活动期对比')}>
      <div className="mb-2 flex justify-end gap-3 text-xs text-muted-foreground">
        <Legend color="#3b82f6" label="实际 GMV" />
        <Legend color="#9ca3af" label="自然基线" />
        <Legend color="#fed7aa" label="活动期窗口" />
        <Legend color="#ef4444" label="发薪日" />
      </div>
      <div className="grid grid-cols-[minmax(0,1fr)_150px] gap-3">
        <div
          ref={chartRef}
          className="h-48 min-w-0"
          role="img"
          aria-label="活动前中后 GMV 趋势与活动期对比"
        />
        <div className="grid content-start gap-2">
          {periodSummaries.map((summary) => (
            <button
              key={summary.label}
              onClick={(event) => {
                event.stopPropagation()
                onOpen(summary.label)
              }}
              className="rounded-xl border border-border bg-[#fbfcfe] px-3 py-2 text-left"
            >
              <p className="text-xs text-muted-foreground">{summary.label}</p>
              <p className="mt-1 text-sm font-bold">{summary.value}</p>
              <p className={`mt-1 text-xs font-semibold ${summary.tone}`}>{summary.delta}</p>
            </button>
          ))}
        </div>
      </div>
    </ChartCard>
  )
}

function buildGmvTrendOption(data: TrendDatum[]): echarts.EChartsOption {
  const dates = data.map((item) => item.date)
  const paydayPoints = data
    .filter((item) => item.isPayday)
    .map((item) => ({
      name: '发薪日',
      coord: [item.date, item.gmv],
      value: item.gmv,
    }))

  return {
    animation: false,
    grid: {
      left: 46,
      right: 18,
      top: 20,
      bottom: 32,
    },
    tooltip: {
      trigger: 'axis',
      axisPointer: {
        type: 'line',
      },
      formatter(params: unknown) {
        const items = Array.isArray(params) ? params : [params]

        return items
          .map((item) => {
            const point = item as { marker?: string; seriesName?: string; value?: number | string }
            const value =
              typeof point.value === 'number'
                ? point.value.toLocaleString()
                : point.value

            return `${point.marker ?? ''}${point.seriesName ?? ''}: ${value} 万元`
          })
          .join('<br/>')
      },
    },
    xAxis: {
      type: 'category',
      data: dates,
      boundaryGap: false,
      axisLine: {
        lineStyle: {
          color: '#d9e1ec',
        },
      },
      axisTick: {
        show: false,
      },
      axisLabel: {
        color: '#6b7280',
        fontSize: 11,
      },
    },
    yAxis: {
      type: 'value',
      name: 'GMV（万元）',
      nameTextStyle: {
        color: '#6b7280',
        fontSize: 11,
        align: 'left',
      },
      splitLine: {
        lineStyle: {
          color: '#eef2f7',
        },
      },
      axisLabel: {
        color: '#6b7280',
        fontSize: 11,
      },
    },
    series: [
      {
        name: '实际 GMV',
        type: 'line',
        data: data.map((item) => item.gmv),
        smooth: true,
        symbol: 'circle',
        symbolSize: 5,
        lineStyle: {
          width: 3,
          color: '#3b82f6',
        },
        itemStyle: {
          color: '#3b82f6',
        },
        areaStyle: {
          color: {
            type: 'linear',
            x: 0,
            y: 0,
            x2: 0,
            y2: 1,
            colorStops: [
              { offset: 0, color: 'rgba(59, 130, 246, 0.16)' },
              { offset: 1, color: 'rgba(59, 130, 246, 0.02)' },
            ],
          },
        },
        markArea: {
          silent: true,
          itemStyle: {
            color: 'rgba(251, 146, 60, 0.16)',
          },
          data: buildActivityMarkAreas(data),
        },
        markPoint: {
          symbol: 'circle',
          symbolSize: 8,
          itemStyle: {
            color: '#ef4444',
          },
          label: {
            show: false,
          },
          data: paydayPoints,
        },
      },
      {
        name: '自然基线',
        type: 'line',
        data: data.map((item) => item.baselineGmv),
        smooth: true,
        symbol: 'none',
        lineStyle: {
          width: 2,
          type: 'dashed',
          color: '#9ca3af',
        },
      },
    ],
  }
}

function buildActivityMarkAreas(data: TrendDatum[]) {
  const ranges: Array<[{ xAxis: string }, { xAxis: string }]> = []
  let start: string | null = null

  data.forEach((item, index) => {
    if (item.isActivityDay && start === null) {
      start = item.date
    }

    const next = data[index + 1]
    if (item.isActivityDay && (!next || !next.isActivityDay)) {
      ranges.push([{ xAxis: start ?? item.date }, { xAxis: item.date }])
      start = null
    }
  })

  return ranges
}

function buildPeriodSummaries(data: TrendDatum[]) {
  const preGmv = sumGmvByPeriod(data, 'pre')
  const duringGmv = sumGmvByPeriod(data, 'during')
  const postGmv = sumGmvByPeriod(data, 'post')

  return [
    {
      label: '活动前',
      value: `GMV ${formatGmv(preGmv)}`,
      delta: '基准阶段',
      tone: 'text-muted-foreground',
    },
    {
      label: '活动中',
      value: `GMV ${formatGmv(duringGmv)}`,
      delta: formatLift(duringGmv, preGmv),
      tone: 'text-blue-600',
    },
    {
      label: '活动后',
      value: `GMV ${formatGmv(postGmv)}`,
      delta: formatLift(postGmv, preGmv),
      tone: 'text-blue-600',
    },
  ]
}

function sumGmvByPeriod(data: TrendDatum[], period: TrendDatum['period']) {
  return data
    .filter((item) => item.period === period)
    .reduce((sum, item) => sum + item.gmv, 0)
}

function formatLift(current: number, base: number) {
  if (base === 0) return '+0.0%'
  const lift = ((current - base) / base) * 100
  return `${lift >= 0 ? '+' : ''}${lift.toFixed(1)}%`
}

function formatGmv(value: number) {
  return value.toLocaleString('en-US')
}

function StrategyQuadrantCard({ data, onOpen }: { data: QuadrantItem[]; onOpen: (title: string) => void }) {
  const visualLayout: Record<string, { x: number; y: number; size: number; color: string; textColor?: string }> = {
    饮料: { x: 78, y: 64, size: 54, color: '#60a5fa', textColor: '#0f172a' },
    零食: { x: 64, y: 60, size: 40, color: '#a3e635', textColor: '#1f2937' },
    个护: { x: 88, y: 59, size: 36, color: '#bfdbfe', textColor: '#1e3a8a' },
    母婴: { x: 28, y: 62, size: 36, color: '#bfdbfe', textColor: '#1e3a8a' },
    酒水: { x: 40, y: 65, size: 32, color: '#ddd6fe', textColor: '#312e81' },
    生鲜: { x: 57, y: 34, size: 34, color: '#fdba74', textColor: '#7c2d12' },
    乳品: { x: 67, y: 28, size: 30, color: '#bbf7d0', textColor: '#14532d' },
    家清: { x: 78, y: 31, size: 30, color: '#fde68a', textColor: '#713f12' },
    粮油: { x: 27, y: 31, size: 30, color: '#fda4af', textColor: '#7f1d1d' },
  }

  const laidOutData = data.map((item) => {
    const visual = visualLayout[item.category] ?? {
      x: Math.min(88, Math.max(22, item.x)),
      y: Math.min(72, Math.max(28, item.y)),
      size: Math.max(30, item.size),
      color: item.color,
    }
    return { ...item, visual }
  })

  return (
    <ChartCard title="品类策略四象限（气泡图）" onOpen={() => onOpen('品类策略四象限（气泡图）')}>
      <div className="relative h-60 overflow-hidden rounded-xl border border-border bg-[#fbfcfe]">
        <svg className="pointer-events-none absolute inset-0 h-full w-full" viewBox="0 0 100 100" preserveAspectRatio="none" aria-hidden="true">
          <line x1="14" y1="84" x2="92" y2="84" stroke="#94a3b8" strokeWidth="0.6" />
          <polyline points="89,81.5 92,84 89,86.5" fill="none" stroke="#94a3b8" strokeWidth="0.6" />
          <line x1="14" y1="84" x2="14" y2="14" stroke="#94a3b8" strokeWidth="0.6" />
          <polyline points="11.5,17 14,14 16.5,17" fill="none" stroke="#94a3b8" strokeWidth="0.6" />
          <line x1="53" y1="16" x2="53" y2="84" stroke="#cbd5e1" strokeDasharray="2 2" strokeWidth="0.65" />
          <line x1="14" y1="50" x2="92" y2="50" stroke="#cbd5e1" strokeDasharray="2 2" strokeWidth="0.65" />
          {[28, 40, 66, 80].map((x) => (
            <line key={`x-tick-${x}`} x1={x} y1="82.5" x2={x} y2="85.5" stroke="#cbd5e1" strokeWidth="0.45" />
          ))}
          {[28, 40, 62, 74].map((y) => (
            <line key={`y-tick-${y}`} x1="12.5" y1={y} x2="15.5" y2={y} stroke="#cbd5e1" strokeWidth="0.45" />
          ))}
        </svg>

        <QuadrantLabel className="left-[18%] top-3" text="小规模试验区" />
        <QuadrantLabel className="right-[5%] top-3" text="优先加码区" />
        <QuadrantLabel className="bottom-[34px] left-[18%]" text="减少投入区" />
        <QuadrantLabel className="bottom-[34px] right-[5%]" text="保护基本盘区" />

        <span className="absolute bottom-2 left-1/2 -translate-x-1/2 text-xs font-medium text-muted-foreground">增量贡献</span>
        <span className="absolute bottom-2 left-[14%] text-xs text-muted-foreground">低</span>
        <span className="absolute bottom-2 right-[6%] text-xs text-muted-foreground">高</span>
        <span className="absolute left-2 top-1/2 -translate-y-1/2 -rotate-90 text-xs font-medium text-muted-foreground">效果改善</span>
        <span className="absolute left-[5%] top-[14%] text-xs text-muted-foreground">高</span>
        <span className="absolute bottom-[14%] left-[5%] text-xs text-muted-foreground">低</span>

        {laidOutData.map((item) => (
          <button
            key={item.category}
            type="button"
            onClick={(event) => {
              event.stopPropagation()
              onOpen(item.category)
            }}
            className="absolute z-[1] flex -translate-x-1/2 -translate-y-1/2 items-center justify-center rounded-full border border-white text-[11px] font-bold leading-none shadow-[0_8px_18px_rgba(15,23,42,0.16)] transition hover:z-10 hover:scale-110"
            style={{
              left: `${item.visual.x}%`,
              top: `${100 - item.visual.y}%`,
              width: item.visual.size,
              height: item.visual.size,
              minWidth: item.visual.size,
              backgroundColor: item.visual.color,
              color: item.visual.textColor ?? '#111827',
              boxShadow:
                item.category === '饮料'
                  ? '0 12px 24px rgba(37, 99, 235, 0.28)'
                  : '0 8px 18px rgba(15, 23, 42, 0.16)',
            }}
            title={`${item.category}: ${item.suggestedAction}`}
          >
            <span className="whitespace-nowrap">{item.category}</span>
          </button>
        ))}
      </div>
    </ChartCard>
  )
}

function RecommendationPanel({
  groups,
  onOpen,
  className = '',
}: {
  groups: RecommendationGroup[]
  onOpen: (title: string) => void
  className?: string
}) {
  return (
    <aside className={`grid auto-rows-fr content-stretch gap-4 ${className}`}>
      {groups.map((group) => (
        <RecommendationCard key={group.key} group={group} onOpen={onOpen} />
      ))}
    </aside>
  )
}

function RecommendationCard({ group, onOpen }: { group: RecommendationGroup; onOpen: (title: string) => void }) {
  const color = colorClass[group.color]
  return (
    <article className={`flex min-h-0 flex-col rounded-2xl border ${color.border} bg-white p-3 shadow-[var(--shadow-soft)]`}>
      <div className="flex items-start justify-between gap-3">
        <div className="flex min-w-0 items-start gap-3">
          <span className={`rounded-xl p-2 ${color.tile}`}>
            <ArrowUpRight className="h-4 w-4" />
          </span>
          <div className="min-w-0">
            <h3 className="font-bold">{group.title}</h3>
            <p className="mt-1 overflow-hidden text-xs leading-4 text-muted-foreground [display:-webkit-box] [-webkit-box-orient:vertical] [-webkit-line-clamp:2]">{group.description}</p>
          </div>
        </div>
        <Badge variant="outline" className={`shrink-0 ${color.tile} ${color.border}`}>{group.countLabel}</Badge>
      </div>
      <div className="mt-2 flex flex-wrap gap-2">
        {group.categories.map((category) => (
          <button
            key={category}
            type="button"
            onClick={() => onOpen(category)}
            className="rounded-lg border border-border bg-[#fbfcfe] px-2 py-1 text-xs font-semibold hover:border-[#f2cf4a] hover:bg-secondary"
          >
            {category}
          </button>
        ))}
      </div>
      <button onClick={() => onOpen(group.title)} className="mt-auto pt-2 text-left text-xs font-bold text-blue-600">查看全部</button>
    </article>
  )
}

function DashboardDrilldownDrawer({
  open,
  title,
  summary,
  onClose,
}: {
  open: boolean
  title: string
  summary: DashboardSummary
  onClose: () => void
}) {
  if (!open) return null

  const kpi = summary.kpis.find((item) => item.label === title)

  return (
    <div className="fixed inset-0 z-40 bg-black/20" onClick={onClose}>
      <aside className="absolute right-0 top-0 h-full w-full max-w-2xl overflow-y-auto bg-white p-5 shadow-2xl" onClick={(event) => event.stopPropagation()}>
        <div className="flex items-center justify-between gap-3">
          <div>
            <h2 className="text-lg font-bold">{title} 明细</h2>
            <p className="mt-1 text-sm text-muted-foreground">
              {kpi ? getKpiSubtitle(kpi.key) : '按品类、指标与周期查看可解释贡献。'}
            </p>
          </div>
          <button className="rounded-lg p-2 hover:bg-[#f7f8fa]" onClick={onClose} aria-label="关闭">
            <X className="h-5 w-5" />
          </button>
        </div>
        {kpi ? (
          <KpiDrilldownContent kpi={kpi} summary={summary} />
        ) : (
          <GenericDrilldownContent title={title} />
        )}
        <div className="mt-5 flex justify-end gap-2">
          <Button variant="outline">导出明细</Button>
          <Button>询问 Agent</Button>
        </div>
      </aside>
    </div>
  )
}

function GenericDrilldownContent({ title }: { title: string }) {
  return (
    <>
        <div className="mt-5 grid grid-cols-3 gap-2">
          <FilterButton icon={<Tag className="h-4 w-4" />} label="品类" value={title} />
          <FilterButton icon={<Zap className="h-4 w-4" />} label="指标" value="GMV" />
          <FilterButton icon={<CalendarDays className="h-4 w-4" />} label="周期" value="活动期" />
        </div>
        <div className="mt-5 grid grid-cols-3 gap-3">
          <MiniDetail label="GMV" value="1,290 万" />
          <MiniDetail label="订单" value="42,180" />
          <MiniDetail label="转化" value="+8.4%" />
        </div>
        <div className="mt-5 rounded-2xl border border-border bg-[#fbfcfe] p-4">
          <h3 className="font-bold">贡献拆解</h3>
          {[
            ['曝光贡献', '+980 万', '75.9%'],
            ['折扣贡献', '+180 万', '14.0%'],
            ['发薪日贡献', '+120 万', '9.3%'],
            ['交互/残差', '-110 万', '-8.5%'],
          ].map(([name, value, ratio]) => (
            <div key={name} className="mt-3 grid grid-cols-3 rounded-lg bg-white px-3 py-2 text-sm">
              <span>{name}</span>
              <span className="font-bold">{value}</span>
              <span className="text-right text-muted-foreground">{ratio}</span>
            </div>
          ))}
        </div>
        <div className="mt-5 rounded-2xl border border-blue-200 bg-blue-50 p-4 text-sm leading-6 text-blue-950">
          <h3 className="font-bold">方法说明</h3>
          <p className="mt-2">LocalGap 以局部基线估计活动期自然增长，再将实际 GMV 与基线之间的差值拆解到曝光、折扣、发薪日和交互残差。</p>
        </div>
    </>
  )
}

function KpiDrilldownContent({ kpi, summary }: { kpi: KpiCardData; summary: DashboardSummary }) {
  const detail = buildKpiDetail(kpi, summary)
  const color = colorClass[kpi.color]

  return (
    <>
      <div className="mt-5 grid grid-cols-3 gap-2">
        <FilterButton icon={<Zap className="h-4 w-4" />} label="指标口径" value={detail.scope} />
        <FilterButton icon={<CalendarDays className="h-4 w-4" />} label="数据粒度" value={detail.granularity} />
        <FilterButton icon={<Target className="h-4 w-4" />} label="对照方式" value={detail.benchmark} />
      </div>

      <div className="mt-5 grid grid-cols-4 gap-3">
        {detail.metricCards.map((card) => (
          <MiniDetail key={card.label} label={card.label} value={card.value} />
        ))}
      </div>

      <section className="mt-5 rounded-2xl border border-border bg-[#fbfcfe] p-4">
        <div className="flex items-center justify-between gap-3">
          <div>
            <h3 className="font-bold">{detail.chartTitle}</h3>
            <p className="mt-1 text-xs text-muted-foreground">{detail.chartHint}</p>
          </div>
          <Badge variant="outline" className={`${color.tile} ${color.border}`}>
            {kpi.value}{kpi.unit ? ` ${kpi.unit}` : ''}
          </Badge>
        </div>
        <DetailSeriesChart
          series={kpi.series}
          color={kpi.color}
          type={kpi.chartType}
          signed={kpi.signed}
        />
      </section>

      {detail.tags.length > 0 && (
        <section className="mt-5 rounded-2xl border border-border bg-white p-4">
          <h3 className="font-bold">当前关联品类</h3>
          <div className="mt-3 flex flex-wrap gap-2">
            {detail.tags.map((tag) => (
              <span key={tag} className={`rounded-lg border px-2.5 py-1 text-xs font-semibold ${color.tile} ${color.border}`}>
                {tag}
              </span>
            ))}
          </div>
        </section>
      )}

      <DetailTable title={detail.tableTitle} columns={detail.columns} rows={detail.rows} />

      <div className={`mt-5 rounded-2xl border p-4 text-sm leading-6 ${color.border} ${color.tile}`}>
        <h3 className="font-bold">{detail.methodTitle}</h3>
        <p className="mt-2">{detail.methodText}</p>
      </div>
    </>
  )
}

function getKpiSubtitle(key: string) {
  if (key === 'gmv_increment') return '查看每日实际 GMV、自然基线与净增量的对应关系。'
  if (key === 'exposure_contribution') return '查看曝光资源在 LocalGap 分解中的每日贡献。'
  if (key === 'discount_contribution') return '查看折扣贡献的正负波动与零轴关系。'
  if (key === 'boost_categories') return '查看多轮分析快照中的优先加码品类数变化。'

  return '查看该指标在当前筛选条件下的明细口径。'
}

function buildKpiDetail(kpi: KpiCardData, summary: DashboardSummary) {
  const latest = kpi.series[kpi.series.length - 1]
  const peak = getMaxPoint(kpi.series)
  const min = getMinPoint(kpi.series)
  const negativeCount = kpi.series.filter((item) => item.value < 0).length
  const boostCategories = summary.recommendations.find((item) => item.key === 'boost')?.categories ?? []
  const baseMetricCards = [
    { label: '当前值', value: `${kpi.value}${kpi.unit ? ` ${kpi.unit}` : ''}` },
    { label: '最近点', value: latest ? formatDetailPoint(latest, kpi.unit) : '-' },
    { label: '峰值点', value: peak ? formatDetailPoint(peak, kpi.unit) : '-' },
    { label: '低点', value: min ? formatDetailPoint(min, kpi.unit) : '-' },
  ]

  if (kpi.key === 'gmv_increment') {
    return {
      scope: '实际 - 基线',
      granularity: '日度',
      benchmark: '自然基线',
      chartTitle: '每日 GMV 净增量走势',
      chartHint: '小图口径与卡片主值一致，展示 daily_actual_gmv - daily_baseline_gmv。',
      metricCards: [
        { label: '累计净增量', value: `${kpi.value} ${kpi.unit}` },
        { label: '最近日净增', value: latest ? formatSignedAmount(latest.value, '万') : '-' },
        { label: '峰值日期', value: peak ? `${peak.label} ${formatSignedAmount(peak.value, '万')}` : '-' },
        { label: '负向天数', value: `${negativeCount} 天` },
      ],
      tableTitle: '日度净增量明细',
      columns: ['日期', '实际 GMV', '自然基线', '净增量'],
      rows: summary.trend.map((item) => [
        item.date,
        formatPlainAmount(item.gmv, '万'),
        formatPlainAmount(item.baselineGmv, '万'),
        formatSignedAmount(item.gmv - item.baselineGmv, '万'),
      ]),
      tags: [],
      methodTitle: '口径说明',
      methodText: 'GMV 净增量按日计算为实际 GMV 减自然基线 GMV，累计后对应顶部卡片的 1,290 万元；它不等同于 GMV 总量曲线。',
    }
  }

  if (kpi.key === 'exposure_contribution') {
    return {
      scope: '曝光贡献',
      granularity: '日度',
      benchmark: 'LocalGap',
      chartTitle: '每日曝光贡献走势',
      chartHint: '曝光贡献是增量分解项，因此使用小柱表达每日贡献量。',
      metricCards: [
        { label: '累计曝光贡献', value: `${kpi.value} ${kpi.unit}` },
        { label: '最近日贡献', value: latest ? formatSignedAmount(latest.value, '万') : '-' },
        { label: '峰值贡献', value: peak ? `${peak.label} ${formatSignedAmount(peak.value, '万')}` : '-' },
        { label: '净增量占比', value: '75.9%' },
      ],
      tableTitle: '日度曝光贡献明细',
      columns: ['日期', '曝光贡献', '当日净增占比', '日历标记'],
      rows: summary.trend.map((item) => {
        const net = item.gmv - item.baselineGmv
        const exposure = item.exposure ?? 0

        return [
          item.date,
          formatSignedAmount(exposure, '万'),
          formatPercent(exposure, net),
          getCalendarLabel(item),
        ]
      }),
      tags: boostCategories,
      methodTitle: '口径说明',
      methodText: '曝光贡献来自 LocalGap / 归因分解中的 exposure contribution，表达曝光资源对每日净增量的拉动，不与 GMV 总量曲线混用。',
    }
  }

  if (kpi.key === 'discount_contribution') {
    return {
      scope: '折扣贡献',
      granularity: '日度',
      benchmark: '零轴',
      chartTitle: '每日折扣贡献走势',
      chartHint: '折扣贡献允许为负，因此趋势图保留 0 轴，区分拉动与拖累。',
      metricCards: [
        { label: '累计折扣贡献', value: `${kpi.value} ${kpi.unit}` },
        { label: '最近日贡献', value: latest ? formatSignedAmount(latest.value, '万') : '-' },
        { label: '负贡献天数', value: `${negativeCount} 天` },
        { label: '净增量占比', value: '14.0%' },
      ],
      tableTitle: '日度折扣贡献明细',
      columns: ['日期', '折扣贡献', '影响方向', '日历标记'],
      rows: summary.trend.map((item) => {
        const discount = item.discount ?? 0

        return [
          item.date,
          formatSignedAmount(discount, '万'),
          discount >= 0 ? '拉动净增量' : '压低净增量',
          getCalendarLabel(item),
        ]
      }),
      tags: summary.recommendations.find((item) => item.key === 'control_discount')?.categories ?? [],
      methodTitle: '口径说明',
      methodText: '折扣贡献来自增量分解中的 discount contribution。负值说明折扣效率不足或带来干扰，适合以 0 轴观察波动。',
    }
  }

  if (kpi.key === 'boost_categories') {
    return {
      scope: '分析快照',
      granularity: '每轮输出',
      benchmark: '上轮结果',
      chartTitle: '优先加码品类数快照趋势',
      chartHint: '该指标不是天然日度指标，展示多轮分析快照中被判定为优先加码的品类数。',
      metricCards: [
        { label: '当前加码品类', value: `${kpi.value} ${kpi.unit}` },
        { label: '最近快照', value: latest?.label ?? '-' },
        { label: '最高快照', value: peak ? `${peak.value} 个` : '-' },
        { label: '当前品类数', value: `${boostCategories.length} 个` },
      ],
      tableTitle: '分析快照记录',
      columns: ['快照日期', '优先加码品类数', '较上轮变化', '说明'],
      rows: kpi.series.map((item, index) => {
        const previous = kpi.series[index - 1]
        const delta = previous ? item.value - previous.value : 0

        return [
          item.label,
          `${item.value} 个`,
          `${delta >= 0 ? '+' : ''}${delta} 个`,
          index === kpi.series.length - 1 ? '当前看板使用结果' : '历史分析输出',
        ]
      }),
      tags: boostCategories,
      methodTitle: '口径说明',
      methodText: '优先加码品类数来自多轮分析快照中的 boost_category_count。若未来没有历史快照，可切换为当前优先品类 uplift score 分布。',
    }
  }

  return {
    scope: '当前指标',
    granularity: '当前筛选',
    benchmark: '看板口径',
    chartTitle: `${kpi.label}走势`,
    chartHint: '展示该指标在当前筛选条件下的序列变化。',
    metricCards: baseMetricCards,
    tableTitle: '指标明细',
    columns: ['标签', '数值'],
    rows: kpi.series.map((item) => [item.label, String(item.value)]),
    tags: [],
    methodTitle: '口径说明',
    methodText: '该指标使用当前看板数据口径生成。',
  }
}

function DetailSeriesChart({
  series,
  color,
  type,
  signed = false,
}: {
  series: SparklinePoint[]
  color: KpiCardData['color']
  type: KpiCardData['chartType']
  signed?: boolean
}) {
  const width = 620
  const height = 168
  const left = 34
  const right = 14
  const top = 18
  const bottom = 136
  const values = series.map((item) => item.value).filter(Number.isFinite)

  if (values.length === 0) {
    return <div className="mt-4 rounded-xl bg-white p-6 text-center text-sm text-muted-foreground">暂无趋势数据</div>
  }

  let min = Math.min(...values)
  let max = Math.max(...values)

  if (signed) {
    min = Math.min(min, 0)
    max = Math.max(max, 0)
  }

  if (min === max) {
    min -= 1
    max += 1
  }

  const xForIndex = (index: number) =>
    series.length === 1
      ? (left + width - right) / 2
      : left + (index / (series.length - 1)) * (width - left - right)
  const yForValue = (value: number) => top + (1 - (value - min) / (max - min)) * (bottom - top)
  const zeroY = yForValue(0)
  const palette = sparklinePalette[color]
  const points = series.map((item, index) => ({
    ...item,
    x: xForIndex(index),
    y: yForValue(item.value),
  }))
  const linePath = points.map((point, index) => `${index === 0 ? 'M' : 'L'} ${point.x} ${point.y}`).join(' ')
  const barWidth = Math.max(16, Math.min(34, (width - left - right) / Math.max(series.length, 1) - 18))
  const gridTicks = [min, (min + max) / 2, max]

  return (
    <svg viewBox={`0 0 ${width} ${height}`} className="mt-4 h-44 w-full" role="img" aria-label="指标明细趋势">
      {gridTicks.map((tick) => {
        const y = yForValue(tick)

        return (
          <g key={tick}>
            <line x1={left} x2={width - right} y1={y} y2={y} stroke="#eef2f7" />
            <text x="4" y={y + 4} fontSize="10" fill="#6b7280">
              {Math.round(tick)}
            </text>
          </g>
        )
      })}
      {signed && (
        <line x1={left} x2={width - right} y1={zeroY} y2={zeroY} stroke={palette.zero} strokeDasharray="4 4" />
      )}
      <line x1={left} x2={width - right} y1={bottom} y2={bottom} stroke="#d9e1ec" />
      {type === 'bar' ? (
        points.map((point) => {
          const baseY = signed ? zeroY : bottom
          const y = Math.min(point.y, baseY)

          return (
            <g key={point.label}>
              <rect
                x={point.x - barWidth / 2}
                y={y}
                width={barWidth}
                height={Math.max(3, Math.abs(baseY - point.y))}
                rx="5"
                fill={palette.stroke}
                opacity="0.72"
              />
              <text x={point.x} y={bottom + 18} textAnchor="middle" fontSize="10" fill="#6b7280">
                {point.label}
              </text>
            </g>
          )
        })
      ) : (
        <>
          <path d={linePath} fill="none" stroke={palette.stroke} strokeWidth="3" strokeLinecap="round" strokeLinejoin="round" />
          {points.map((point) => (
            <g key={point.label}>
              <circle cx={point.x} cy={point.y} r="4" fill="#ffffff" stroke={palette.stroke} strokeWidth="2" />
              <text x={point.x} y={bottom + 18} textAnchor="middle" fontSize="10" fill="#6b7280">
                {point.label}
              </text>
            </g>
          ))}
        </>
      )}
    </svg>
  )
}

function DetailTable({ title, columns, rows }: { title: string; columns: string[]; rows: string[][] }) {
  return (
    <section className="mt-5 rounded-2xl border border-border bg-[#fbfcfe] p-4">
      <h3 className="font-bold">{title}</h3>
      <div className="mt-3 overflow-hidden rounded-xl border border-border bg-white">
        <div className="grid bg-[#f7f8fa] px-3 py-2 text-xs font-bold text-muted-foreground" style={{ gridTemplateColumns: `repeat(${columns.length}, minmax(0, 1fr))` }}>
          {columns.map((column) => (
            <span key={column}>{column}</span>
          ))}
        </div>
        {rows.map((row, index) => (
          <div
            key={`${row.join('-')}-${index}`}
            className="grid border-t border-border px-3 py-2 text-sm"
            style={{ gridTemplateColumns: `repeat(${columns.length}, minmax(0, 1fr))` }}
          >
            {row.map((cell, cellIndex) => (
              <span key={`${cell}-${cellIndex}`} className={cell.startsWith('+') ? 'font-semibold text-green-600' : cell.startsWith('-') ? 'font-semibold text-red-500' : ''}>
                {cell}
              </span>
            ))}
          </div>
        ))}
      </div>
    </section>
  )
}

function getMaxPoint(series: SparklinePoint[]) {
  return series.reduce<SparklinePoint | null>((max, item) => (!max || item.value > max.value ? item : max), null)
}

function getMinPoint(series: SparklinePoint[]) {
  return series.reduce<SparklinePoint | null>((min, item) => (!min || item.value < min.value ? item : min), null)
}

function formatDetailPoint(point: SparklinePoint, unit?: string) {
  return `${point.label} ${point.value.toLocaleString('en-US')}${unit ? ` ${unit}` : ''}`
}

function formatSignedAmount(value: number, unit: string) {
  return `${value >= 0 ? '+' : ''}${value.toLocaleString('en-US')}${unit}`
}

function formatPlainAmount(value: number, unit: string) {
  return `${value.toLocaleString('en-US')}${unit}`
}

function formatPercent(value: number, base: number) {
  if (base === 0) return '0.0%'
  return `${((value / base) * 100).toFixed(1)}%`
}

function getCalendarLabel(item: TrendDatum) {
  if (item.isPayday) return '发薪日'
  if (item.isActivityDay) return '活动期'

  return item.period === 'pre' ? '活动前' : '活动后'
}

function DashboardExportModal({ open, onClose }: { open: boolean; onClose: () => void }) {
  const [format, setFormat] = useState('PDF')
  const [scope, setScope] = useState('当前看板')
  if (!open) return null
  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/25 p-4" onClick={onClose}>
      <section className="w-full max-w-md rounded-2xl bg-white p-5 shadow-2xl" onClick={(event) => event.stopPropagation()}>
        <div className="flex items-center justify-between">
          <h2 className="text-lg font-bold">导出看板</h2>
          <button className="rounded-lg p-2 hover:bg-[#f7f8fa]" onClick={onClose} aria-label="关闭导出">
            <X className="h-5 w-5" />
          </button>
        </div>
        <Selector title="导出格式" options={['PDF', 'Excel', 'PNG']} value={format} onChange={setFormat} />
        <Selector title="导出范围" options={['当前看板', '当前筛选结果', '全量分析结果']} value={scope} onChange={setScope} />
        <div className="mt-5 flex justify-end gap-2">
          <Button variant="outline" onClick={onClose}>取消</Button>
          <Button onClick={onClose}>确认导出</Button>
        </div>
      </section>
    </div>
  )
}

function Selector({ title, options, value, onChange }: { title: string; options: string[]; value: string; onChange: (value: string) => void }) {
  return (
    <div className="mt-5">
      <p className="text-sm font-bold">{title}</p>
      <div className="mt-2 grid grid-cols-3 gap-2">
        {options.map((option) => (
          <button
            key={option}
            type="button"
            onClick={() => onChange(option)}
            className={`rounded-xl border px-3 py-2 text-sm font-semibold ${value === option ? 'border-[#f2cf4a] bg-secondary' : 'border-border bg-white hover:bg-[#f7f8fa]'}`}
          >
            {option}
          </button>
        ))}
      </div>
    </div>
  )
}

const sparklinePalette: Record<
  KpiCardData['color'],
  { stroke: string; zero: string }
> = {
  green: {
    stroke: '#22c55e',
    zero: 'rgba(34, 197, 94, 0.28)',
  },
  blue: {
    stroke: '#3b82f6',
    zero: 'rgba(59, 130, 246, 0.28)',
  },
  orange: {
    stroke: '#f97316',
    zero: 'rgba(249, 115, 22, 0.28)',
  },
  purple: {
    stroke: '#8b5cf6',
    zero: 'rgba(139, 92, 246, 0.28)',
  },
}

function normalizeSparklinePoints(
  data: SparklinePoint[],
  width: number,
  height: number,
  signed: boolean,
) {
  const paddingX = 4
  const paddingY = 5
  const values = data.map((item) => item.value).filter(Number.isFinite)

  if (values.length === 0) {
    return {
      points: [],
      zeroY: height / 2,
    }
  }

  let min = Math.min(...values)
  let max = Math.max(...values)

  if (signed) {
    min = Math.min(min, 0)
    max = Math.max(max, 0)
  }

  if (min === max) {
    min -= 1
    max += 1
  }

  const innerWidth = width - paddingX * 2
  const innerHeight = height - paddingY * 2
  const points = data.map((item, index) => {
    const x =
      data.length === 1
        ? width / 2
        : paddingX + (index / (data.length - 1)) * innerWidth
    const y = paddingY + (1 - (item.value - min) / (max - min)) * innerHeight

    return {
      x,
      y,
      label: item.label,
      value: item.value,
    }
  })
  const zeroY = paddingY + (1 - (0 - min) / (max - min)) * innerHeight

  return { points, zeroY }
}

function Sparkline({
  data,
  color,
  type = 'line',
  width = 128,
  height = 48,
  signed = false,
  showArea = true,
}: {
  data: SparklinePoint[]
  color: KpiCardData['color']
  type?: KpiCardData['chartType']
  width?: number
  height?: number
  signed?: boolean
  showArea?: boolean
}) {
  const rawGradientId = useId()
  const gradientId = `sparkline-${rawGradientId.replace(/:/g, '')}`
  const palette = sparklinePalette[color]
  const { points, zeroY } = normalizeSparklinePoints(data, width, height, signed)

  if (points.length === 0) {
    return (
      <svg width={width} height={height} viewBox={`0 0 ${width} ${height}`} className="block overflow-visible">
        <text
          x={width / 2}
          y={height / 2}
          textAnchor="middle"
          dominantBaseline="middle"
          fontSize="11"
          fill="#9ca3af"
        >
          暂无数据
        </text>
      </svg>
    )
  }

  const linePath = points
    .map((point, index) => `${index === 0 ? 'M' : 'L'} ${point.x} ${point.y}`)
    .join(' ')
  const first = points[0]
  const last = points[points.length - 1]
  const baseY = signed ? zeroY : height - 5
  const areaPath = `${linePath} L ${last.x} ${baseY} L ${first.x} ${baseY} Z`
  const barWidth =
    points.length <= 1 ? 8 : Math.max(3, Math.min(8, width / points.length - 3))

  return (
    <svg
      width={width}
      height={height}
      viewBox={`0 0 ${width} ${height}`}
      className="block overflow-visible"
      role="img"
      aria-label="指标趋势"
    >
      <defs>
        <linearGradient id={gradientId} x1="0" y1="0" x2="0" y2="1">
          <stop offset="0%" stopColor={palette.stroke} stopOpacity="0.22" />
          <stop offset="100%" stopColor={palette.stroke} stopOpacity="0.02" />
        </linearGradient>
      </defs>

      {signed && (
        <line
          x1="0"
          x2={width}
          y1={zeroY}
          y2={zeroY}
          stroke={palette.zero}
          strokeDasharray="3 3"
          strokeWidth="1"
        />
      )}

      {type === 'bar' ? (
        points.map((point, index) => {
          const y = Math.min(point.y, baseY)
          const barHeight = Math.abs(baseY - point.y)

          return (
            <rect
              key={`${point.label}-${index}`}
              x={point.x - barWidth / 2}
              y={y}
              width={barWidth}
              height={Math.max(barHeight, 2)}
              rx="2"
              fill={palette.stroke}
              opacity="0.72"
            >
              <title>
                {point.label}: {point.value}
              </title>
            </rect>
          )
        })
      ) : (
        <>
          {showArea && <path d={areaPath} fill={`url(#${gradientId})`} />}
          <path
            d={linePath}
            fill="none"
            stroke={palette.stroke}
            strokeWidth="2.2"
            strokeLinecap="round"
            strokeLinejoin="round"
          />
          <circle
            cx={last.x}
            cy={last.y}
            r="3"
            fill="#ffffff"
            stroke={palette.stroke}
            strokeWidth="2"
          >
            <title>
              {last.label}: {last.value}
            </title>
          </circle>
        </>
      )}
    </svg>
  )
}

function InsightMiniPanel({ text }: { text: string }) {
  return (
    <div className="mt-3 rounded-xl border border-border bg-[#fbfcfe] px-3 py-2">
      <p className="text-xs font-bold">洞察</p>
      <p className="mt-1 text-xs leading-4 text-muted-foreground">{text}</p>
    </div>
  )
}

function Legend({ color, label }: { color: string; label: string }) {
  return (
    <span className="inline-flex items-center gap-1">
      <span className="h-2.5 w-2.5 rounded-sm" style={{ backgroundColor: color }} />
      {label}
    </span>
  )
}

function QuadrantLabel({ text, className }: { text: string; className: string }) {
  return <span className={`absolute text-xs font-bold text-blue-600 ${className}`}>{text}</span>
}

function MiniDetail({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-xl border border-border bg-[#fbfcfe] px-3 py-3">
      <p className="text-xs text-muted-foreground">{label}</p>
      <p className="mt-1 font-bold">{value}</p>
    </div>
  )
}
