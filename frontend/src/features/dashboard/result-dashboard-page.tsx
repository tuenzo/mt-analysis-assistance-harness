'use client'

import { useCallback, useEffect, useId, useMemo, useRef, useState, type ReactNode } from 'react'
import { useParams, useRouter } from 'next/navigation'
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
  MessageSquarePlus,
  RotateCcw,
  Tag,
  Target,
  X,
  Zap,
} from 'lucide-react'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { ScaledPageFrame } from '@/components/ui/scaled-page-frame'
import { createAgentHandoff } from '@/lib/agent-handoff'
import { useApiBaseHref } from '@/lib/use-api-base-href'
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

const defaultInitialFilters: DashboardFilters = {
  timeRange: ['', ''],
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

const WAN_UNIT_SCALE = 10000

function inferCurrencyScale(values: number[]) {
  const maxValue = Math.max(0, ...values.filter(Number.isFinite).map((value) => Math.abs(value)))
  return maxValue >= WAN_UNIT_SCALE ? WAN_UNIT_SCALE : 1
}

function formatCurrencyNumber(value: number, scale: number, signed = false) {
  const displayValue = value / scale
  const prefix = signed && value > 0 ? '+' : ''
  return `${prefix}${displayValue.toLocaleString('en-US', {
    maximumFractionDigits: 2,
  })}`
}

function formatScaledCurrencyNumber(value: number, scale: number, signed = false) {
  const prefix = signed && value > 0 ? '+' : ''
  return `${prefix}${value.toLocaleString('en-US', {
    maximumFractionDigits: 2,
  })}`
}

function normalizeCurrencyUnitLabel(unitLabel?: string) {
  const normalized = String(unitLabel || '').trim()
  if (!normalized || normalized.includes('原始单位')) return '元'
  return normalized
}

function currencyUnitForScale(scale: number, unitLabel?: string) {
  const baseUnit = normalizeCurrencyUnitLabel(unitLabel)
  if (scale === WAN_UNIT_SCALE && baseUnit === '元') return '万元'
  return baseUnit || (scale === WAN_UNIT_SCALE ? '万元' : '元')
}

function formatCurrencyWithUnit(value: number, scale: number, signed = false, unitLabel?: string) {
  return `${formatCurrencyNumber(value, scale, signed)} ${currencyUnitForScale(scale, unitLabel)}`
}

function summaryCurrencyScale(summary: DashboardSummary, values: number[]) {
  const baseUnit = normalizeCurrencyUnitLabel(summary.valueUnit)
  if (!summary.valueScale || summary.valueScale <= 1 || baseUnit === '元') return inferCurrencyScale(values)
  return summary.valueScale
}

function resolveCurrencyScale(unitScale: number | undefined, unitLabel: string | undefined, values: number[]) {
  const baseUnit = normalizeCurrencyUnitLabel(unitLabel)
  if (!unitScale || unitScale <= 1 || baseUnit === '元') return inferCurrencyScale(values)
  return unitScale
}

function summaryCurrencyUnit(summary: DashboardSummary, scale: number) {
  return currencyUnitForScale(scale, summary.valueUnit)
}

function getNiceAxisMax(maxValue: number) {
  if (maxValue <= 0) return 1
  const step = maxValue <= 10 ? 2 : maxValue <= 100 ? 20 : maxValue <= 1000 ? 200 : 400
  return Math.ceil(maxValue / step) * step
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
  一段婴儿奶粉: 'top',
  可乐汽水: 'top',
  夹心巧克力: 'top',
  方便面: 'top',
  洗衣液: 'mid',
  天然矿泉水: 'mid',
  '乳液/面霜': 'mid',
  '牙膏/牙粉': 'mid',
  一次性杯子: 'longtail',
  研磨咖啡: 'longtail',
  一次性手套: 'longtail',
  '保鲜膜/套': 'longtail',
  其他冰淇淋: 'longtail',
  黑巧克力: 'longtail',
}

function applyDashboardFilters(
  summary: DashboardSummary,
  filters: DashboardFilters,
  options: { preserveLocalGap?: boolean } = {},
): DashboardSummary {
  const trend = summary.trend.filter(
    (item) => matchesActivityWindow(item, filters.activityWindow) && matchesCalendarType(item, filters.calendarType),
  )
  const pareto = recalculatePareto(summary.pareto.filter((item) => matchesCategoryLevel(item.category, filters.categoryLevel)))
  const quadrants = summary.quadrants.filter(
    (item) => item.resourceType || matchesCategoryLevel(item.category, filters.categoryLevel),
  )
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
    kpis: buildFilteredKpis(summary, trend, recommendations),
    pareto,
    localGap: options.preserveLocalGap ? summary.localGap : buildFilteredLocalGap(trend),
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
  if (categoryLevel === 'all') return true
  const mappedLevel = categoryLevelByName[category]
  return mappedLevel ? mappedLevel === categoryLevel : true
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
  summary: DashboardSummary,
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
  const currencyScale = summaryCurrencyScale(
    summary,
    trend.flatMap((item) => [item.gmv, item.baselineGmv, item.exposure ?? 0, item.discount ?? 0]),
  )
  const currencyUnit = summaryCurrencyUnit(summary, currencyScale)
  const boostCount = recommendations.find((group) => group.key === 'boost')?.categories.length ?? 0

  return summary.kpis.map((kpi) => {
    if (kpi.key === 'gmv_increment') {
      return {
        ...kpi,
        value: formatCurrencyNumber(netTotal, currencyScale),
        unit: currencyUnit,
        subText: `较基线 ${formatSignedPercent(netTotal, baselineTotal)}`,
        trendDirection: toTrendDirection(netTotal),
        series: netSeries,
      }
    }

    if (kpi.key === 'exposure_contribution') {
      return {
        ...kpi,
        value: formatCurrencyNumber(exposureTotal, currencyScale, true),
        unit: currencyUnit,
        subText: `占净增量 ${formatSharePercent(exposureTotal, netTotal)}`,
        trendDirection: toTrendDirection(exposureTotal),
        series: exposureSeries,
      }
    }

    if (kpi.key === 'discount_contribution') {
      return {
        ...kpi,
        value: formatCurrencyNumber(discountTotal, currencyScale, true),
        unit: currencyUnit,
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

export function ResultDashboardPage({
  summary,
  initialFilters = defaultInitialFilters,
  timeRangeLabel,
  preserveLocalGap = false,
  showcaseLayout = false,
}: {
  summary: DashboardSummary
  initialFilters?: DashboardFilters
  timeRangeLabel?: string
  preserveLocalGap?: boolean
  showcaseLayout?: boolean
}) {
  const params = useParams<{ project_id: string }>()
  const router = useRouter()
  const hrefFor = useApiBaseHref()
  const projectId = params.project_id
  const [filters, setFilters] = useState<DashboardFilters>(initialFilters)
  const [drilldown, setDrilldown] = useState<string | null>(null)
  const [exportOpen, setExportOpen] = useState(false)
  const resolvedTimeRangeLabel = timeRangeLabel ?? summarizeTrendRange(summary.trend)

  const filteredSummary = useMemo(
    () => applyDashboardFilters(summary, filters, { preserveLocalGap }),
    [summary, filters, preserveLocalGap],
  )

  const handleAskAgent = useCallback(
    (title: string) => {
      const handoffId = createAgentHandoff({
        projectId,
        source: 'dashboard-drilldown',
        title,
        context: buildDashboardAgentHandoffContext(title, filteredSummary),
        suggestedQuestion: `请解释「${title}」这张看板卡片，并告诉我下一步应该重点验证什么。`,
      })
      if (!handoffId) {
        window.alert('无法创建看板上下文线程，请刷新后重试。')
        return
      }
      router.push(hrefFor(`/projects/${projectId}/agent?agent_handoff=${encodeURIComponent(handoffId)}`))
    },
    [filteredSummary, hrefFor, projectId, router],
  )

  return (
    <div className="h-full bg-background">
      <ScaledPageFrame
        designWidth={1620}
        designHeight={940}
        minScale={0.25}
        contentClassName="h-full"
      >
        <div className="flex h-full flex-col bg-background px-6 pb-0 pt-4">
          <DashboardFilterBar
            filters={filters}
            onChange={setFilters}
            onReset={() => setFilters(initialFilters)}
            onExport={() => setExportOpen(true)}
            timeRangeLabel={resolvedTimeRangeLabel}
          />
          <CoreConclusionBanner conclusion={filteredSummary.conclusion} onExplain={() => setDrilldown('核心结论')} />
          <KpiSummaryStrip kpis={filteredSummary.kpis} onOpen={setDrilldown} />
          <DashboardMainGrid summary={filteredSummary} onOpen={setDrilldown} showcaseLayout={showcaseLayout} />
        </div>
      </ScaledPageFrame>

      <DashboardDrilldownDrawer
        open={Boolean(drilldown)}
        title={drilldown || ''}
        summary={filteredSummary}
        onClose={() => setDrilldown(null)}
        onAskAgent={handleAskAgent}
      />
      <DashboardExportModal open={exportOpen} onClose={() => setExportOpen(false)} />
    </div>
  )
}

function summarizeTrendRange(trend: TrendDatum[]) {
  if (trend.length === 0) return '暂无真实分析时间范围'
  const first = trend[0]?.date
  const last = trend.at(-1)?.date
  if (!first || !last) return '暂无真实分析时间范围'
  return first === last ? first : `${first}~${last}`
}

function buildDashboardAgentHandoffContext(title: string, summary: DashboardSummary) {
  const currencyScale = summaryCurrencyScale(summary, [
    ...summary.pareto.map((item) => item.gmv),
    ...summary.trend.flatMap((item) => [item.gmv, item.baselineGmv, item.exposure ?? 0, item.discount ?? 0]),
    ...summary.localGap.map((item) => item.value),
  ])
  const currencyUnit = summaryCurrencyUnit(summary, currencyScale)
  const kpi = summary.kpis.find((item) => item.label === title)
  const paretoItem = summary.pareto.find((item) => item.category === title)
  const quadrantItem = summary.quadrants.find((item) => item.category === title)
  const recommendationGroups = summary.recommendations
    .filter((group) => group.title === title || group.categories.includes(title))
    .map((group) => `${group.title}(${group.countLabel})`)
  const localGapTotal = summary.localGap
    .filter((item) => item.type !== 'baseline' && item.type !== 'total')
    .reduce((sum, item) => sum + item.value, 0)
  const topPareto = summary.pareto.slice(0, 5).map((item) => `${item.category} ${formatCurrencyWithUnit(item.gmv, currencyScale, false, currencyUnit)}`)
  const lines = [
    `看板卡片：${title}`,
    `时间范围：${summarizeTrendRange(summary.trend)}`,
    `核心结论：${summary.conclusion}`,
    `质量状态：${summary.qualityStatus ?? 'unknown'}`,
    summary.qualityReasons?.length ? `质量提示：${summary.qualityReasons.slice(0, 3).join('；')}` : '',
    typeof localGapTotal === 'number' ? `LocalGap 总量：${formatCurrencyWithUnit(localGapTotal, currencyScale, true, currencyUnit)}` : '',
    kpi ? `KPI：${kpi.label} = ${kpi.value}${kpi.unit ? ` ${kpi.unit}` : ''}，${kpi.subText}` : '',
    paretoItem ? `品类 GMV：${paretoItem.category} = ${formatCurrencyWithUnit(paretoItem.gmv, currencyScale, false, currencyUnit)}，累计占比 ${paretoItem.cumulativeRatio}%` : '',
    quadrantItem
      ? `策略气泡：${quadrantItem.category}，动作：${quadrantItem.suggestedAction}，贡献：${formatCurrencyWithUnit(quadrantItem.contribution ?? 0, currencyScale, true, currencyUnit)}`
      : '',
    recommendationGroups.length ? `所属策略组：${recommendationGroups.join('；')}` : '',
    topPareto.length ? `Top GMV 品类：${topPareto.join('；')}` : '',
    `建议问题：解释这张卡片背后的证据、风险和下一步验证动作。`,
  ]

  return lines.filter(Boolean).join('\n')
}

function DashboardFilterBar({
  filters,
  onChange,
  onReset,
  onExport,
  timeRangeLabel,
}: {
  filters: DashboardFilters
  onChange: (filters: DashboardFilters) => void
  onReset: () => void
  onExport: () => void
  timeRangeLabel: string
}) {
  return (
    <div data-dashboard-filter-bar className="flex items-center justify-between gap-3">
      <div className="grid flex-1 grid-cols-4 gap-3">
        <FilterButton icon={<CalendarDays className="h-4 w-4" />} label="时间范围" value={timeRangeLabel} />
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
        <Button variant="outline" className="h-[62px] rounded-xl px-4 text-base font-bold" onClick={onReset}>
          <RotateCcw className="mr-2 h-4 w-4" />
          重置
        </Button>
        <Button className="h-[62px] rounded-xl px-5 text-base font-bold" onClick={onExport}>
          <Download className="mr-2 h-4 w-4" />
          导出
        </Button>
      </div>
    </div>
  )
}

function FilterButton({ icon, label, value }: { icon: ReactNode; label: string; value: string }) {
  return (
    <button className="flex h-[62px] items-center gap-3 rounded-xl border border-border bg-white px-4 text-left shadow-sm">
      <span className="text-[#1f2937]">{icon}</span>
      <span className="min-w-0">
        <span className="block text-[11px] font-semibold text-muted-foreground">{label}</span>
        <span className="block truncate text-base font-bold">{value}</span>
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
        className={`flex h-[62px] w-full items-center gap-3 rounded-xl border bg-white px-4 text-left shadow-sm transition ${
          open ? 'border-[#f2cf4a] ring-2 ring-[#fff1a8]' : 'border-border hover:border-[#f2cf4a]'
        }`}
      >
        <span className="text-[#1f2937]">{icon}</span>
        <span className="min-w-0 flex-1">
          <span className="block text-[11px] font-semibold text-muted-foreground">{label}</span>
          <span className="block truncate text-base font-bold">{selectedLabel}</span>
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
    <section data-dashboard-conclusion-banner className="mt-4 flex items-center justify-between gap-3 rounded-xl border border-blue-200 bg-gradient-to-r from-blue-50 to-white px-5 py-3 text-blue-950">
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

function DashboardMainGrid({
  summary,
  onOpen,
  showcaseLayout = false,
}: {
  summary: DashboardSummary
  onOpen: (title: string) => void
  showcaseLayout?: boolean
}) {
  return (
    <section
      data-dashboard-main-grid
      className="mt-3 grid min-h-0 flex-1 items-stretch gap-4 pb-4 xl:grid-cols-[minmax(0,1.18fr)_minmax(0,1.18fr)_320px]"
    >
      <div
        data-dashboard-left-column
        className={showcaseLayout ? 'grid h-full min-h-0 grid-rows-[auto_minmax(0,1fr)] gap-4' : 'grid content-start gap-4'}
      >
        <ParetoChartCard data={summary.pareto} onOpen={onOpen} unitLabel={summary.valueUnit} unitScale={summary.valueScale} />
        <GmvTrendComparisonCard data={summary.trend} onOpen={onOpen} stretchToFill={showcaseLayout} unitLabel={summary.valueUnit} unitScale={summary.valueScale} />
      </div>
      <div
        data-dashboard-middle-column
        className={showcaseLayout ? 'grid h-full min-h-0 grid-rows-[auto_minmax(0,1fr)] gap-4' : 'grid content-start gap-4'}
      >
        <LocalGapWaterfallCard data={summary.localGap} onOpen={onOpen} unitLabel={summary.valueUnit} unitScale={summary.valueScale} />
        <StrategyQuadrantCard data={summary.quadrants} onOpen={onOpen} stretchToFill={showcaseLayout} />
      </div>
      <RecommendationPanel groups={summary.recommendations} onOpen={onOpen} className="h-full min-h-0" />
    </section>
  )
}

function ChartCard({
  title,
  children,
  footer,
  onOpen,
  className = '',
}: {
  title: string
  children: ReactNode
  footer?: ReactNode
  onOpen?: () => void
  className?: string
}) {
  return (
    <article className={`rounded-2xl border border-border bg-white p-3 shadow-[var(--shadow-soft)] ${className}`}>
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

function ParetoChartCard({
  data,
  onOpen,
  unitLabel,
  unitScale,
}: {
  data: ParetoDatum[]
  onOpen: (title: string) => void
  unitLabel?: string
  unitScale?: number
}) {
  const chartTop = 16
  const chartBottom = 154
  const chartHeight = chartBottom - chartTop
  const plotLeft = 35
  const plotRight = 590
  const rightAxisX = 598
  const currencyScale = resolveCurrencyScale(unitScale, unitLabel, data.map((item) => item.gmv))
  const displayData = data.map((item) => ({ ...item, displayGmv: item.gmv / currencyScale }))
  const gmvAxisMax = getNiceAxisMax(Math.max(...displayData.map((item) => item.displayGmv), 1))
  const gmvTicks = Array.from({ length: 5 }, (_, index) => Math.round((gmvAxisMax / 4) * index))
  const xForIndex = (index: number) => {
    if (data.length <= 1) return (plotLeft + plotRight) / 2
    return plotLeft + 22 + (index / (data.length - 1)) * (plotRight - plotLeft - 44)
  }
  const barWidth = data.length <= 2 ? 42 : Math.max(18, Math.min(30, ((plotRight - plotLeft) / data.length) * 0.48))
  const points = data
    .map((item, index) => `${xForIndex(index)},${chartBottom - (item.cumulativeRatio / 100) * chartHeight}`)
    .join(' ')
  const topCategories = data.slice(0, 2).map((item) => item.category)
  const topShare = data[Math.min(1, data.length - 1)]?.cumulativeRatio ?? 0
  const footerText = data.length > 0
    ? `${topCategories.join('、')}累计贡献约 ${topShare.toFixed(1)}% GMV，是当前真实数据中的优先复核对象。`
    : '暂无品类 GMV 产物；运行 diagnostics 后会展示真实 Pareto。'
  return (
    <ChartCard title="品类 GMV Pareto" onOpen={() => onOpen('品类 GMV Pareto')} footer={<InsightMiniPanel text={footerText} />}>
      <svg viewBox="0 0 650 188" className="h-48 w-full" role="img" aria-label="品类 GMV Pareto">
        <text x="5" y="8" fontSize="11" fill="#374151">GMV（{currencyUnitForScale(currencyScale, unitLabel)}）</text>
        <text x="586" y="8" fontSize="11" fill="#374151">累计占比（%）</text>
        <line x1={plotLeft} y1={chartBottom} x2={plotRight} y2={chartBottom} stroke="#d9e1ec" />
        <line x1={rightAxisX} y1={chartTop} x2={rightAxisX} y2={chartBottom} stroke="#d9e1ec" />
        {gmvTicks.map((tick, index) => (
          <g key={`gmv-tick-${tick}-${index}`}>
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
        {displayData.map((item, index) => {
          const height = (item.displayGmv / gmvAxisMax) * chartHeight
          const x = xForIndex(index) - barWidth / 2
          return (
            <g
              key={`${item.category}-${index}`}
              onClick={(event) => {
                event.stopPropagation()
                onOpen(item.category)
              }}
              className="cursor-pointer"
            >
              <rect
                x={x}
                y={chartBottom - height}
                width={barWidth}
                height={height}
                rx="4"
                fill="#60a5fa"
                aria-label={`${item.category}: ${formatCurrencyWithUnit(item.gmv, currencyScale, false, unitLabel)}`}
              />
              <text x={xForIndex(index)} y="180" textAnchor="middle" fontSize="11" fill="#374151">{item.category}</text>
            </g>
          )
        })}
        <polyline points={points} fill="none" stroke="#2563eb" strokeWidth="3" />
        {data.map((item, index) => (
          <circle
            key={`${item.category}-line-${index}`}
            cx={xForIndex(index)}
            cy={chartBottom - (item.cumulativeRatio / 100) * chartHeight}
            r="4"
            fill="#2563eb"
            aria-label={`累计占比 ${item.cumulativeRatio}%`}
          />
        ))}
      </svg>
    </ChartCard>
  )
}

function LocalGapWaterfallCard({
  data,
  onOpen,
  unitLabel,
  unitScale,
}: {
  data: WaterfallDatum[]
  onOpen: (title: string) => void
  unitLabel?: string
  unitScale?: number
}) {
  const chartTop = 14
  const chartBottom = 150
  const chartHeight = chartBottom - chartTop
  const barWidth = 70
  const step = 94
  const startX = 42
  const currencyScale = resolveCurrencyScale(unitScale, unitLabel, data.map((item) => item.value))
  const displayData = data.map((item) => ({
    ...item,
    rawValue: item.value,
    value: item.value / currencyScale,
  }))
  const { bars } = displayData.reduce<{
    cumulative: number
    bars: Array<{
      item: WaterfallDatum & { rawValue: number }
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
  const chartMax = getNiceAxisMax(maxValue)
  const ticks = Array.from({ length: 5 }, (_, index) => Math.round((chartMax / 4) * index))
  const scaleY = (value: number) => chartBottom - (value / chartMax) * chartHeight
  const contributionRows = data.filter((item) => item.type === 'positive' || item.type === 'negative')
  const largestContribution = contributionRows.reduce<WaterfallDatum | null>(
    (largest, item) => (!largest || Math.abs(item.value) > Math.abs(largest.value) ? item : largest),
    null,
  )
  const footerText = largestContribution && Math.abs(largestContribution.value) > 0
    ? `${largestContribution.name}是当前最大拆解项，贡献 ${formatCurrencyWithUnit(largestContribution.value, currencyScale, true, unitLabel)}。`
    : '当前 LocalGap 产物未提供可拆分资源贡献，净增量主要留在残差/未拆分项。'

  return (
    <ChartCard title="LocalGap 增量分解瀑布图" onOpen={() => onOpen('LocalGap 增量分解瀑布图')} footer={<InsightMiniPanel text={footerText} />}>
      <div className="mb-2 flex justify-end gap-3 text-xs text-muted-foreground">
        <Legend color="#22c55e" label="正向贡献" />
        <Legend color="#ef4444" label="负向贡献" />
        <Legend color="#9ca3af" label="基线/合计" />
      </div>
      <svg viewBox="0 0 635 188" className="h-48 w-full" role="img" aria-label="LocalGap 增量分解瀑布图">
        <text x="5" y="8" fontSize="11" fill="#374151">GMV（{currencyUnitForScale(currencyScale, unitLabel)}）</text>
        <line x1="34" y1={chartBottom} x2="610" y2={chartBottom} stroke="#d9e1ec" />
        {ticks.map((tick, index) => {
          const y = scaleY(tick)
          return (
            <g key={`localgap-tick-${tick}-${index}`}>
              <line x1="34" y1={y} x2="610" y2={y} stroke="#eef2f7" />
              <text x="5" y={y + 4} fontSize="10" fill="#6b7280">
                {formatScaledCurrencyNumber(tick, currencyScale)}
              </text>
            </g>
          )
        })}
        {bars.slice(0, -1).map((bar, index) => {
          const nextBar = bars[index + 1]
          const y = scaleY(bar.end)
          return (
            <line
              key={`${bar.item.name}-connector-${index}`}
              x1={bar.x + barWidth}
              y1={y}
              x2={nextBar.x}
              y2={y}
              stroke="#94a3b8"
              strokeDasharray="4 4"
            />
          )
        })}
        {bars.map(({ item, x, start, end }, index) => {
          const top = Math.min(scaleY(start), scaleY(end))
          const height = Math.max(6, Math.abs(scaleY(start) - scaleY(end)))
          const color = item.type === 'positive' ? '#22c55e' : item.type === 'negative' ? '#ef4444' : '#9ca3af'
          const label = formatScaledCurrencyNumber(item.value, currencyScale, item.type === 'positive')
          return (
            <g
              key={`${item.name}-${index}`}
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
                aria-label={`${item.name}: ${formatCurrencyWithUnit(item.rawValue, currencyScale, false, unitLabel)}`}
              />
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

function GmvTrendComparisonCard({
  data,
  onOpen,
  stretchToFill = false,
  unitLabel,
  unitScale,
}: {
  data: TrendDatum[]
  onOpen: (title: string) => void
  stretchToFill?: boolean
  unitLabel?: string
  unitScale?: number
}) {
  const chartRef = useRef<HTMLDivElement>(null)
  const periodSummaries = buildPeriodSummaries(data, unitScale, unitLabel)

  useEffect(() => {
    if (!chartRef.current) return

    const chart = echarts.init(chartRef.current, undefined, { renderer: 'svg' })
    chart.setOption(buildGmvTrendOption(data, unitScale, unitLabel))
    const frame = window.requestAnimationFrame(() => chart.resize())
    const resizeObserver = new ResizeObserver(() => chart.resize())
    resizeObserver.observe(chartRef.current)

    return () => {
      window.cancelAnimationFrame(frame)
      resizeObserver.disconnect()
      chart.dispose()
    }
  }, [data, unitLabel, unitScale])

  return (
    <ChartCard
      title="活动前中后：GMV 趋势与活动期对比"
      onOpen={() => onOpen('活动前中后：GMV 趋势与活动期对比')}
      className={stretchToFill ? 'flex h-full min-h-0 flex-col' : ''}
    >
      <div className="mb-2 flex justify-end gap-3 text-xs text-muted-foreground">
        <Legend color="#3b82f6" label="实际 GMV" />
        <Legend color="#9ca3af" label="自然基线" />
        <Legend color="#fed7aa" label="活动期窗口" />
        <Legend color="#ef4444" label="发薪日" />
      </div>
      <div className={`grid grid-cols-[minmax(0,1fr)_150px] gap-3 ${stretchToFill ? 'min-h-0 flex-1' : ''}`}>
        <div
          data-dashboard-gmv-trend-chart
          ref={chartRef}
          className={stretchToFill ? 'h-full min-h-0 min-w-0' : 'h-48 min-w-0'}
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

function buildGmvTrendOption(data: TrendDatum[], unitScale?: number, unitLabel?: string): echarts.EChartsOption {
  const dates = data.map((item) => item.date)
  const currencyScale = resolveCurrencyScale(unitScale, unitLabel, data.flatMap((item) => [item.gmv, item.baselineGmv]))
  const paydayPoints = data
    .filter((item) => item.isPayday)
    .map((item) => ({
      name: '发薪日',
      coord: [item.date, item.gmv / currencyScale],
      value: item.gmv / currencyScale,
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
                ? formatScaledCurrencyNumber(point.value, currencyScale)
                : point.value

            return `${point.marker ?? ''}${point.seriesName ?? ''}: ${value} ${currencyUnitForScale(currencyScale, unitLabel)}`
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
      name: `GMV（${currencyUnitForScale(currencyScale, unitLabel)}）`,
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
        data: data.map((item) => item.gmv / currencyScale),
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
        data: data.map((item) => item.baselineGmv / currencyScale),
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

function buildPeriodSummaries(data: TrendDatum[], unitScale?: number, unitLabel?: string) {
  const currencyScale = resolveCurrencyScale(unitScale, unitLabel, data.flatMap((item) => [item.gmv, item.baselineGmv]))
  const pre = summarizePeriod(data, 'pre')
  const during = summarizePeriod(data, 'during')
  const post = summarizePeriod(data, 'post')

  return [
    {
      label: '活动前',
      value: `日均 ${formatCurrencyWithUnit(pre.dailyAvg, currencyScale, false, unitLabel)}`,
      delta: pre.days > 0 ? `${pre.days} 天基准窗口` : '无基准窗口',
      tone: 'text-muted-foreground',
    },
    {
      label: '活动中',
      value: `日均 ${formatCurrencyWithUnit(during.dailyAvg, currencyScale, false, unitLabel)}`,
      delta: formatLift(during.dailyAvg, pre.dailyAvg),
      tone: 'text-blue-600',
    },
    {
      label: '活动后',
      value: `日均 ${formatCurrencyWithUnit(post.dailyAvg, currencyScale, false, unitLabel)}`,
      delta: formatLift(post.dailyAvg, pre.dailyAvg),
      tone: 'text-blue-600',
    },
  ]
}

function summarizePeriod(data: TrendDatum[], period: TrendDatum['period']) {
  const rows = data.filter((item) => item.period === period)
  const total = rows.reduce((sum, item) => sum + item.gmv, 0)
  return {
    total,
    days: rows.length,
    dailyAvg: rows.length > 0 ? total / rows.length : 0,
  }
}

function formatLift(current: number, base: number) {
  if (base === 0) return '+0.0%'
  const lift = ((current - base) / base) * 100
  return `${lift >= 0 ? '+' : ''}${lift.toFixed(1)}%`
}

type RepresentativeQuadrantKey = RecommendationGroup['key']

type RepresentativeQuadrantItem = QuadrantItem & {
  representativeGroup: RepresentativeQuadrantKey
  representativeIndex: number
  representativeVisibleCount: number
  representativeTotal: number
  originalIndex: number
}

const representativeQuadrantOrder: RepresentativeQuadrantKey[] = ['boost', 'watch', 'control_discount', 'avoid']

const representativeQuadrantLabels: Record<RepresentativeQuadrantKey, string> = {
  boost: '优先加码',
  watch: '小规模验证',
  control_discount: '控制折扣',
  avoid: '避免打扰',
}

const representativeQuadrantBounds: Record<
  RepresentativeQuadrantKey,
  { minX: number; maxX: number; minY: number; maxY: number }
> = {
  boost: { minX: 23, maxX: 46, minY: 58, maxY: 77 },
  watch: { minX: 60, maxX: 86, minY: 58, maxY: 77 },
  control_discount: { minX: 23, maxX: 46, minY: 27, maxY: 45 },
  avoid: { minX: 60, maxX: 86, minY: 27, maxY: 45 },
}

const representativeScatterTemplate = [
  { x: 0.24, y: 0.78 },
  { x: 0.72, y: 0.64 },
  { x: 0.40, y: 0.35 },
  { x: 0.84, y: 0.28 },
]

function representativeGroupForItem(item: QuadrantItem): RepresentativeQuadrantKey {
  if (item.group === 'boost') return 'boost'
  if (item.group === 'avoid') return 'avoid'
  if (item.group === 'control_discount' || item.group === 'reduce') return 'control_discount'
  return 'watch'
}

function representativeScore(item: QuadrantItem) {
  const contribution = Math.abs(item.contribution ?? 0)
  const size = Math.abs(item.size ?? 0)
  const count = Math.abs(item.count ?? 0)
  return contribution * 10 + size + count
}

function selectRepresentativeQuadrantItems(data: QuadrantItem[], limitPerQuadrant: number) {
  const grouped = representativeQuadrantOrder.reduce<Record<RepresentativeQuadrantKey, Array<{ item: QuadrantItem; index: number }>>>(
    (acc, key) => {
      acc[key] = []
      return acc
    },
    {} as Record<RepresentativeQuadrantKey, Array<{ item: QuadrantItem; index: number }>>,
  )

  data.forEach((item, index) => {
    grouped[representativeGroupForItem(item)].push({ item, index })
  })

  const visible = representativeQuadrantOrder.flatMap((group) => {
    const selected = [...grouped[group]]
      .sort((a, b) => {
        const scoreDelta = representativeScore(b.item) - representativeScore(a.item)
        if (scoreDelta !== 0) return scoreDelta
        return a.item.category.localeCompare(b.item.category, 'zh-Hans-CN')
      })
      .slice(0, limitPerQuadrant)

    return selected.map((entry, selectedIndex): RepresentativeQuadrantItem => ({
      ...entry.item,
      representativeGroup: group,
      representativeIndex: selectedIndex,
      representativeVisibleCount: selected.length,
      representativeTotal: grouped[group].length,
      originalIndex: entry.index,
    }))
  })

  return {
    visible,
    hiddenCount: Math.max(0, data.length - visible.length),
    summary: representativeQuadrantOrder
      .filter((group) => grouped[group].length > 0)
      .map((group) => ({
        group,
        label: representativeQuadrantLabels[group],
        total: grouped[group].length,
        visible: Math.min(grouped[group].length, limitPerQuadrant),
      })),
  }
}

function getRepresentativePosition(item: RepresentativeQuadrantItem) {
  const bounds = representativeQuadrantBounds[item.representativeGroup]
  const template = representativeScatterTemplate[item.representativeIndex % representativeScatterTemplate.length]
  const jitterSeed = stableScatterSeed(`${item.representativeGroup}:${item.category}:${item.originalIndex}`)
  const jitterX = (jitterSeed.x - 0.5) * 4.2
  const jitterY = (jitterSeed.y - 0.5) * 3.6
  const x = clampLayoutValue(bounds.minX + (bounds.maxX - bounds.minX) * template.x + jitterX, bounds.minX, bounds.maxX)
  const y = clampLayoutValue(bounds.minY + (bounds.maxY - bounds.minY) * template.y + jitterY, bounds.minY, bounds.maxY)

  return { x, y }
}

function stableScatterSeed(text: string) {
  let hash = 2166136261
  for (let index = 0; index < text.length; index += 1) {
    hash ^= text.charCodeAt(index)
    hash = Math.imul(hash, 16777619)
  }
  const x = ((hash >>> 0) % 997) / 997
  const y = (((hash >>> 8) % 991) / 991)
  return { x, y }
}

function clampLayoutValue(value: number, min: number, max: number) {
  return Math.min(max, Math.max(min, value))
}

function StrategyQuadrantCard({
  data,
  onOpen,
  stretchToFill = false,
}: {
  data: QuadrantItem[]
  onOpen: (title: string) => void
  stretchToFill?: boolean
}) {
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
  const hasUpliftSummary = data.some((item) => item.count || item.resourceType || item.quadrant)
  const maxBubbleContribution = Math.max(...data.map((item) => Math.abs(item.contribution ?? item.size ?? 0)), 1)
  const representativeLimitPerQuadrant = 4
  const {
    visible: visibleBubbleData,
    hiddenCount: hiddenBubbleCount,
    summary: representativeSummary,
  } = selectRepresentativeQuadrantItems(data, representativeLimitPerQuadrant)
  const representativeSummaryText = representativeSummary
    .map((item) => `${item.label} ${item.visible}/${item.total}`)
    .join(' · ')
  const getBubbleSize = (item: QuadrantItem) => {
    if (!hasUpliftSummary) return Math.min(44, Math.max(28, item.size))
    const contribution = Math.abs(item.contribution ?? item.size)
    return Math.min(46, 29 + Math.sqrt(contribution / maxBubbleContribution) * 15)
  }

  const laidOutData = visibleBubbleData.map((item) => {
    const representativePosition = getRepresentativePosition(item)
    const visual = visualLayout[item.category] ?? {
      x: representativePosition.x,
      y: representativePosition.y,
      size: getBubbleSize(item),
      color: item.color,
      textColor: item.contribution || item.count ? '#ffffff' : undefined,
    }
    return { ...item, visual }
  })

  return (
    <ChartCard
      title={hasUpliftSummary ? '连续 Uplift 四象限（气泡图）' : '品类策略四象限（气泡图）'}
      onOpen={() => onOpen(hasUpliftSummary ? '连续 Uplift 四象限（气泡图）' : '品类策略四象限（气泡图）')}
      className={stretchToFill ? 'flex h-full min-h-0 flex-col' : ''}
    >
      <div
        data-dashboard-quadrant-plot
        className={`relative overflow-hidden rounded-xl border border-border bg-[#fbfcfe] ${
          stretchToFill ? 'min-h-0 flex-1' : 'h-60'
        }`}
      >
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

        <QuadrantLabel className="left-[18%] top-3" text={hasUpliftSummary ? '优先加码' : '小规模试验区'} toneClass="text-emerald-600" />
        <QuadrantLabel className="right-[7%] top-3" text={hasUpliftSummary ? '稳定维持' : '优先加码区'} toneClass="text-blue-600" />
        <QuadrantLabel className="bottom-[34px] left-[18%]" text={hasUpliftSummary ? '控制折扣' : '减少投入区'} toneClass="text-orange-600" />
        <QuadrantLabel className="bottom-[34px] right-[7%]" text={hasUpliftSummary ? '避免打扰' : '保护基本盘区'} toneClass="text-purple-600" />
        {hiddenBubbleCount > 0 && (
          <span
            className="absolute right-3 top-10 max-w-[76%] truncate rounded-full border border-border bg-white px-2 py-1 text-[11px] font-bold text-muted-foreground shadow-sm"
            title={`每象限最多 ${representativeLimitPerQuadrant} 个代表：${representativeSummaryText}；另 ${hiddenBubbleCount} 个见策略清单`}
          >
            每象限最多 {representativeLimitPerQuadrant} 个代表，另 {hiddenBubbleCount} 个见策略清单
          </span>
        )}

        <span className="absolute bottom-2 left-1/2 -translate-x-1/2 text-xs font-medium text-muted-foreground">
          {hasUpliftSummary ? '自然购买倾向' : '增量贡献'}
        </span>
        <span className="absolute bottom-2 left-[14%] text-xs text-muted-foreground">低</span>
        <span className="absolute bottom-2 right-[6%] text-xs text-muted-foreground">高</span>
        <span className="absolute left-2 top-1/2 -translate-y-1/2 -rotate-90 text-xs font-medium text-muted-foreground">
          {hasUpliftSummary ? '资源后响应' : '效果改善'}
        </span>
        <span className="absolute left-[5%] top-[14%] text-xs text-muted-foreground">高</span>
        <span className="absolute bottom-[14%] left-[5%] text-xs text-muted-foreground">低</span>

        {laidOutData.map((item, index) => (
          <button
            key={`${item.category}-${index}`}
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
                item.group === 'boost'
                  ? '0 12px 24px rgba(37, 99, 235, 0.28)'
                  : '0 8px 18px rgba(15, 23, 42, 0.16)',
            }}
            title={[
              `${item.category}: ${item.suggestedAction}`,
              `象限：${representativeQuadrantLabels[item.representativeGroup]} ${item.representativeIndex + 1}/${item.representativeTotal}`,
              item.contribution ? `品类贡献：${item.contribution.toLocaleString('zh-CN', { maximumFractionDigits: 1 })}` : '',
              item.count ? `品类数：${item.count}` : '',
              item.resourceType ? `资源类型：${item.resourceType}` : '',
              item.representativeCategories?.length
                ? `代表品类：${item.representativeCategories.join('、')}`
                : '',
            ].filter(Boolean).join('；')}
          >
            {hasUpliftSummary ? (
              <span className="max-w-full overflow-hidden px-1 text-center text-[8.75px] leading-[1.05] [display:-webkit-box] [-webkit-box-orient:vertical] [-webkit-line-clamp:3] [overflow-wrap:anywhere]">
                {item.category}
              </span>
            ) : (
              <span className="whitespace-nowrap">{item.category}</span>
            )}
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
    <aside
      data-dashboard-recommendation-panel
      className={`grid content-stretch gap-4 ${className}`}
      style={{ gridTemplateRows: `repeat(${groups.length}, minmax(0, 1fr))` }}
    >
      {groups.map((group) => (
        <RecommendationCard key={group.key} group={group} onOpen={onOpen} />
      ))}
    </aside>
  )
}

function RecommendationCard({ group, onOpen }: { group: RecommendationGroup; onOpen: (title: string) => void }) {
  const color = colorClass[group.color]
  const visibleCategories = group.categories.length > 2 ? group.categories.slice(0, 2) : group.categories
  const hiddenCategoryCount = group.categories.length - visibleCategories.length

  return (
    <article className={`flex min-h-0 flex-col overflow-hidden rounded-2xl border ${color.border} bg-white p-3 shadow-[var(--shadow-soft)]`}>
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
        <Badge variant="outline" className={`max-w-[104px] shrink-0 truncate ${color.tile} ${color.border}`}>{group.countLabel}</Badge>
      </div>
      <div className="mt-2 flex min-h-[24px] gap-1.5 overflow-hidden">
        {visibleCategories.map((category, index) => (
          <button
            key={`${category}-${index}`}
            type="button"
            onClick={() => onOpen(category)}
            className="max-w-[96px] flex-none truncate rounded-lg border border-border bg-[#fbfcfe] px-2 py-0.5 text-left text-[11px] font-semibold leading-5 hover:border-[#f2cf4a] hover:bg-secondary"
            title={category}
          >
            {category}
          </button>
        ))}
        {hiddenCategoryCount > 0 && (
          <button
            type="button"
            onClick={() => onOpen(group.title)}
            className="flex-none rounded-lg border border-dashed border-border bg-[#fbfcfe] px-2 py-0.5 text-left text-[11px] font-bold leading-5 text-muted-foreground hover:border-[#f2cf4a] hover:bg-secondary"
          >
            +{hiddenCategoryCount}
          </button>
        )}
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
  onAskAgent,
}: {
  open: boolean
  title: string
  summary: DashboardSummary
  onClose: () => void
  onAskAgent: (title: string) => void
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
          <GenericDrilldownContent title={title} summary={summary} />
        )}
        <div className="mt-5 flex justify-end gap-2">
          <Button variant="outline">导出明细</Button>
          <Button onClick={() => onAskAgent(title)}>
            <MessageSquarePlus className="mr-2 h-4 w-4" />
            询问 Agent
          </Button>
        </div>
      </aside>
    </div>
  )
}

function GenericDrilldownContent({ title, summary }: { title: string; summary: DashboardSummary }) {
  const currencyScale = summaryCurrencyScale(summary, [
    ...summary.pareto.map((item) => item.gmv),
    ...summary.trend.flatMap((item) => [item.gmv, item.baselineGmv, item.exposure ?? 0, item.discount ?? 0]),
  ])
  const currencyUnit = summaryCurrencyUnit(summary, currencyScale)
  const paretoItem = summary.pareto.find((item) => item.category === title)
  const totalGmv = paretoItem?.gmv ?? sumTrendValue(summary.trend, (item) => item.gmv)
  const baselineTotal = sumTrendValue(summary.trend, (item) => item.baselineGmv)
  const netTotal = sumTrendValue(summary.trend, (item) => item.gmv - item.baselineGmv)
  const exposureTotal = sumTrendValue(summary.trend, (item) => item.exposure ?? 0)
  const discountTotal = sumTrendValue(summary.trend, (item) => item.discount ?? 0)
  const localGapRows = summary.localGap.filter((item) => item.type !== 'total' && item.type !== 'baseline')

  return (
    <>
        <div className="mt-5 grid grid-cols-3 gap-2">
          <FilterButton icon={<Tag className="h-4 w-4" />} label="品类" value={title} />
          <FilterButton icon={<Zap className="h-4 w-4" />} label="指标" value="GMV" />
          <FilterButton icon={<CalendarDays className="h-4 w-4" />} label="周期" value="活动期" />
        </div>
        <div className="mt-5 grid grid-cols-3 gap-3">
          <MiniDetail label="GMV" value={formatCurrencyWithUnit(totalGmv, currencyScale, false, currencyUnit)} />
          <MiniDetail label="自然基线" value={formatCurrencyWithUnit(baselineTotal, currencyScale, false, currencyUnit)} />
          <MiniDetail label="净增量" value={formatCurrencyWithUnit(netTotal, currencyScale, true, currencyUnit)} />
        </div>
        <div className="mt-5 rounded-2xl border border-border bg-[#fbfcfe] p-4">
          <h3 className="font-bold">贡献拆解</h3>
          {(localGapRows.length > 0 ? localGapRows : [
            { name: '曝光贡献', value: exposureTotal, type: 'positive' as const },
            { name: '折扣贡献', value: discountTotal, type: discountTotal >= 0 ? 'positive' as const : 'negative' as const },
          ]).map((item) => (
            <div key={item.name} className="mt-3 grid grid-cols-3 rounded-lg bg-white px-3 py-2 text-sm">
              <span>{item.name}</span>
              <span className="font-bold">{formatCurrencyWithUnit(item.value, currencyScale, true, currencyUnit)}</span>
              <span className="text-right text-muted-foreground">{formatSharePercent(item.value, netTotal)}</span>
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
          unitLabel={kpi.unit}
          unitScale={summary.valueScale}
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
  const currencyScale = summaryCurrencyScale(summary, [
    ...summary.trend.flatMap((item) => [item.gmv, item.baselineGmv, item.exposure ?? 0, item.discount ?? 0]),
    ...kpi.series.map((item) => item.value),
  ])
  const currencyUnit = summaryCurrencyUnit(summary, currencyScale)
  const netTotal = sumTrendValue(summary.trend, (item) => item.gmv - item.baselineGmv)
  const exposureTotal = sumTrendValue(summary.trend, (item) => item.exposure ?? 0)
  const discountTotal = sumTrendValue(summary.trend, (item) => item.discount ?? 0)
  const baseMetricCards = [
    { label: '当前值', value: `${kpi.value}${kpi.unit ? ` ${kpi.unit}` : ''}` },
    { label: '最近点', value: latest ? formatDetailPoint(latest, kpi.unit, currencyScale) : '-' },
    { label: '峰值点', value: peak ? formatDetailPoint(peak, kpi.unit, currencyScale) : '-' },
    { label: '低点', value: min ? formatDetailPoint(min, kpi.unit, currencyScale) : '-' },
  ]
  const kpiDisplayValue = `${kpi.value}${kpi.unit ? ` ${kpi.unit}` : ''}`

  if (kpi.key === 'gmv_increment') {
    return {
      scope: '实际 - 基线',
      granularity: '日度',
      benchmark: '自然基线',
      chartTitle: '每日 GMV 净增量走势',
      chartHint: '小图口径与卡片主值一致，展示 daily_actual_gmv - daily_baseline_gmv。',
      metricCards: [
        { label: '累计净增量', value: kpiDisplayValue },
        { label: '最近日净增', value: latest ? formatCurrencyWithUnit(latest.value, currencyScale, true, currencyUnit) : '-' },
        { label: '峰值日期', value: peak ? `${peak.label} ${formatCurrencyWithUnit(peak.value, currencyScale, true, currencyUnit)}` : '-' },
        { label: '负向天数', value: `${negativeCount} 天` },
      ],
      tableTitle: '日度净增量明细',
      columns: ['日期', '实际 GMV', '自然基线', '净增量'],
      rows: summary.trend.map((item) => [
        item.date,
        formatCurrencyWithUnit(item.gmv, currencyScale, false, currencyUnit),
        formatCurrencyWithUnit(item.baselineGmv, currencyScale, false, currencyUnit),
        formatCurrencyWithUnit(item.gmv - item.baselineGmv, currencyScale, true, currencyUnit),
      ]),
      tags: [],
      methodTitle: '口径说明',
      methodText: `GMV 净增量按日计算为实际 GMV 减自然基线 GMV，累计后对应顶部卡片的 ${kpiDisplayValue}；它不等同于 GMV 总量曲线。`,
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
        { label: '累计曝光贡献', value: kpiDisplayValue },
        { label: '最近日贡献', value: latest ? formatCurrencyWithUnit(latest.value, currencyScale, true, currencyUnit) : '-' },
        { label: '峰值贡献', value: peak ? `${peak.label} ${formatCurrencyWithUnit(peak.value, currencyScale, true, currencyUnit)}` : '-' },
        { label: '净增量占比', value: formatSharePercent(exposureTotal, netTotal) },
      ],
      tableTitle: '日度曝光贡献明细',
      columns: ['日期', '曝光贡献', '当日净增占比', '日历标记'],
      rows: summary.trend.map((item) => {
        const net = item.gmv - item.baselineGmv
        const exposure = item.exposure ?? 0

        return [
          item.date,
          formatCurrencyWithUnit(exposure, currencyScale, true, currencyUnit),
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
        { label: '累计折扣贡献', value: kpiDisplayValue },
        { label: '最近日贡献', value: latest ? formatCurrencyWithUnit(latest.value, currencyScale, true, currencyUnit) : '-' },
        { label: '负贡献天数', value: `${negativeCount} 天` },
        { label: '净增量占比', value: formatSharePercent(discountTotal, netTotal) },
      ],
      tableTitle: '日度折扣贡献明细',
      columns: ['日期', '折扣贡献', '影响方向', '日历标记'],
      rows: summary.trend.map((item) => {
        const discount = item.discount ?? 0

        return [
          item.date,
          formatCurrencyWithUnit(discount, currencyScale, true, currencyUnit),
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
        { label: '当前加码品类', value: kpiDisplayValue },
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
  unitLabel,
  unitScale,
}: {
  series: SparklinePoint[]
  color: KpiCardData['color']
  type: KpiCardData['chartType']
  signed?: boolean
  unitLabel?: string
  unitScale?: number
}) {
  const width = 620
  const height = 168
  const left = 34
  const right = 14
  const top = 18
  const bottom = 136
  const currencyScale = resolveCurrencyScale(unitScale, unitLabel, series.map((item) => item.value))
  const displaySeries = series.map((item) => ({ ...item, value: item.value / currencyScale }))
  const values = displaySeries.map((item) => item.value).filter(Number.isFinite)

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
    displaySeries.length === 1
      ? (left + width - right) / 2
      : left + (index / (displaySeries.length - 1)) * (width - left - right)
  const yForValue = (value: number) => top + (1 - (value - min) / (max - min)) * (bottom - top)
  const zeroY = yForValue(0)
  const palette = sparklinePalette[color]
  const points = displaySeries.map((item, index) => ({
    ...item,
    x: xForIndex(index),
    y: yForValue(item.value),
  }))
  const linePath = points.map((point, index) => `${index === 0 ? 'M' : 'L'} ${point.x} ${point.y}`).join(' ')
  const barWidth = Math.max(16, Math.min(34, (width - left - right) / Math.max(displaySeries.length, 1) - 18))
  const gridTicks = [min, (min + max) / 2, max]

  return (
    <svg viewBox={`0 0 ${width} ${height}`} className="mt-4 h-44 w-full" role="img" aria-label={`指标明细趋势（${currencyUnitForScale(currencyScale, unitLabel)}）`}>
      {gridTicks.map((tick, index) => {
        const y = yForValue(tick)

        return (
          <g key={`detail-grid-${tick}-${index}`}>
            <line x1={left} x2={width - right} y1={y} y2={y} stroke="#eef2f7" />
            <text x="4" y={y + 4} fontSize="10" fill="#6b7280">
              {formatScaledCurrencyNumber(tick, currencyScale)}
            </text>
          </g>
        )
      })}
      {signed && (
        <line x1={left} x2={width - right} y1={zeroY} y2={zeroY} stroke={palette.zero} strokeDasharray="4 4" />
      )}
      <line x1={left} x2={width - right} y1={bottom} y2={bottom} stroke="#d9e1ec" />
      {type === 'bar' ? (
        points.map((point, index) => {
          const baseY = signed ? zeroY : bottom
          const y = Math.min(point.y, baseY)

          return (
            <g key={`${point.label}-${index}`}>
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
          {points.map((point, index) => (
            <g key={`${point.label}-${index}`}>
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

function formatDetailPoint(point: SparklinePoint, unit?: string, scale?: number) {
  const currencyScale = resolveCurrencyScale(scale, unit, [point.value])
  return `${point.label} ${formatCurrencyWithUnit(point.value, currencyScale, false, unit)}`
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
              aria-label={`${point.label}: ${point.value}`}
            />
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
            aria-label={`${last.label}: ${last.value}`}
          />
        </>
      )}
    </svg>
  )
}

function InsightMiniPanel({ text }: { text: string }) {
  return (
    <div className="mt-3 rounded-xl border border-border bg-[#fbfcfe] px-3 py-2">
      <p className="text-xs leading-4 text-muted-foreground">{text}</p>
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

function QuadrantLabel({
  text,
  className,
  toneClass = 'text-blue-600',
}: {
  text: string
  className: string
  toneClass?: string
}) {
  return <span className={`absolute text-xs font-bold ${toneClass} ${className}`}>{text}</span>
}

function MiniDetail({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-xl border border-border bg-[#fbfcfe] px-3 py-3">
      <p className="text-xs text-muted-foreground">{label}</p>
      <p className="mt-1 font-bold">{value}</p>
    </div>
  )
}
