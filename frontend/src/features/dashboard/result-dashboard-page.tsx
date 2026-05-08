'use client'

import { useState, type ReactNode } from 'react'
import {
  ArrowUpRight,
  CalendarDays,
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
  TrendDatum,
  WaterfallDatum,
} from '@/types/dashboard'

const initialFilters: DashboardFilters = {
  timeRange: ['2025-05-06', '2025-06-04'],
  activityWindow: 'during',
  categoryLevel: 'all',
  calendarType: 'all',
}

const colorClass = {
  green: {
    tile: 'bg-green-50 text-green-700',
    border: 'border-green-200',
    accent: '#22c55e',
  },
  blue: {
    tile: 'bg-blue-50 text-blue-700',
    border: 'border-blue-200',
    accent: '#3b82f6',
  },
  orange: {
    tile: 'bg-orange-50 text-orange-700',
    border: 'border-orange-200',
    accent: '#f97316',
  },
  purple: {
    tile: 'bg-purple-50 text-purple-700',
    border: 'border-purple-200',
    accent: '#8b5cf6',
  },
}

export function ResultDashboardPage({ summary }: { summary: DashboardSummary }) {
  const [filters, setFilters] = useState<DashboardFilters>(initialFilters)
  const [drilldown, setDrilldown] = useState<string | null>(null)
  const [exportOpen, setExportOpen] = useState(false)

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
          <CoreConclusionBanner conclusion={summary.conclusion} onExplain={() => setDrilldown('核心结论')} />
          <KpiSummaryStrip kpis={summary.kpis} onOpen={setDrilldown} />
          <DashboardMainGrid summary={summary} onOpen={setDrilldown} />
        </div>
      </ScaledPageFrame>

      <DashboardDrilldownDrawer
        open={Boolean(drilldown)}
        title={drilldown || ''}
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
  return (
    <label className="flex h-12 items-center gap-3 rounded-xl border border-border bg-white px-4 shadow-sm">
      <span className="text-[#1f2937]">{icon}</span>
      <span className="min-w-0 flex-1">
        <span className="block text-[11px] font-semibold text-muted-foreground">{label}</span>
        <select
          value={value}
          onChange={(event) => onChange(event.target.value)}
          className="w-full bg-transparent text-sm font-bold outline-none"
        >
          {options.map(([optionValue, optionLabel]) => (
            <option key={optionValue} value={optionValue}>
              {optionLabel}
            </option>
          ))}
        </select>
      </span>
    </label>
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
      className={`rounded-2xl border ${color.border} bg-white px-3 py-2.5 text-left shadow-[var(--shadow-soft)] transition hover:-translate-y-0.5 hover:shadow-lg`}
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
          <p className="mt-0.5 truncate text-xs font-semibold text-muted-foreground">{kpi.subText}</p>
        </div>
        <div className="flex w-24 shrink-0 flex-col items-end gap-1">
          <ArrowUpRight className="h-4 w-4 text-muted-foreground" />
          <Sparkline values={kpi.sparkline} color={color.accent} />
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

function ChartCard({ title, children, footer }: { title: string; children: ReactNode; footer?: ReactNode }) {
  return (
    <article className="rounded-2xl border border-border bg-white p-3 shadow-[var(--shadow-soft)]">
      <ChartCardHeader title={title} />
      {children}
      {footer}
    </article>
  )
}

function ChartCardHeader({ title }: { title: string }) {
  return (
    <div className="mb-3 flex items-center justify-between gap-3">
      <h2 className="text-base font-bold">{title}</h2>
      <button className="rounded-full p-1 text-muted-foreground hover:bg-[#f7f8fa]" title={`${title} 方法说明`}>
        <Info className="h-4 w-4" />
      </button>
    </div>
  )
}

function ParetoChartCard({ data, onOpen }: { data: ParetoDatum[]; onOpen: (title: string) => void }) {
  const chartTop = 16
  const chartBottom = 154
  const chartHeight = chartBottom - chartTop
  const rightAxisX = 598
  const points = data
    .map((item, index) => `${45 + index * 62},${chartBottom - (item.cumulativeRatio / 100) * chartHeight}`)
    .join(' ')
  return (
    <ChartCard title="品类 GMV Pareto" footer={<InsightMiniPanel text="饮料和零食贡献接近 60% GMV，是活动资源优先验证对象。" />}>
      <svg viewBox="0 0 650 188" className="h-48 w-full" role="img" aria-label="品类 GMV Pareto">
        <text x="5" y="8" fontSize="11" fill="#374151">GMV（万元）</text>
        <text x="586" y="8" fontSize="11" fill="#374151">累计占比（%）</text>
        <line x1="35" y1={chartBottom} x2="590" y2={chartBottom} stroke="#d9e1ec" />
        <line x1={rightAxisX} y1={chartTop} x2={rightAxisX} y2={chartBottom} stroke="#d9e1ec" />
        {[0, 600, 1200, 1800, 2400].map((tick) => (
          <g key={tick}>
            <line x1="35" y1={chartBottom - (tick / 2400) * chartHeight} x2="590" y2={chartBottom - (tick / 2400) * chartHeight} stroke="#eef2f7" />
            <text x="5" y={chartBottom + 4 - (tick / 2400) * chartHeight} fontSize="10" fill="#6b7280">{tick}</text>
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
          const height = (item.gmv / 2400) * chartHeight
          const x = 30 + index * 62
          return (
            <g key={item.category} onClick={() => onOpen(item.category)} className="cursor-pointer">
              <rect x={x} y={chartBottom - height} width="30" height={height} rx="4" fill="#60a5fa">
                <title>{`${item.category}: ${item.gmv} 万元`}</title>
              </rect>
              <text x={x + 15} y="180" textAnchor="middle" fontSize="11" fill="#374151">{item.category}</text>
            </g>
          )
        })}
        <polyline points={points} fill="none" stroke="#2563eb" strokeWidth="3" />
        {data.map((item, index) => (
          <circle key={`${item.category}-line`} cx={45 + index * 62} cy={chartBottom - (item.cumulativeRatio / 100) * chartHeight} r="4" fill="#2563eb">
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
  let cumulative = 0
  const bars = data.map((item, index) => {
    const x = startX + index * step
    const start = item.type === 'baseline' || item.type === 'total' ? 0 : cumulative
    const end =
      item.type === 'baseline' || item.type === 'total'
        ? item.value
        : cumulative + item.value

    if (item.type !== 'total') {
      cumulative = end
    }

    return { item, x, start, end }
  })
  const maxValue = Math.max(...bars.flatMap((bar) => [bar.start, bar.end]), 1)
  const chartMax = Math.ceil(maxValue / 400) * 400
  const scaleY = (value: number) => chartBottom - (value / chartMax) * chartHeight

  return (
    <ChartCard title="LocalGap 增量分解瀑布图" footer={<InsightMiniPanel text="曝光贡献是主要增量来源，交互/渠道项提示需要复盘触达质量。" />}>
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
            <g key={item.name} onClick={() => onOpen(item.name)} className="cursor-pointer">
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
  const max = Math.max(...data.map((item) => item.gmv))
  const chartTop = 18
  const chartBottom = 154
  const chartHeight = chartBottom - chartTop
  const points = data.map((item, index) => `${40 + index * 75},${chartBottom - (item.gmv / max) * chartHeight * 0.92}`).join(' ')
  return (
    <ChartCard title="活动前中后：GMV 趋势与活动期对比">
      <div className="mb-2 flex justify-end gap-3 text-xs text-muted-foreground">
        <Legend color="#3b82f6" label="GMV" />
        <Legend color="#fed7aa" label="活动期窗口" />
        <Legend color="#ef4444" label="发薪日" />
      </div>
      <div className="grid grid-cols-[minmax(0,1fr)_150px] gap-3">
        <svg viewBox="0 0 540 188" className="h-48 w-full" role="img" aria-label="GMV 趋势">
          <text x="5" y="8" fontSize="11" fill="#374151">GMV（万元）</text>
          <text x="176" y="12" fontSize="11" fill="#92400e">活动期</text>
          <rect x="190" y={chartTop} width="155" height={chartHeight} fill="#fed7aa" opacity="0.35" />
          {[0, 300, 600, 900, 1200].map((tick) => (
            <g key={tick}>
              <line x1="35" y1={chartBottom - (tick / 1200) * chartHeight} x2="510" y2={chartBottom - (tick / 1200) * chartHeight} stroke="#eef2f7" />
              <text x="5" y={chartBottom + 4 - (tick / 1200) * chartHeight} fontSize="10" fill="#6b7280">{tick}</text>
            </g>
          ))}
          <polyline points={points} fill="none" stroke="#3b82f6" strokeWidth="3" />
          {data.map((item, index) => {
            const x = 40 + index * 75
            const y = chartBottom - (item.gmv / max) * chartHeight * 0.92
            return (
              <g key={item.date} onClick={() => onOpen(item.date)} className="cursor-pointer">
                <circle cx={x} cy={y} r="5" fill="#3b82f6">
                  <title>{`${item.date}: GMV ${item.gmv} 万`}</title>
                </circle>
                {item.isPayday && <circle cx={x} cy="170" r="4" fill="#ef4444" />}
                <text x={x} y="181" textAnchor="middle" fontSize="11" fill="#374151">{item.date}</text>
              </g>
            )
          })}
        </svg>
        <div className="grid content-start gap-2">
          {[
            ['活动前', 'GMV 1,120', '+3.8%'],
            ['活动中', 'GMV 2,960', '+61.2%'],
            ['活动后', 'GMV 1,620', '+8.4%'],
          ].map(([label, value, delta]) => (
            <button key={label} onClick={() => onOpen(label)} className="rounded-xl border border-border bg-[#fbfcfe] px-3 py-2 text-left">
              <p className="text-xs text-muted-foreground">{label}</p>
              <p className="mt-1 text-sm font-bold">{value}</p>
              <p className="mt-1 text-xs font-semibold text-blue-600">{delta}</p>
            </button>
          ))}
        </div>
      </div>
    </ChartCard>
  )
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
    <ChartCard title="品类策略四象限（气泡图）">
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
            onClick={() => onOpen(item.category)}
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

function DashboardDrilldownDrawer({ open, title, onClose }: { open: boolean; title: string; onClose: () => void }) {
  if (!open) return null
  return (
    <div className="fixed inset-0 z-40 bg-black/20" onClick={onClose}>
      <aside className="absolute right-0 top-0 h-full w-full max-w-xl overflow-y-auto bg-white p-5 shadow-2xl" onClick={(event) => event.stopPropagation()}>
        <div className="flex items-center justify-between gap-3">
          <div>
            <h2 className="text-lg font-bold">{title} 明细</h2>
            <p className="mt-1 text-sm text-muted-foreground">按品类、指标与周期查看可解释贡献。</p>
          </div>
          <button className="rounded-lg p-2 hover:bg-[#f7f8fa]" onClick={onClose} aria-label="关闭">
            <X className="h-5 w-5" />
          </button>
        </div>
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
        <div className="mt-5 flex justify-end gap-2">
          <Button variant="outline">导出明细</Button>
          <Button>询问 Agent</Button>
        </div>
      </aside>
    </div>
  )
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

function Sparkline({ values, color }: { values: number[]; color: string }) {
  const max = Math.max(...values)
  const min = Math.min(...values)
  const points = values
    .map((value, index) => {
      const x = (index / Math.max(1, values.length - 1)) * 120
      const y = 36 - ((value - min) / Math.max(1, max - min)) * 28
      return `${x},${y}`
    })
    .join(' ')
  return (
    <svg viewBox="0 0 120 42" className="h-7 w-full">
      <polyline points={points} fill="none" stroke={color} strokeWidth="3" />
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
