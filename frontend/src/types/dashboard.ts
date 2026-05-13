export type DashboardFilters = {
  timeRange: [string, string]
  activityWindow: 'all' | 'pre' | 'during' | 'post'
  categoryLevel: 'all' | 'top' | 'mid' | 'longtail'
  calendarType: 'all' | 'payday' | 'nonpayday'
}

export type SparklinePoint = {
  label: string
  value: number
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
  chartType: 'line' | 'bar'
  signed?: boolean
  series: SparklinePoint[]
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
  baselineGmv: number
  exposure?: number
  discount?: number
  isActivityDay?: boolean
  isPayday?: boolean
  period: 'pre' | 'during' | 'post'
}

export type QuadrantItem = {
  category: string
  x: number
  y: number
  size: number
  group: 'boost' | 'maintain' | 'reduce' | 'avoid' | 'control_discount' | 'watch'
  color: string
  suggestedAction: string
  resourceType?: '曝光' | '折扣'
  quadrant?: 'Persuadables' | 'Sure Things' | 'Lost Causes' | 'Do Not Disturb'
  count?: number
  contribution?: number
  representativeCategories?: string[]
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
  valueUnit?: string
  valueScale?: number
  valueUnitSource?: string
  qualityStatus?: 'ready' | 'limited' | 'unknown'
  qualityReasons?: string[]
  conclusion: string
  kpis: KpiCardData[]
  pareto: ParetoDatum[]
  localGap: WaterfallDatum[]
  trend: TrendDatum[]
  quadrants: QuadrantItem[]
  recommendations: RecommendationGroup[]
}
