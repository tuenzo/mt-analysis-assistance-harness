import type { Artifact, LatestReport, ProjectState } from '@/lib/api-types'
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

export type DashboardSummarySource = {
  state: ProjectState | null
  artifacts: Artifact[]
  report: LatestReport | null
  latestResult?: unknown
  panelSummary?: unknown
}

type JsonRecord = Record<string, unknown>
type RecommendationKey = RecommendationGroup['key']
type UnitContext = {
  unitLabel: string
  scale: number
  source: string
}
type QualityContext = {
  status: DashboardSummary['qualityStatus']
  reasons: string[]
}

const recommendationTemplates: Record<
  RecommendationKey,
  Pick<RecommendationGroup, 'key' | 'title' | 'description' | 'color'>
> = {
  boost: {
    key: 'boost',
    title: '优先加码',
    description: '来自 latest_result 的高 uplift 或高 LocalGap 动作建议。',
    color: 'green',
  },
  control_discount: {
    key: 'control_discount',
    title: '控制折扣',
    description: '折扣响应或模型 uplift 偏弱，适合先收窄补贴。',
    color: 'orange',
  },
  watch: {
    key: 'watch',
    title: '小规模验证',
    description: '证据方向存在但样本或稳定性有限，先做 holdout / event-study。',
    color: 'blue',
  },
  avoid: {
    key: 'avoid',
    title: '避免打扰',
    description: '响应弱或负向风险较高，减少泛化触达。',
    color: 'purple',
  },
}

const quadrantColors: Record<QuadrantItem['group'], string> = {
  boost: '#22c55e',
  maintain: '#60a5fa',
  reduce: '#f97316',
  avoid: '#a78bfa',
  control_discount: '#f59e0b',
  watch: '#3b82f6',
}

const emptyGroups = (): RecommendationGroup[] =>
  (['boost', 'control_discount', 'watch', 'avoid'] as RecommendationKey[]).map((key) =>
    makeRecommendationGroup(key, []),
  )

export function buildDashboardSummary(source: DashboardSummarySource): DashboardSummary {
  const latestResult = asRecord(source.latestResult)
  const panelSummary = asRecord(source.panelSummary)
  const diagnostics = resultSection(latestResult, 'diagnostics', ['gmv_trend', 'category_concentration'])
  const localgap = resultSection(latestResult, 'localgap', ['total_local_gap', 'categories', 'monthly_decomposition'])
  const uplift = resultSection(latestResult, 'uplift', ['recommended_actions', 'uplift_ranking'])
  const recommendedActions = readRecommendedActions(latestResult, uplift)
  const unitContext = readUnitContext(panelSummary, localgap)
  const quality = readQualityContext(panelSummary, localgap, diagnostics)

  if (!panelSummary && !diagnostics && !localgap && recommendedActions.length === 0) {
    return buildEmptyDashboardSummary(source, unitContext)
  }

  const trend = buildTrend(diagnostics, localgap)
  const pareto = buildPareto(diagnostics, localgap)
  const localGap = buildLocalGap(localgap, trend)
  const limitedEvidence = quality.status === 'limited'
  const recommendations = buildRecommendations(recommendedActions, localgap, pareto, limitedEvidence)
  const quadrants = buildQuadrants(recommendedActions, localgap, pareto, limitedEvidence)
  const kpis = buildKpis({ trend, localgap, recommendations, panelSummary, unitContext })

  return {
    valueUnit: unitContext.unitLabel,
    valueScale: unitContext.scale,
    valueUnitSource: unitContext.source,
    qualityStatus: quality.status,
    qualityReasons: quality.reasons,
    conclusion: buildConclusion({ panelSummary, localgap, pareto, recommendations, trend, unitContext, quality }),
    kpis,
    pareto,
    localGap,
    trend,
    quadrants,
    recommendations,
  }
}

export function buildDashboardInitialFilters(summary: DashboardSummary): DashboardFilters {
  const [start, end] = getTrendDateRange(summary)
  return {
    timeRange: [start, end],
    activityWindow: 'all',
    categoryLevel: 'all',
    calendarType: 'all',
  }
}

export function buildDashboardTimeRangeLabel(summary: DashboardSummary) {
  const [start, end] = getTrendDateRange(summary)
  if (!start || !end) return '暂无真实分析时间范围'
  return start === end ? start : `${start}~${end}`
}

export function hasRealDashboardSummary(summary: DashboardSummary) {
  return summary.trend.length > 0 || summary.pareto.length > 0 || summary.localGap.some((item) => item.value !== 0)
}

function buildEmptyDashboardSummary(source: DashboardSummarySource, unitContext: UnitContext): DashboardSummary {
  const fileCount = source.state?.files_count ?? 0
  const artifactCount = source.artifacts.length || source.state?.artifacts_count || 0
  const reportCount = source.state?.reports_count ?? (source.report ? 1 : 0)
  const context = [
    fileCount > 0 ? `${fileCount} 个文件已接入` : '尚未接入文件',
    artifactCount > 0 ? `${artifactCount} 个产物可复核` : '尚未发现分析产物',
    reportCount > 0 ? `${reportCount} 份报告可查看` : '尚未生成报告',
  ].join('，')

  return {
    valueUnit: unitContext.unitLabel,
    valueScale: unitContext.scale,
    valueUnitSource: unitContext.source,
    qualityStatus: 'unknown',
    qualityReasons: [],
    conclusion: `${context}；请先运行完整分析 pipeline 生成真实结果。`,
    kpis: [
      makeKpi('gmv_increment', 'GMV 净增量', '待分析', undefined, '等待 LocalGap 结果', 'green', 'line', []),
      makeKpi('exposure_contribution', '曝光贡献', '待分析', undefined, '等待分解产物', 'blue', 'bar', []),
      makeKpi('discount_contribution', '折扣贡献', '待分析', undefined, '等待分解产物', 'orange', 'line', []),
      makeKpi('boost_categories', '建议优先加码品类数', '0', '个', '暂无策略分层', 'purple', 'line', []),
    ],
    pareto: [],
    localGap: [
      { name: '基线GMV', value: 0, type: 'baseline' },
      { name: '曝光贡献', value: 0, type: 'positive' },
      { name: '折扣贡献', value: 0, type: 'positive' },
      { name: '发薪日贡献', value: 0, type: 'positive' },
      { name: '残差/未拆分', value: 0, type: 'positive' },
      { name: '实际GMV', value: 0, type: 'total' },
    ],
    trend: [],
    quadrants: [],
    recommendations: emptyGroups(),
  }
}

function buildTrend(diagnostics: JsonRecord | null, localgap: JsonRecord | null): TrendDatum[] {
  const rows = asRecordArray(diagnostics?.gmv_trend)
  const totalGap = getTotalLocalGap(localgap)
  const totalExposure = sumLocalGapCategory(localgap, 'exposure_gap')
  const totalDiscount = sumLocalGapCategory(localgap, 'discount_gap')
  const activityRows = rows.filter((row) => toNumber(row.activity_rows) > 0)
  const activityGmvTotal = sum(activityRows, (row) => toNumber(row.gmv))
  const firstActivityDate = toText(activityRows[0]?.date)
  const lastActivityDate = toText(activityRows.at(-1)?.date)

  return rows
    .map((row) => {
      const date = toText(row.date)
      const actualGmv = toNumber(row.gmv)
      const isActivityDay = toNumber(row.activity_rows) > 0
      const preActivityRows = toNumber(row.pre_activity_rows)
      const postActivityRows = toNumber(row.post_activity_rows)
      const localGapShare =
        isActivityDay && activityGmvTotal > 0
          ? actualGmv / activityGmvTotal
          : 0
      const localGap = roundMoney(totalGap * localGapShare)
      const rollingBaseline = toNumber(row.rolling_7d_gmv, actualGmv)
      const baselineGmv = totalGap > 0
        ? roundMoney(Math.max(0, actualGmv - localGap))
        : roundMoney(rollingBaseline)

      return {
        date,
        gmv: roundMoney(actualGmv),
        baselineGmv,
        exposure: roundMoney(totalExposure * localGapShare),
        discount: roundMoney(totalDiscount * localGapShare),
        isActivityDay,
        isPayday: inferPayday(date),
        period: inferPeriod(date, isActivityDay, preActivityRows, postActivityRows, firstActivityDate, lastActivityDate),
      }
    })
    .filter((item) => item.date)
}

function buildPareto(diagnostics: JsonRecord | null, localgap: JsonRecord | null): ParetoDatum[] {
  const diagnosticsRows = asRecordArray(diagnostics?.category_concentration)
  if (diagnosticsRows.length > 0) {
    const rows = diagnosticsRows.map((row) => ({
      category: toText(row.category || row.category_key),
      gmv: roundMoney(toNumber(row.gmv || row.actual_gmv)),
      cumulativeRatio: toNumber(row.cumulative_share, Number.NaN),
    }))
    return fillCumulativeRatio(rows.filter((row) => row.category && row.gmv >= 0))
  }

  const categoryRows = asRecordArray(localgap?.categories)
  return fillCumulativeRatio(
    categoryRows
      .map((row) => ({
        category: toText(row.category || row.category_key),
        gmv: roundMoney(toNumber(row.actual_gmv)),
        cumulativeRatio: Number.NaN,
      }))
      .filter((row) => row.category && row.gmv >= 0),
  )
}

function buildLocalGap(localgap: JsonRecord | null, trend: TrendDatum[]): WaterfallDatum[] {
  const actual = toNumber(localgap?.total_actual_gmv, sum(trend, (item) => item.gmv))
  const baseline = toNumber(
    localgap?.total_baseline_gmv,
    Math.max(0, actual - getTotalLocalGap(localgap)),
  )
  const totalGap = getTotalLocalGap(localgap) || roundMoney(actual - baseline)
  const exposure = sumLocalGapCategory(localgap, 'exposure_gap')
  const discount = sumLocalGapCategory(localgap, 'discount_gap')
  const payday = sumLocalGapCategory(localgap, 'payday_gap')
  const interaction = sumLocalGapCategory(localgap, 'interaction')
  const residual = roundMoney(totalGap - exposure - discount - payday - interaction)

  return [
    { name: '基线GMV', value: roundMoney(baseline), type: 'baseline' },
    { name: '曝光贡献', value: roundMoney(exposure), type: exposure >= 0 ? 'positive' : 'negative' },
    { name: '折扣贡献', value: roundMoney(discount), type: discount >= 0 ? 'positive' : 'negative' },
    { name: '发薪日贡献', value: roundMoney(payday), type: payday >= 0 ? 'positive' : 'negative' },
    { name: '残差/未拆分', value: residual, type: residual >= 0 ? 'positive' : 'negative' },
    { name: '实际GMV', value: roundMoney(actual), type: 'total' },
  ]
}

function buildRecommendations(
  actions: JsonRecord[],
  localgap: JsonRecord | null,
  pareto: ParetoDatum[],
  limitedEvidence: boolean,
): RecommendationGroup[] {
  const buckets: Record<RecommendationKey, string[]> = {
    boost: [],
    control_discount: [],
    watch: [],
    avoid: [],
  }

  if (actions.length > 0) {
    for (const action of actions) {
      const category = toText(action.category || action.category_key)
      if (!category) continue
      const key = categorizeRecommendation(action, limitedEvidence)
      addUnique(buckets[key], category)

      const modelUplift = toNumber(action.model_uplift, 0)
      const doseUplift = toNumber(action.dose_uplift, 0)
      if ((modelUplift < 0 || doseUplift < 0) && key !== 'avoid') {
        addUnique(buckets.control_discount, category)
      }
    }
  } else {
    for (const row of asRecordArray(localgap?.categories)) {
      const category = toText(row.category || row.category_key)
      const localGap = toNumber(row.local_gap)
      if (!category) continue
      addUnique(buckets[localGap > 0 ? 'watch' : 'avoid'], category)
    }
  }

  if (Object.values(buckets).every((items) => items.length === 0) && pareto.length > 0) {
    addUnique(buckets.watch, pareto[0].category)
  }

  return (['boost', 'control_discount', 'watch', 'avoid'] as RecommendationKey[]).map((key) =>
    makeRecommendationGroup(key, buckets[key]),
  )
}

function buildQuadrants(
  actions: JsonRecord[],
  localgap: JsonRecord | null,
  pareto: ParetoDatum[],
  limitedEvidence: boolean,
): QuadrantItem[] {
  const sourceRows = actions.length > 0 ? actions : asRecordArray(localgap?.categories)
  const maxContribution = Math.max(
    1,
    ...sourceRows.map((row) => Math.abs(toNumber(row.local_gap || row.gmv || row.actual_gmv))),
  )

  const items = sourceRows
    .map((row, index): QuadrantItem | null => {
      const category = toText(row.category || row.category_key)
      if (!category) return null

      const score = toNumber(row.uplift_score, Number.NaN)
      const contribution = toNumber(row.local_gap || row.gmv || row.actual_gmv)
      const group = actions.length > 0 ? categorizeRecommendation(row, limitedEvidence) : contribution > 0 ? 'watch' : 'avoid'
      const normalizedScore = Number.isFinite(score)
        ? clamp(score, 12, 88)
        : clamp(35 + index * 9, 12, 88)
      const contributionScore = clamp(25 + (Math.max(0, contribution) / maxContribution) * 55, 18, 82)

      return {
        category,
        x: normalizedScore,
        y: contributionScore,
        size: roundMoney(Math.max(18, Math.sqrt(Math.abs(contribution) / maxContribution) * 42)),
        group,
        color: quadrantColors[group],
        suggestedAction: translateAction(row),
        contribution: roundMoney(contribution),
      }
    })
    .filter((item): item is QuadrantItem => Boolean(item))

  if (items.length > 0) return items

  return pareto.slice(0, 6).map((row, index) => ({
    category: row.category,
    x: clamp(30 + index * 10, 18, 82),
    y: clamp(70 - index * 8, 20, 80),
    size: 24,
    group: 'watch',
    color: quadrantColors.watch,
    suggestedAction: '等待 uplift 结果后再决策。',
    contribution: roundMoney(row.gmv),
  }))
}

function buildKpis({
  trend,
  localgap,
  recommendations,
  panelSummary,
  unitContext,
}: {
  trend: TrendDatum[]
  localgap: JsonRecord | null
  recommendations: RecommendationGroup[]
  panelSummary: JsonRecord | null
  unitContext: UnitContext
}): KpiCardData[] {
  const totalGap = getTotalLocalGap(localgap) || sum(trend, (item) => item.gmv - item.baselineGmv)
  const baseline = toNumber(localgap?.total_baseline_gmv, Math.max(0, toNumber(panelSummary?.total_gmv) - totalGap))
  const exposure = sumLocalGapCategory(localgap, 'exposure_gap')
  const discount = sumLocalGapCategory(localgap, 'discount_gap')
  const boostCount = recommendations.find((group) => group.key === 'boost')?.categories.length ?? 0
  const netSeries = trend.map((item) => ({ label: item.date, value: roundMoney(item.gmv - item.baselineGmv) }))
  const exposureSeries = trend.map((item) => ({ label: item.date, value: roundMoney(item.exposure ?? 0) }))
  const discountSeries = trend.map((item) => ({ label: item.date, value: roundMoney(item.discount ?? 0) }))
  const boostSeries = buildBoostSeries(trend, boostCount)
  const netParts = formatCurrencyParts(totalGap, false, unitContext)
  const exposureParts = formatCurrencyParts(exposure, true, unitContext)
  const discountParts = formatCurrencyParts(discount, true, unitContext)

  return [
    makeKpi(
      'gmv_increment',
      'GMV 净增量',
      netParts.value,
      netParts.unit,
      `较基线 ${formatSignedPercent(totalGap, baseline)}`,
      'green',
      'line',
      netSeries,
      totalGap,
      true,
    ),
    makeKpi(
      'exposure_contribution',
      '曝光贡献',
      exposureParts.value,
      exposureParts.unit,
      `占净增量 ${formatSharePercent(exposure, totalGap)}`,
      'blue',
      'bar',
      exposureSeries,
      exposure,
      false,
    ),
    makeKpi(
      'discount_contribution',
      '折扣贡献',
      discountParts.value,
      discountParts.unit,
      `占净增量 ${formatSharePercent(discount, totalGap)}`,
      'orange',
      'line',
      discountSeries,
      discount,
      true,
    ),
    makeKpi(
      'boost_categories',
      '建议优先加码品类数',
      `${boostCount}`,
      '个',
      boostCount > 0 ? `真实策略结果 ${boostCount} 个品类` : '暂无直接加码建议',
      'purple',
      'line',
      boostSeries,
      boostCount,
      false,
    ),
  ]
}

function buildConclusion({
  panelSummary,
  localgap,
  pareto,
  recommendations,
  trend,
  unitContext,
  quality,
}: {
  panelSummary: JsonRecord | null
  localgap: JsonRecord | null
  pareto: ParetoDatum[]
  recommendations: RecommendationGroup[]
  trend: TrendDatum[]
  unitContext: UnitContext
  quality: QualityContext
}) {
  const range = getRangeFromPanel(panelSummary) || getRangeFromTrend(trend)
  const totalGmv = toNumber(panelSummary?.total_gmv)
  const gap = getTotalLocalGap(localgap)
  const topCategory = pareto[0]?.category
  const boost = recommendations.find((group) => group.key === 'boost')?.categories[0]
  const watch = recommendations.find((group) => group.key === 'watch')?.categories[0]
  const focus = boost || watch || topCategory
  const parts = [
    range ? `真实数据周期 ${range}` : '',
    totalGmv > 0 ? `累计 GMV ${formatCurrencyText(totalGmv, false, unitContext)}` : '',
    gap !== 0 ? `LocalGap 净增量 ${formatCurrencyText(gap, true, unitContext)}` : '',
    quality.status === 'limited' ? '证据 limited，仅适合流程校验和小规模验证' : '',
    focus ? `当前优先复核 ${focus}` : '',
  ].filter(Boolean)

  return parts.length > 0 ? parts.join('；') : '已读取真实分析产物，但关键指标仍需继续补齐。'
}

function readRecommendedActions(latestResult: JsonRecord | null, uplift: JsonRecord | null) {
  const topLevel = asRecordArray(latestResult?.recommended_actions)
  if (topLevel.length > 0) return topLevel
  return asRecordArray(uplift?.recommended_actions)
}

function resultSection(latestResult: JsonRecord | null, key: string, ownKeys: string[]) {
  const section = asRecord(latestResult?.[key])
  if (section) return section
  if (latestResult && ownKeys.some((ownKey) => ownKey in latestResult)) return latestResult
  return null
}

function defaultUnitContext(): UnitContext {
  return {
    unitLabel: '元',
    scale: 1,
    source: 'No source-unit metadata was available; GMV values are treated as yuan.',
  }
}

function readUnitContext(panelSummary: JsonRecord | null, localgap: JsonRecord | null): UnitContext {
  const measureUnits = asRecord(panelSummary?.measure_units) || asRecord(localgap?.measure_units)
  const gmvUnit = asRecord(measureUnits?.gmv)
  if (!gmvUnit) return defaultUnitContext()
  const unitLabel = normalizeAmountUnitLabel(toText(gmvUnit.unit_label || gmvUnit.unit))
  const rawScale = toNumber(gmvUnit.scale, 1)
  return {
    unitLabel,
    scale: rawScale > 0 ? rawScale : 1,
    source: toText(gmvUnit.provenance) || 'Values remain in raw GMV source units.',
  }
}

function readQualityContext(
  panelSummary: JsonRecord | null,
  localgap: JsonRecord | null,
  diagnostics: JsonRecord | null,
): QualityContext {
  const statuses = [
    toText(asRecord(panelSummary?.analysis_readiness)?.status),
    toText(asRecord(localgap?.quality_gate)?.status),
    toText(localgap?.method_status),
    toText(diagnostics?.method_status),
  ].filter(Boolean)
  const reasons = [
    ...asTextArray(asRecord(panelSummary?.analysis_readiness)?.reasons),
    ...asTextArray(asRecord(localgap?.quality_gate)?.reasons),
    ...asTextArray(localgap?.warnings),
    ...asTextArray(diagnostics?.warnings),
  ]
  const dedupedReasons = Array.from(new Set(reasons))
  if (statuses.includes('limited')) {
    return { status: 'limited', reasons: dedupedReasons }
  }
  if (statuses.length === 0) return { status: 'unknown', reasons: dedupedReasons }
  return { status: 'ready', reasons: dedupedReasons }
}

function makeKpi(
  key: string,
  label: string,
  value: string,
  unit: string | undefined,
  subText: string,
  color: KpiCardData['color'],
  chartType: KpiCardData['chartType'],
  series: SparklinePoint[],
  trendValue = 0,
  signed = false,
): KpiCardData {
  return {
    key,
    label,
    value,
    unit,
    subText,
    trendText: key === 'boost_categories' ? value : formatSignedPercent(trendValue, Math.abs(trendValue) || 1),
    trendDirection: trendValue > 0 ? 'up' : trendValue < 0 ? 'down' : 'flat',
    color,
    chartType,
    signed,
    series,
  }
}

function makeRecommendationGroup(key: RecommendationKey, categories: string[]): RecommendationGroup {
  const template = recommendationTemplates[key]
  return {
    ...template,
    count: categories.length,
    countLabel: `${categories.length} 个品类`,
    categories,
  }
}

function categorizeRecommendation(action: JsonRecord, limitedEvidence = false): RecommendationKey {
  const actionText = `${toText(action.action)} ${toText(action.bucket)} ${toText(action.reason)}`.toLowerCase()
  const score = toNumber(action.uplift_score, Number.NaN)
  const modelUplift = toNumber(action.model_uplift, 0)
  const doseUplift = toNumber(action.dose_uplift, 0)
  const localGap = toNumber(action.local_gap, Number.NaN)
  const isNegative = (Number.isFinite(score) && score < 0) || (Number.isFinite(localGap) && localGap < 0)
  const hasPrioritizeSignal =
    actionText.includes('prioritize') ||
    actionText.includes('protect_high_response') ||
    actionText.includes('boost') ||
    actionText.includes('scale')
  const hasObserveSignal =
    actionText.includes('observe') ||
    actionText.includes('refresh') ||
    actionText.includes('selective') ||
    actionText.includes('holdout') ||
    actionText.includes('test')

  if (actionText.includes('avoid') || actionText.includes('do_not') || actionText.includes('reduce')) return 'avoid'
  if (limitedEvidence) {
    if (Number.isFinite(score) && score < 30) return 'avoid'
    if (modelUplift < 0 || doseUplift < 0) return 'control_discount'
    return 'watch'
  }
  if (isNegative) return doseUplift < 0 ? 'control_discount' : 'avoid'
  if (modelUplift < 0 || doseUplift < 0) return 'control_discount'
  if (hasObserveSignal) return 'watch'
  if (hasPrioritizeSignal) return 'boost'
  if (Number.isFinite(score) && score >= 60) return 'boost'
  if (Number.isFinite(score) && score < 30) return 'avoid'
  if (actionText.includes('discount') && !actionText.includes('exposure')) return 'control_discount'
  return 'watch'
}

function translateAction(action: JsonRecord) {
  const guardrail = toText(action.guardrail)
  if (guardrail) return guardrail
  const rawAction = toText(action.action)
  if (!rawAction) return '等待下一轮分析确认动作。'
  return rawAction
    .replace(/_/g, ' ')
    .replace('controlled discount or exposure test', '先做小规模折扣或曝光对照实验')
}

function fillCumulativeRatio(rows: ParetoDatum[]): ParetoDatum[] {
  const sorted = [...rows].sort((a, b) => b.gmv - a.gmv)
  const total = sum(sorted, (row) => row.gmv)
  let running = 0
  return sorted.map((row) => {
    running += row.gmv
    return {
      ...row,
      cumulativeRatio: Number.isFinite(row.cumulativeRatio)
        ? roundMoney(row.cumulativeRatio)
        : total > 0
          ? roundMoney((running / total) * 100)
          : 0,
    }
  })
}

function buildBoostSeries(trend: TrendDatum[], boostCount: number): SparklinePoint[] {
  if (trend.length === 0) return boostCount > 0 ? [{ label: '当前', value: boostCount }] : []
  return trend.map((item) => ({
    label: item.date,
    value: item.isActivityDay ? boostCount : Math.max(0, boostCount - 1),
  }))
}

function getTotalLocalGap(localgap: JsonRecord | null) {
  return roundMoney(
    toNumber(
      localgap?.total_local_gap,
      sum(asRecordArray(localgap?.categories), (row) => toNumber(row.local_gap)),
    ),
  )
}

function sumLocalGapCategory(localgap: JsonRecord | null, key: string) {
  return roundMoney(sum(asRecordArray(localgap?.categories), (row) => toNumber(row[key])))
}

function inferPeriod(
  date: string,
  isActivityDay: boolean,
  preActivityRows: number,
  postActivityRows: number,
  firstActivityDate: string,
  lastActivityDate: string,
): TrendDatum['period'] {
  if (isActivityDay) return 'during'
  if (preActivityRows > 0) return 'pre'
  if (postActivityRows > 0) return 'post'
  if (firstActivityDate && date < firstActivityDate) return 'pre'
  if (lastActivityDate && date > lastActivityDate) return 'post'
  return firstActivityDate ? 'post' : 'pre'
}

function inferPayday(date: string) {
  const day = Number(date.match(/-(\d{2})$/)?.[1])
  if (!Number.isFinite(day)) return false
  return day <= 2 || day >= 27
}

function getTrendDateRange(summary: DashboardSummary): [string, string] {
  const dates = summary.trend.map((item) => item.date).filter(Boolean)
  if (dates.length === 0) return ['', '']
  return [dates[0], dates[dates.length - 1]]
}

function getRangeFromTrend(trend: TrendDatum[]) {
  if (trend.length === 0) return ''
  const first = trend[0]?.date
  const last = trend.at(-1)?.date
  if (!first || !last) return ''
  return first === last ? first : `${first}~${last}`
}

function getRangeFromPanel(panelSummary: JsonRecord | null) {
  const dateRange = asRecord(panelSummary?.date_range)
  const start = toText(dateRange?.start)
  const end = toText(dateRange?.end)
  if (!start || !end) return ''
  return start === end ? start : `${start}~${end}`
}

function formatCurrencyParts(value: number, signed = false, unitContext = defaultUnitContext()) {
  const displayScale = displayCurrencyScale([value], unitContext)
  const displayValue = value / displayScale
  const prefix = signed && value > 0 ? '+' : ''
  return {
    value: `${prefix}${formatNumber(displayValue)}`,
    unit: displayCurrencyUnit(displayScale, unitContext),
  }
}

function formatCurrencyText(value: number, signed = false, unitContext = defaultUnitContext()) {
  const parts = formatCurrencyParts(value, signed, unitContext)
  return `${parts.value} ${parts.unit}`
}

function formatSignedPercent(numerator: number, denominator: number) {
  if (!Number.isFinite(numerator) || !Number.isFinite(denominator) || denominator === 0) return '+0.0%'
  const percent = (numerator / denominator) * 100
  return `${percent >= 0 ? '+' : ''}${percent.toFixed(1)}%`
}

function formatSharePercent(part: number, total: number) {
  if (!Number.isFinite(part) || !Number.isFinite(total) || total === 0) return '0.0%'
  return `${((part / total) * 100).toFixed(1)}%`
}

function normalizeAmountUnitLabel(unitLabel?: string) {
  const normalized = String(unitLabel || '').trim()
  if (!normalized || normalized.includes('原始单位')) return '元'
  return normalized
}

function displayCurrencyScale(values: number[], unitContext = defaultUnitContext()) {
  const baseUnit = normalizeAmountUnitLabel(unitContext.unitLabel)
  const maxValue = Math.max(0, ...values.filter(Number.isFinite).map((value) => Math.abs(value)))
  if ((unitContext.scale <= 1 || baseUnit === '元') && maxValue >= 10000) return 10000
  return unitContext.scale > 0 ? unitContext.scale : 1
}

function displayCurrencyUnit(scale: number, unitContext = defaultUnitContext()) {
  const baseUnit = normalizeAmountUnitLabel(unitContext.unitLabel)
  if (scale === 10000 && baseUnit === '元') return '万元'
  return baseUnit
}

function addUnique(list: string[], item: string) {
  if (!list.includes(item)) list.push(item)
}

function sum<T>(items: T[], getValue: (item: T) => number) {
  return items.reduce((total, item) => total + getValue(item), 0)
}

function asRecord(value: unknown): JsonRecord | null {
  return Boolean(value && typeof value === 'object' && !Array.isArray(value))
    ? value as JsonRecord
    : null
}

function asRecordArray(value: unknown): JsonRecord[] {
  return Array.isArray(value)
    ? value.map(asRecord).filter((item): item is JsonRecord => Boolean(item))
    : []
}

function asTextArray(value: unknown): string[] {
  return Array.isArray(value)
    ? value.map(toText).filter(Boolean)
    : []
}

function toNumber(value: unknown, fallback = 0) {
  if (typeof value === 'number' && Number.isFinite(value)) return value
  if (typeof value === 'string') {
    const numeric = Number(value.replace(/[,%]/g, '').trim())
    if (Number.isFinite(numeric)) return numeric
  }
  return fallback
}

function toText(value: unknown) {
  return typeof value === 'string' ? value.trim() : ''
}

function clamp(value: number, min: number, max: number) {
  return Math.min(max, Math.max(min, value))
}

function roundMoney(value: number) {
  if (!Number.isFinite(value)) return 0
  return Math.round(value * 100) / 100
}

function formatNumber(value: number) {
  return new Intl.NumberFormat('zh-CN', {
    maximumFractionDigits: Math.abs(value) >= 100 ? 0 : 2,
  }).format(value)
}
