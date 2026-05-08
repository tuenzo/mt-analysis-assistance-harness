export type DashboardFilters = {
  timeRange: [string, string]
  activityWindow: 'all' | 'pre' | 'during' | 'post'
  categoryLevel: 'all' | 'top' | 'mid' | 'longtail'
  calendarType: 'all' | 'payday' | 'nonpayday'
}

export type KpiCardData = {
  key: string
  label: string
  value: string
  unit?: string
  subText: string
  trendText?: string
  trendDirection?: 'up' | 'down' | 'flat'
  color: 'green' | 'blue' | 'orange' | 'purple'
  sparkline: number[]
}

export type ParetoDatum = {
  category: string
  gmv: number
  cumulativeRatio: number
}

export type WaterfallDatum = {
  name: string
  value: number
  type: 'baseline' | 'positive' | 'negative' | 'total'
}

export type TrendDatum = {
  date: string
  gmv: number
  exposure?: number
  discount?: number
  isActivityDay?: boolean
  isPayday?: boolean
}

export type QuadrantItem = {
  category: string
  x: number
  y: number
  size: number
  group: 'boost' | 'maintain' | 'reduce' | 'avoid'
  color: string
  suggestedAction: string
}

export type RecommendationGroup = {
  key: 'boost' | 'control_discount' | 'watch' | 'avoid'
  title: string
  description: string
  count: number
  countLabel: string
  categories: string[]
  color: 'green' | 'orange' | 'blue' | 'purple'
}

export type DashboardSummary = {
  conclusion: string
  kpis: KpiCardData[]
  pareto: ParetoDatum[]
  localGap: WaterfallDatum[]
  trend: TrendDatum[]
  quadrants: QuadrantItem[]
  recommendations: RecommendationGroup[]
}
