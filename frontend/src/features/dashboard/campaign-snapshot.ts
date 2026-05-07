import type { Artifact, LatestReport, ProjectState } from '@/lib/api-types'

export type MetricTone = 'good' | 'neutral' | 'watch' | 'risk'

export type CampaignMetric = {
  label: string
  value: string
  delta?: string
  tone?: MetricTone
}

export type CampaignPeriodSnapshot = {
  id: 'before' | 'during' | 'after'
  label: string
  windowLabel: string
  primary: CampaignMetric
  secondary: CampaignMetric[]
  interpretation: string
}

export type TrendPoint = {
  label: string
  value: number
  displayValue: string
  caption: string
  tone: MetricTone
}

export type DidEvaluationSnapshot = {
  verdict: string
  effect: string
  incrementalValue: string
  baselineComparison: string
  confidence: string
  significance: string
  interpretation: string
  methodNote: string
  tone: MetricTone
}

export type UpliftQuadrantId = 'persuadables' | 'sure_things' | 'lost_causes' | 'do_not_disturb'

export type UpliftQuadrantSnapshot = {
  id: UpliftQuadrantId
  label: string
  countLabel: string
  shareLabel: string
  categories: string[]
  meaning: string
  action: string
  emphasis?: boolean
  tone: MetricTone
}

export type ArtifactSummarySnapshot = {
  total: number
  charts: number
  tables: number
  reports: number
  latestTitle: string
}

export type CampaignDashboardSnapshot = {
  title: string
  decisionLabel: string
  statusLabel: string
  sourceLabel: string
  stageLabel: string
  updatedAtLabel: string
  periods: CampaignPeriodSnapshot[]
  trend: {
    metricLabel: string
    points: TrendPoint[]
  }
  did: DidEvaluationSnapshot
  quadrants: UpliftQuadrantSnapshot[]
  recommendations: string[]
  conclusions: string[]
  caveats: string[]
  artifactSummary: ArtifactSummarySnapshot
}

type LatestReportWithKpis = LatestReport & {
  kpi_summary?: {
    did_estimate?: number | string
    incremental_lift_pct?: number | string
    total_local_gap?: number | string
  }
}

type MarkdownSection = {
  heading: string
  content: string
}

type SnapshotInput = {
  state: ProjectState | null
  artifacts: Artifact[]
  report: LatestReport | null
}

const MVP_CAMPAIGN_SNAPSHOT: CampaignDashboardSnapshot = {
  title: '活动效果决策看板',
  decisionLabel: '扩大定向补贴，收缩泛化折扣',
  statusLabel: 'MVP 分析快照',
  sourceLabel: '前端兜底快照',
  stageLabel: '等待 pipeline 状态',
  updatedAtLabel: '暂无记录',
  periods: [
    {
      id: 'before',
      label: '活动前',
      windowLabel: '基线窗口',
      primary: {
        label: '日均 GMV',
        value: '18.6 万元',
        delta: '指数 100',
        tone: 'neutral',
      },
      secondary: [
        { label: '日均订单', value: '4,820', tone: 'neutral' },
        { label: '曝光点击率', value: '9.8%', tone: 'neutral' },
      ],
      interpretation: '需求走势相对稳定，可作为后续 uplift 与 DID 评估的经营基线。',
    },
    {
      id: 'during',
      label: '活动中',
      windowLabel: '活动窗口',
      primary: {
        label: '日均 GMV',
        value: '24.9 万元',
        delta: '较基线 +33.9%',
        tone: 'good',
      },
      secondary: [
        { label: '日均订单', value: '6,140', delta: '+27.4%', tone: 'good' },
        { label: '平均折扣率', value: '12.6%', tone: 'watch' },
      ],
      interpretation: '活动带来明显需求抬升，但折扣压力同步上升，需要更精细的人群和品类投放。',
    },
    {
      id: 'after',
      label: '活动后',
      windowLabel: '回落观察窗口',
      primary: {
        label: '日均 GMV',
        value: '20.7 万元',
        delta: '较基线 +11.3%',
        tone: 'good',
      },
      secondary: [
        { label: '复购用户占比', value: '68%', tone: 'good' },
        { label: '回落风险', value: '可控', tone: 'neutral' },
      ],
      interpretation: '活动结束后仍保留部分增量，说明可沉淀再营销人群，而不是只依赖单日补贴峰值。',
    },
  ],
  trend: {
    metricLabel: '日均 GMV 指数',
    points: [
      { label: '活动前', value: 100, displayValue: '100', caption: '基线', tone: 'neutral' },
      { label: '活动中', value: 134, displayValue: '134', caption: '+34%', tone: 'good' },
      { label: '活动后', value: 111, displayValue: '111', caption: '+11%', tone: 'good' },
    ],
  },
  did: {
    verdict: '存在正向增量信号',
    effect: '+7.8%',
    incrementalValue: '38.2 万元增量 GMV',
    baselineComparison: '匹配对照 +4.1%，活动组 +11.9%',
    confidence: '中高置信',
    significance: 'p = 0.043; 95% CI +1.2% to +14.4%',
    interpretation:
      '匹配 DID 结果显示，活动带来的部分增长更可能是增量，而不只是季节性或全市场需求同步变化。',
    methodNote:
      '在 panel 质量、平行趋势和供给约束复核前，应将其作为方向性因果证据使用。',
    tone: 'good',
  },
  quadrants: [
    {
      id: 'persuadables',
      label: '可被撬动人群 / 品类',
      countLabel: '18 个品类',
      shareLabel: '占活动 GMV 31%',
      categories: ['饮料', '零食', '乳品', '烘焙', '咖啡', '冰品', '速食', '夜宵', '酒水', '水果', '休闲熟食', '宠物食品', '个护', '清洁', '鲜花', '母婴', '数码配件', '调味品'],
      meaning: 'uplift 高且成本可控，是活动真正能撬动的主要增长池。',
      action: '优先给到券力度、流量位和补货保障。',
      emphasis: true,
      tone: 'good',
    },
    {
      id: 'sure_things',
      label: '自然会买人群 / 品类',
      countLabel: '12 个品类',
      shareLabel: '占活动 GMV 29%',
      categories: ['生鲜', '粮油', '家清', '纸品', '基础乳', '日用百货', '医药健康', '米面粮油', '肉禽蛋', '蔬菜', '水产', '厨具'],
      meaning: '基线需求强，但活动增量有限。收入高，不代表补贴效率高。',
      action: '保留曝光，降低折扣深度，优先保护毛利。',
      tone: 'neutral',
    },
    {
      id: 'lost_causes',
      label: '低响应人群 / 品类',
      countLabel: '9 个品类',
      shareLabel: '占活动 GMV 11%',
      categories: ['大家电', '家具', '户外装备', '高客单厨电', '礼品卡', '鲜花礼盒', '进口保健', '汽车用品', '小众宠物'],
      meaning: '基线低、响应也低，泛化促销很难形成高效增长。',
      action: '暂停一刀切投放，先诊断供给、价格或库存问题。',
      tone: 'risk',
    },
    {
      id: 'do_not_disturb',
      label: '避免打扰人群 / 品类',
      countLabel: '7 个品类',
      shareLabel: '占活动 GMV 8%',
      categories: ['刚需纸品', '常温水', '基础米面', '盐糖调味', '低价蔬菜', '基础药品', '清洁耗材'],
      meaning: '可能存在蚕食或负 uplift，额外补贴会提前透支自然需求。',
      action: '减少折扣曝光，测试非补贴型留存手段。',
      tone: 'watch',
    },
  ],
  recommendations: [
    '下一轮预算向可被撬动人群 / 品类倾斜，对自然会买人群设置补贴上限。',
    '用活动期流量沉淀再营销池，活动后用更轻的权益承接复购。',
    '低响应品类再次投放前先复核库存、价格和供给结构。',
    '放量前设置毛利护栏，因为当前增量仍伴随一定折扣压力。',
  ],
  conclusions: [
    '从组合层面看，活动存在正向增量。',
    '增长并非均匀分布，最强机会来自品类和人群的定向处理。',
    '更小但更准的活动，大概率优于照搬上一轮泛化折扣。',
  ],
  caveats: [
    '当前数值是 MVP 前端快照，若后端报告或 artifact 提供指标，会优先替换。',
    'DID 在平行趋势和匹配诊断复核前，应作为方向性证据。',
    '毛利、库存和履约能力尚未完整纳入前端快照。',
  ],
  artifactSummary: {
    total: 0,
    charts: 0,
    tables: 0,
    reports: 0,
    latestTitle: '暂无已注册产物',
  },
}

export function buildCampaignDashboardSnapshot({
  state,
  artifacts,
  report,
}: SnapshotInput): CampaignDashboardSnapshot {
  const reportContent = report?.content ?? ''
  const sections = parseMarkdownSections(reportContent)
  const kpis = report as LatestReportWithKpis | null

  const didEstimate =
    metricToText(kpis?.kpi_summary?.did_estimate) ||
    metricToText(kpis?.kpi_summary?.incremental_lift_pct) ||
    extractMetric(reportContent, [
      /did[_\s-]*(?:estimate|effect|lift)?\s*[:=]\s*([+\-]?[0-9,.]+%?)/i,
      /incremental[_\s-]*lift(?:_pct)?\s*[:=]\s*([+\-]?[0-9,.]+%?)/i,
    ])
  const incrementalValue =
    metricToText(kpis?.kpi_summary?.total_local_gap) ||
    extractMetric(reportContent, [
      /total[_\s-]*local[_\s-]*gap\s*[:=]\s*([+\-]?[0-9,.]+%?)/i,
      /incremental[_\s-]*(?:gmv|value)\s*[:=]\s*([+\-]?[0-9,.]+%?)/i,
    ])

  const recommendationItems = pickBusinessBullets(sections, ['recommendation', 'action', 'strategy', '建议', '策略', '行动'])
  const conclusionItems = pickBusinessBullets(sections, ['conclusion', 'summary', 'executive', '结论', '摘要'])
  const caveatItems = pickBusinessBullets(sections, ['caveat', 'limitation', 'assumption', 'risk', '限制', '假设', '风险'])
  const didNumericValue = parseMetricNumber(didEstimate)
  const didTone = resolveDidTone(didNumericValue)
  const didVerdict = resolveDidVerdict(didNumericValue)
  const didInterpretation = resolveDidInterpretation(didNumericValue)

  return {
    ...MVP_CAMPAIGN_SNAPSHOT,
    statusLabel: buildStatusLabel(state, report),
    sourceLabel: buildSourceLabel(artifacts, report),
    stageLabel: humanizeStage(state?.current_stage),
    updatedAtLabel: formatDateTime(state?.last_activity),
    did: {
      ...MVP_CAMPAIGN_SNAPSHOT.did,
      verdict: didVerdict,
      tone: didTone,
      confidence: didNumericValue !== null && didNumericValue < 0 ? '需重点复核' : MVP_CAMPAIGN_SNAPSHOT.did.confidence,
      effect: didEstimate ? formatMetricValue(didEstimate, true) : MVP_CAMPAIGN_SNAPSHOT.did.effect,
      incrementalValue: incrementalValue
        ? `${formatMetricValue(incrementalValue)} 增量价值`
        : MVP_CAMPAIGN_SNAPSHOT.did.incrementalValue,
      interpretation: didInterpretation,
      methodNote: report
        ? '已发现最新报告证据。用于最终决策前，请继续复核报告正文和图表产物。'
        : MVP_CAMPAIGN_SNAPSHOT.did.methodNote,
    },
    recommendations: recommendationItems.length >= 2 ? recommendationItems : MVP_CAMPAIGN_SNAPSHOT.recommendations,
    conclusions: conclusionItems.length >= 2 ? conclusionItems : MVP_CAMPAIGN_SNAPSHOT.conclusions,
    caveats: caveatItems.length > 0 ? caveatItems : buildFallbackCaveats(state, artifacts, report),
    artifactSummary: summarizeArtifacts(artifacts),
  }
}

function buildStatusLabel(state: ProjectState | null, report: LatestReport | null) {
  if (report) return '最新报告已就绪'
  if ((state?.latest_jobs ?? []).some((job) => job.status === 'running')) return '分析运行中'
  if ((state?.files_count ?? 0) > 0) return '数据已接入'
  return MVP_CAMPAIGN_SNAPSHOT.statusLabel
}

function buildSourceLabel(artifacts: Artifact[], report: LatestReport | null) {
  if (report && artifacts.length > 0) return '报告 + 已注册产物'
  if (report) return '最新报告 + MVP 快照'
  if (artifacts.length > 0) return '已注册产物 + MVP 快照'
  return MVP_CAMPAIGN_SNAPSHOT.sourceLabel
}

function buildFallbackCaveats(state: ProjectState | null, artifacts: Artifact[], report: LatestReport | null) {
  const caveats = [...MVP_CAMPAIGN_SNAPSHOT.caveats]
  if ((state?.files_count ?? 0) < 3) {
    caveats.unshift('订单、曝光和活动时间线文件可能尚未全部注册。')
  }
  if (!hasArtifact(artifacts, ['did', 'psm', 'causal'])) {
    caveats.unshift('尚未注册因果产物，DID 数值仍是 MVP 快照提示。')
  }
  if (!report) {
    caveats.unshift('暂无最新报告，建议来自前端 MVP 快照。')
  }
  return caveats.slice(0, 5)
}

function summarizeArtifacts(artifacts: Artifact[]): ArtifactSummarySnapshot {
  const reports = artifacts.filter((artifact) => isReportArtifact(artifact)).length
  const charts = artifacts.filter((artifact) => isChartArtifact(artifact)).length
  const tables = artifacts.filter((artifact) => isTableArtifact(artifact)).length
  const latest = [...artifacts].sort((a, b) => Date.parse(b.created_at) - Date.parse(a.created_at))[0]

  return {
    total: artifacts.length,
    charts,
    tables,
    reports,
    latestTitle: latest?.title ?? MVP_CAMPAIGN_SNAPSHOT.artifactSummary.latestTitle,
  }
}

function isChartArtifact(artifact: Artifact) {
  const haystack = `${artifact.type} ${artifact.title} ${artifact.path}`.toLowerCase()
  return artifact.type === 'chart' || haystack.includes('/charts/') || haystack.includes('chart')
}

function isTableArtifact(artifact: Artifact) {
  const haystack = `${artifact.type} ${artifact.title} ${artifact.path}`.toLowerCase()
  return artifact.type === 'table' || haystack.endsWith('.csv') || haystack.includes('/tables/')
}

function isReportArtifact(artifact: Artifact) {
  const haystack = `${artifact.type} ${artifact.title} ${artifact.path}`.toLowerCase()
  return artifact.type === 'report' || haystack.endsWith('.md') || haystack.includes('/reports/')
}

function hasArtifact(artifacts: Artifact[], needles: string[]) {
  return artifacts.some((artifact) => {
    const haystack = `${artifact.type} ${artifact.title} ${artifact.path}`.toLowerCase()
    return needles.some((needle) => haystack.includes(needle))
  })
}

function parseMarkdownSections(content: string): MarkdownSection[] {
  if (!content.trim()) return []
  const lines = content.split(/\r?\n/)
  const sections: MarkdownSection[] = []
  let current: MarkdownSection | null = null

  for (const line of lines) {
    const match = /^(#{1,3})\s+(.+?)\s*$/.exec(line.trim())
    if (match) {
      if (current) sections.push(current)
      current = { heading: match[2], content: '' }
      continue
    }

    if (current) {
      current.content += `${line}\n`
    }
  }

  if (current) sections.push(current)
  return sections
}

function pickBullets(sections: MarkdownSection[], keywords: string[]) {
  const section = sections.find((candidate) => {
    const heading = candidate.heading.toLowerCase()
    return keywords.some((keyword) => heading.includes(keyword))
  })

  if (!section) return []

  return section.content
    .split(/\r?\n/)
    .map((line) => line.trim())
    .filter((line) => /^[-*]\s+/.test(line) || /^\d+\.\s+/.test(line))
    .map((line) => line.replace(/^[-*]\s+/, '').replace(/^\d+\.\s+/, '').replace(/\*\*/g, '').trim())
    .filter(Boolean)
    .slice(0, 5)
}

function pickBusinessBullets(sections: MarkdownSection[], keywords: string[]) {
  return pickBullets(sections, keywords).filter(isBusinessSentence).slice(0, 5)
}

function isBusinessSentence(value: string) {
  const lower = value.toLowerCase()
  if (value.length < 12) return false
  if (/^[./\\\w-]+\.(json|csv|md|png|jpg|jpeg|svg|xlsx|parquet)$/i.test(value)) return false
  if (lower.includes('artifacts/') || lower.includes('.analysis/') || lower.includes('workspace')) return false
  if (lower.includes('path:') || lower.includes('file:') || lower.includes('artifact')) return false
  return true
}

function extractMetric(content: string, patterns: RegExp[]) {
  for (const pattern of patterns) {
    const match = content.match(pattern)
    if (match?.[1]) return match[1]
  }
  return ''
}

function metricToText(value: unknown) {
  if (typeof value === 'number' && Number.isFinite(value)) return String(value)
  if (typeof value === 'string' && value.trim()) return value.trim()
  return ''
}

function formatMetricValue(value: string, preferPercent = false) {
  const trimmed = value.trim()
  if (trimmed.endsWith('%')) return trimmed
  const numeric = Number(trimmed.replace(/,/g, ''))
  if (!Number.isFinite(numeric)) return trimmed
  if (preferPercent && Math.abs(numeric) < 1) return `${formatNumber(numeric * 100)}%`
  if (preferPercent) return `${formatNumber(numeric)}%`
  return formatNumber(numeric)
}

function parseMetricNumber(value: string) {
  if (!value.trim()) return null
  const hasPercent = value.includes('%')
  const numeric = Number(value.replace(/[%+,]/g, '').trim())
  if (!Number.isFinite(numeric)) return null
  if (!hasPercent && Math.abs(numeric) > 0 && Math.abs(numeric) < 1) return numeric * 100
  return Number.isFinite(numeric) ? numeric : null
}

function resolveDidTone(value: number | null): MetricTone {
  if (value === null) return MVP_CAMPAIGN_SNAPSHOT.did.tone
  if (value < 0) return 'risk'
  if (value < 2) return 'watch'
  return 'good'
}

function resolveDidVerdict(value: number | null) {
  if (value === null) return MVP_CAMPAIGN_SNAPSHOT.did.verdict
  if (value < 0) return 'DID 显示负向，需要复核'
  if (value < 2) return 'DID 增量信号较弱'
  return '存在正向增量信号'
}

function resolveDidInterpretation(value: number | null) {
  if (value === null) return MVP_CAMPAIGN_SNAPSHOT.did.interpretation
  if (value < 0) {
    return '当前解析到的 DID 效应为负，说明活动组相对匹配对照并未跑赢基线，需要优先检查活动窗口、匹配质量和异常品类。'
  }
  if (value < 2) {
    return '当前解析到的 DID 效应偏弱，活动可能有经营抬升，但净增量还不足以支撑扩大泛化补贴。'
  }
  return MVP_CAMPAIGN_SNAPSHOT.did.interpretation
}

function formatNumber(value: number) {
  return new Intl.NumberFormat('zh-CN', { maximumFractionDigits: 2 }).format(value)
}

function formatDateTime(value?: string) {
  if (!value) return MVP_CAMPAIGN_SNAPSHOT.updatedAtLabel
  const date = new Date(value)
  if (Number.isNaN(date.getTime())) return MVP_CAMPAIGN_SNAPSHOT.updatedAtLabel
  return new Intl.DateTimeFormat('zh-CN', {
    month: 'short',
    day: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  }).format(date)
}

function humanizeStage(value?: string) {
  if (!value) return MVP_CAMPAIGN_SNAPSHOT.stageLabel
  const labels: Record<string, string> = {
    report_ready: '报告已就绪',
    diagnostics_ready: '诊断已就绪',
    panel_ready: 'Panel 已就绪',
    data_loaded: '数据已接入',
    created: '已创建',
    unknown: '未知',
  }
  if (labels[value]) return labels[value]
  return value
    .replace(/[_-]+/g, ' ')
    .replace(/\s+/g, ' ')
    .trim()
    .replace(/\b\w/g, (letter) => letter.toUpperCase())
}
