'use client'

import { useEffect, useMemo, useState } from 'react'
import { AlertTriangle, BarChart3, LineChart, PieChart, RefreshCw } from 'lucide-react'
import { api } from '@/lib/api-client'
import type { Artifact, ChartArtifactData } from '@/lib/api-types'
import { Badge } from '@/components/ui/badge'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'

type ChartState = {
  chart: ChartArtifactData | null
  imageSrc: string | null
  error: string | null
}

type ChartArtifactGalleryProps = {
  projectId: string
  artifacts: Artifact[]
}

const palette = ['#2563eb', '#16a34a', '#f97316', '#7c3aed', '#0891b2', '#db2777']

export function ChartArtifactGallery({ projectId, artifacts }: ChartArtifactGalleryProps) {
  const chartArtifacts = useMemo(
    () =>
      artifacts
        .filter((artifact) => artifact.type === 'chart' || artifact.path.toLowerCase().includes('/charts/'))
        .slice(0, 4),
    [artifacts]
  )
  const [chartState, setChartState] = useState<Record<string, ChartState>>({})
  const [loading, setLoading] = useState(false)

  useEffect(() => {
    let cancelled = false
    async function loadCharts() {
      if (chartArtifacts.length === 0) {
        setChartState({})
        setLoading(false)
        return
      }
      setLoading(true)
      const entries = await Promise.all(
        chartArtifacts.map(async (artifact) => {
          const response = await api.getArtifactContent(projectId, artifact.id)
          if (!response.ok || !response.data) {
            return [artifact.id, { chart: null, imageSrc: null, error: response.error || '图表内容读取失败' }] as const
          }
          if (
            response.data.encoding === 'base64' &&
            response.data.content_type.startsWith('image/') &&
            typeof response.data.data === 'string'
          ) {
            return [
              artifact.id,
              {
                chart: null,
                imageSrc: `data:${response.data.content_type};base64,${response.data.data}`,
                error: null,
              },
            ] as const
          }
          if (response.data.encoding !== 'json' || !isChartData(response.data.data)) {
            return [artifact.id, { chart: null, imageSrc: null, error: '该产物不是可渲染的图表 JSON 或图片' }] as const
          }
          return [artifact.id, { chart: response.data.data, imageSrc: null, error: null }] as const
        })
      )
      if (!cancelled) {
        setChartState(Object.fromEntries(entries))
        setLoading(false)
      }
    }
    void loadCharts()
    return () => {
      cancelled = true
    }
  }, [chartArtifacts, projectId])

  return (
    <Card>
      <CardHeader className="pb-3">
        <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
          <div>
            <CardTitle className="text-base">图表证据</CardTitle>
            <CardDescription>直接读取已注册 chart artifact，并按原始 JSON 数据渲染。</CardDescription>
          </div>
          <Badge variant={chartArtifacts.length > 0 ? 'default' : 'secondary'}>
            {loading ? '读取中' : `${chartArtifacts.length} 个图表`}
          </Badge>
        </div>
      </CardHeader>
      <CardContent>
        {chartArtifacts.length === 0 ? (
          <div className="rounded-md border bg-secondary/25 p-4 text-sm text-muted-foreground">
            暂无图表产物。运行完整 pipeline 或 `chart.render` 后，这里会展示 GMV 趋势、LocalGap 等图表。
          </div>
        ) : (
          <div className="grid gap-4 xl:grid-cols-2">
            {chartArtifacts.map((artifact) => (
              <ChartArtifactCard
                key={artifact.id}
                artifact={artifact}
                chart={chartState[artifact.id]?.chart ?? null}
                imageSrc={chartState[artifact.id]?.imageSrc ?? null}
                error={chartState[artifact.id]?.error ?? null}
                loading={loading && !chartState[artifact.id]}
              />
            ))}
          </div>
        )}
      </CardContent>
    </Card>
  )
}

function ChartArtifactCard({
  artifact,
  chart,
  imageSrc,
  error,
  loading,
}: {
  artifact: Artifact
  chart: ChartArtifactData | null
  imageSrc: string | null
  error: string | null
  loading: boolean
}) {
  const chartType = imageSrc ? 'image' : chart?.type ?? 'unknown'
  const Icon = chartType === 'line' ? LineChart : chartType === 'pie' ? PieChart : BarChart3
  const metadata = chart?.metadata

  return (
    <div className="min-w-0 rounded-md border p-4">
      <div className="flex items-start justify-between gap-3">
        <div className="flex min-w-0 items-start gap-2">
          <div className="rounded-md bg-primary/10 p-2 text-primary">
            <Icon className="h-4 w-4" />
          </div>
          <div className="min-w-0">
            <p className="truncate text-sm font-medium">{chart?.title || artifact.title}</p>
            <p className="mt-1 break-all font-mono text-xs text-muted-foreground">{artifact.path}</p>
          </div>
        </div>
        <Badge variant="outline">{chartType}</Badge>
      </div>

      <div className="mt-4 min-h-56">
        {loading ? (
          <div className="flex h-56 items-center justify-center rounded-md bg-secondary/25 text-sm text-muted-foreground">
            <RefreshCw className="mr-2 h-4 w-4 animate-spin" />
            正在读取图表
          </div>
        ) : error ? (
          <div className="flex h-56 items-center justify-center rounded-md border border-amber-300 bg-amber-50 px-4 text-sm text-amber-800">
            <AlertTriangle className="mr-2 h-4 w-4" />
            {error}
          </div>
        ) : imageSrc ? (
          <div className="flex h-56 items-center justify-center rounded-md bg-secondary/20 p-3">
            <img src={imageSrc} alt={artifact.title} className="max-h-full max-w-full rounded-sm object-contain" />
          </div>
        ) : chart ? (
          <ChartRenderer chart={chart} />
        ) : (
          <div className="h-56 rounded-md bg-secondary/25" />
        )}
      </div>

      <div className="mt-4 grid gap-2 text-xs text-muted-foreground sm:grid-cols-2">
        <InfoLine label="证据" value={metadata?.evidence_artifacts?.[0]} />
        <InfoLine label="置信" value={metadata?.confidence?.label} />
        <InfoLine label="发现" value={metadata?.findings?.[0]} wide />
        <InfoLine label="限制" value={metadata?.limitations?.[0]} wide />
      </div>
    </div>
  )
}

function ChartRenderer({ chart }: { chart: ChartArtifactData }) {
  if (chart.type === 'line') return <LineSvg chart={chart} />
  if (chart.type === 'pie') return <DistributionChart chart={chart} />
  return <BarSvg chart={chart} />
}

function LineSvg({ chart }: { chart: ChartArtifactData }) {
  const values = toNumbers(chart.y)
  const labels = toLabels(chart.x)
  if (values.length === 0) return <EmptyChart />

  const width = 420
  const height = 220
  const pad = 38
  const minValue = Math.min(...values)
  const maxValue = Math.max(...values)
  const range = Math.max(maxValue - minValue, 1)
  const plotWidth = width - pad * 2
  const plotHeight = height - pad * 2
  const points = values.map((value, index) => {
    const x = pad + (values.length === 1 ? plotWidth / 2 : (index / (values.length - 1)) * plotWidth)
    const y = pad + (1 - (value - minValue) / range) * plotHeight
    return { x, y, value, label: labels[index] ?? '' }
  })
  const path = points.map((point) => `${point.x},${point.y}`).join(' ')

  return (
    <div className="rounded-md bg-secondary/20 p-3">
      <svg viewBox={`0 0 ${width} ${height}`} className="h-56 w-full" role="img" aria-label={chart.title || 'line chart'}>
        <line x1={pad} y1={height - pad} x2={width - pad} y2={height - pad} stroke="#d1d5db" />
        <line x1={pad} y1={pad} x2={pad} y2={height - pad} stroke="#d1d5db" />
        <text x={pad} y={pad - 10} className="fill-muted-foreground text-[11px]">{formatCompact(maxValue)}</text>
        <text x={pad} y={height - 8} className="fill-muted-foreground text-[11px]">{formatCompact(minValue)}</text>
        <polyline points={path} fill="none" stroke="#2563eb" strokeWidth="3" strokeLinejoin="round" strokeLinecap="round" />
        {points.map((point, index) => (
          <circle key={`${point.x}-${index}`} cx={point.x} cy={point.y} r="3.5" fill="#2563eb" />
        ))}
        <text x={pad} y={height - 3} className="fill-muted-foreground text-[11px]">{points[0]?.label}</text>
        <text x={width - pad} y={height - 3} textAnchor="end" className="fill-muted-foreground text-[11px]">
          {points[points.length - 1]?.label}
        </text>
      </svg>
    </div>
  )
}

function BarSvg({ chart }: { chart: ChartArtifactData }) {
  const values = toNumbers(chart.y)
  const labels = toLabels(chart.x)
  if (values.length === 0) return <EmptyChart />

  const width = 420
  const height = 220
  const pad = 42
  const plotWidth = width - pad * 2
  const plotHeight = height - pad * 2
  const minValue = Math.min(0, ...values)
  const maxValue = Math.max(0, ...values)
  const range = Math.max(maxValue - minValue, 1)
  const zeroY = pad + (1 - (0 - minValue) / range) * plotHeight
  const slot = plotWidth / Math.max(values.length, 1)
  const barWidth = Math.min(42, slot * 0.58)

  return (
    <div className="rounded-md bg-secondary/20 p-3">
      <svg viewBox={`0 0 ${width} ${height}`} className="h-56 w-full" role="img" aria-label={chart.title || 'bar chart'}>
        <line x1={pad} y1={zeroY} x2={width - pad} y2={zeroY} stroke="#d1d5db" />
        <line x1={pad} y1={pad} x2={pad} y2={height - pad} stroke="#d1d5db" />
        <text x={pad} y={pad - 10} className="fill-muted-foreground text-[11px]">{formatCompact(maxValue)}</text>
        <text x={pad} y={height - 8} className="fill-muted-foreground text-[11px]">{formatCompact(minValue)}</text>
        {values.map((value, index) => {
          const x = pad + index * slot + (slot - barWidth) / 2
          const y = pad + (1 - (value - minValue) / range) * plotHeight
          const top = Math.min(y, zeroY)
          const barHeight = Math.max(Math.abs(zeroY - y), 2)
          return (
            <g key={`${labels[index]}-${index}`}>
              <rect x={x} y={top} width={barWidth} height={barHeight} rx="4" fill={palette[index % palette.length]} />
              <text x={x + barWidth / 2} y={height - 8} textAnchor="middle" className="fill-muted-foreground text-[10px]">
                {truncate(labels[index] ?? String(index + 1), 8)}
              </text>
            </g>
          )
        })}
      </svg>
    </div>
  )
}

function DistributionChart({ chart }: { chart: ChartArtifactData }) {
  const labels = toLabels(chart.labels ?? chart.x)
  const values = toNumbers(chart.values ?? chart.y)
  if (values.length === 0) return <EmptyChart />
  const total = values.reduce((sum, value) => sum + Math.abs(value), 0) || 1

  return (
    <div className="rounded-md bg-secondary/20 p-4">
      <div className="flex h-12 overflow-hidden rounded-md border bg-background">
        {values.map((value, index) => (
          <div
            key={`${labels[index]}-${index}`}
            style={{ width: `${Math.max((Math.abs(value) / total) * 100, 2)}%`, backgroundColor: palette[index % palette.length] }}
            title={`${labels[index]} ${formatCompact(value)}`}
          />
        ))}
      </div>
      <div className="mt-4 grid gap-2 sm:grid-cols-2">
        {values.map((value, index) => (
          <div key={`${labels[index]}-legend-${index}`} className="flex items-center justify-between gap-3 text-xs">
            <span className="flex min-w-0 items-center gap-2">
              <span className="h-2.5 w-2.5 shrink-0 rounded-sm" style={{ backgroundColor: palette[index % palette.length] }} />
              <span className="truncate">{labels[index]}</span>
            </span>
            <span className="font-medium">{formatCompact(value)}</span>
          </div>
        ))}
      </div>
    </div>
  )
}

function InfoLine({ label, value, wide }: { label: string; value?: string; wide?: boolean }) {
  if (!value) return null
  return (
    <div className={wide ? 'sm:col-span-2' : ''}>
      <span className="font-medium text-foreground">{label}：</span>
      <span>{value}</span>
    </div>
  )
}

function EmptyChart() {
  return <div className="flex h-56 items-center justify-center rounded-md bg-secondary/25 text-sm text-muted-foreground">暂无可绘制数据</div>
}

function isChartData(value: unknown): value is ChartArtifactData {
  return Boolean(value && typeof value === 'object' && 'type' in value)
}

function toNumbers(values?: Array<number | string | null>) {
  return (values ?? [])
    .map((value) => (typeof value === 'number' ? value : Number(String(value ?? '').replace(/,/g, ''))))
    .filter((value) => Number.isFinite(value))
}

function toLabels(values?: Array<string | number | null>) {
  return (values ?? []).map((value) => String(value ?? ''))
}

function formatCompact(value: number) {
  return new Intl.NumberFormat('zh-CN', { maximumFractionDigits: 1, notation: Math.abs(value) >= 10000 ? 'compact' : 'standard' }).format(value)
}

function truncate(value: string, max: number) {
  return value.length > max ? `${value.slice(0, max - 1)}…` : value
}
