import type { DashboardSummary, TrendDatum } from '@/types/dashboard'

export const KEEMART_PROJECT_ID = 'keemart-saudi-promo-review'
export const KEEMART_PROJECT_LEGACY_ID = 'keemart-demo'
export const KEEMART_PROJECT_NAME = 'Keemart 沙特月末促销复盘'

export function isKeemartPromoProject(projectId?: string | null) {
  return projectId === KEEMART_PROJECT_ID || projectId === KEEMART_PROJECT_LEGACY_ID
}

export const keemartReportFacts = {
  period: '2025-09-01 至 2025-11-30',
  timeRange: ['2025-09-01', '2025-11-30'] as [string, string],
  activityWindows: 4,
  activityDays: 33,
  categoryCount: 336,
  paidUsers: 13201,
  avgActivePurchaseDaysPerUser: 3.96,
  avgDailyActiveBuyers: 574,
  top3Share: '16.41%',
  top10Share: '31.21%',
  actualGmv: 1334767.68,
  counterfactualGmv: 987564.34,
  incrementalGmv: 347203.34,
  liftRate: '35.16%',
  orderContribution: 204588.4,
  orderContributionShare: '58.92%',
  aovContribution: 142614.94,
  aovContributionShare: '41.08%',
  exposureDidAfter05: '60.8%',
  exposureDidAfter610: '43.7%',
  exposureTailGain: 27.365,
  discountTailGain: 4.345,
  topExposurePeakGmv: 4271.412,
  topExposureTailGain: 795.734,
  longTailExposureTailGain: -2.273,
  paydayDiscountTailGain: 1.863,
  nonPaydayDiscountTailGain: -2.304,
}

export type DemoToolCall = {
  action: string
  title: string
  summary: string
  evidence: string[]
  status: 'success' | 'running'
}

export const keemartDemoToolCalls: DemoToolCall[] = [
  {
    action: 'data.validate',
    title: '数据校验与口径识别',
    summary: '识别订单表、曝光表、活动表，并确认样本期、活动窗口和发薪周期口径。',
    evidence: [
      '观测区间：2025-09-01 至 2025-11-30',
      '活动日历覆盖 4 个活动窗口，样本内活动日 33 天',
      '品类层 336 个品类，用户层 13,201 名支付用户',
    ],
    status: 'success',
  },
  {
    action: 'panel.build_category_day',
    title: '构建品类 × 日期分析底座',
    summary: '补齐并聚合为品类日面板，保留活动、曝光、折扣和发薪窗口特征。',
    evidence: [
      'GMV Top3 品类贡献 16.41%，Top10 贡献 31.21%',
      '活动期 GMV、曝光、折扣率均高于非活动期',
      '月末自然消费高峰与活动窗口高度重叠',
    ],
    status: 'success',
  },
  {
    action: 'analysis.run_psm_did',
    title: 'PSM-DID 评估活动是否有效',
    summary: '控制活动前可观测差异后，验证资源加码品类是否仍显著优于匹配对照组。',
    evidence: [
      '曝光组活动后 0-5 天相对差异 60.8%',
      '曝光组活动后 6-10 天仍保持 43.7%',
      '安慰剂检验未显示虚构窗口显著差异',
    ],
    status: 'success',
  },
  {
    action: 'analysis.run_increment_decomposition',
    title: 'GMV 增量拆解',
    summary: '基于反事实基线拆解活动期 GMV 增量，识别订单量与客单价贡献。',
    evidence: [
      '实际 GMV 1,334,767.68，反事实 GMV 987,564.34',
      '净增量 347,203.34，整体提升 35.16%',
      '订单量贡献 58.92%，客单价贡献 41.08%',
    ],
    status: 'success',
  },
  {
    action: 'analysis.run_gps_uplift',
    title: 'GPS/Uplift 资源排序',
    summary: '估计连续资源投入强度的边际收益，并形成投放优先级。',
    evidence: [
      '曝光尾部边际收益 27.365，折扣尾部边际收益 4.345',
      '曝光适合覆盖前 60% 品类捕获大部分增量',
      '折扣增量集中在前 20%-30% 高敏感样本',
    ],
    status: 'success',
  },
  {
    action: 'strategy.generate',
    title: '生成下一轮投放策略',
    summary: '把模型结果转成活动前、活动中、活动后的经营动作。',
    evidence: [
      '曝光作为扩大交易规模的主引擎',
      '折扣作为发薪窗口和高敏感样本的转化微调器',
      '活动后用 Uplift 更新重点池、优惠池和资源优先级',
    ],
    status: 'success',
  },
]

export type DemoAgentEvent =
  | {
      type: 'assistant'
      title: string
      content: string
    }
  | {
      type: 'tool'
      action: string
      title: string
      summary: string
      evidence: string[]
    }
  | {
      type: 'artifact'
      title: string
      content: string
    }

export type DemoAgentPrompt = {
  id: string
  label: string
  prompt: string
  goal: string
  events: DemoAgentEvent[]
}

export const keemartAgentPromptFlows: DemoAgentPrompt[] = [
  {
    id: 'effect',
    label: '活动是否有效',
    prompt: '请评估本轮促销活动是否真正有效，注意区分月末发薪自然高峰和促销带来的真实增量。',
    goal: '先建立可信识别：活动期 GMV 抬升不等于真实增量，需要控制发薪周期和品类差异。',
    events: [
      {
        type: 'assistant',
        title: '任务理解',
        content:
          '我会先确认数据口径，再构建品类乘日期面板，并用 PSM-DID 判断资源加码品类是否在控制发薪周期后仍显著优于匹配对照组。',
      },
      {
        type: 'tool',
        action: 'data.validate',
        title: '校验订单表、曝光表和活动日历',
        summary: '数据覆盖 2025-09-01 至 2025-11-30，活动日历包含 4 个窗口，样本内活动日 33 天。',
        evidence: [
          '品类层：336 个品类的平衡面板',
          '用户层：13,201 名支付用户',
          '月末发薪窗口与活动窗口高度重叠',
        ],
      },
      {
        type: 'tool',
        action: 'panel.build_category_day',
        title: '构建品类 × 日期面板',
        summary: '将订单、曝光、折扣和活动日历统一到品类日粒度，并保留发薪距离变量。',
        evidence: [
          'GMV Top3 品类贡献 16.41%',
          'GMV Top10 品类贡献 31.21%',
          '活动期平均 GMV、曝光、折扣率均高于非活动期',
        ],
      },
      {
        type: 'tool',
        action: 'analysis.run_psm_did',
        title: '运行 PSM-DID 与安慰剂检验',
        summary: '基于活动前历史特征匹配处理组与对照组，评估高曝光/高折扣资源倾斜的方向性效果。',
        evidence: [
          `曝光组活动后 0-5 天相对差异 ${keemartReportFacts.exposureDidAfter05}`,
          `曝光组活动后 6-10 天仍保持 ${keemartReportFacts.exposureDidAfter610}`,
          '虚构干预窗口未出现显著差异，真实效应在活动点后爆发',
        ],
      },
      {
        type: 'assistant',
        title: '回答：活动是否有效',
        content:
          '结论是有效，但前提是不能只看活动期 GMV 抬升。报告中的 PSM-DID 表明，在控制活动前差异和发薪周期后，高曝光与高折扣加码品类在活动后仍表现出更强增长，尤其曝光组活动后 0-5 天相对差异达到 60.8%。这说明本轮促销不是单纯吃到月末自然高峰，而是产生了可归因的销售抬升。',
      },
    ],
  },
  {
    id: 'increment',
    label: '增量来自哪里',
    prompt: '请继续分解 GMV 增量来源，说明订单量和客单价分别贡献多少。',
    goal: '把“有效”进一步拆成可经营的增长来源，说明增长质量。',
    events: [
      {
        type: 'assistant',
        title: '分析计划',
        content:
          '我会使用非活动期样本训练反事实基线，再把活动期实际 GMV 与无促销情形做比较，并按 GMV = Order × AOV 拆分订单量和客单价贡献。',
      },
      {
        type: 'tool',
        action: 'analysis.run_increment_decomposition',
        title: '构造反事实基线并拆解 GMV',
        summary: '基于 Ridge 反事实基线与 LMDI 分解，识别活动期净增量来自订单量还是客单价。',
        evidence: [
          `实际 GMV：${keemartReportFacts.actualGmv.toLocaleString('en-US')}`,
          `反事实 GMV：${keemartReportFacts.counterfactualGmv.toLocaleString('en-US')}`,
          `净增量：${keemartReportFacts.incrementalGmv.toLocaleString('en-US')}，提升 ${keemartReportFacts.liftRate}`,
        ],
      },
      {
        type: 'artifact',
        title: '生成增量拆解卡片',
        content: `订单量贡献 ${keemartReportFacts.orderContribution.toLocaleString('en-US')}，占 ${keemartReportFacts.orderContributionShare}；客单价贡献 ${keemartReportFacts.aovContribution.toLocaleString('en-US')}，占 ${keemartReportFacts.aovContributionShare}。`,
      },
      {
        type: 'assistant',
        title: '回答：增量来自哪里',
        content:
          '活动期实际 GMV 为 1,334,767.68，反事实基线为 987,564.34，因此净增量约 347,203.34，整体提升 35.16%。增量主要由订单量拉动，订单量贡献 58.92%，客单价贡献 41.08%。这说明活动确实扩大了交易规模，但后期增长更多依赖订单量延续，成交质量提升不足，后续要关注资源继续加码后的边际收益。',
      },
    ],
  },
  {
    id: 'strategy',
    label: '资源应投给谁',
    prompt: '基于这些结果，下一轮资源应该怎么投？请区分曝光、折扣、发薪窗口和重点品类。',
    goal: '把模型结论转成下一轮活动前、中、后的投放动作。',
    events: [
      {
        type: 'assistant',
        title: '策略生成思路',
        content:
          '我会结合机制回归、GPS 剂量反应和 Uplift 排序，把曝光和折扣拆成不同经营角色，再给出品类和时间窗口建议。',
      },
      {
        type: 'tool',
        action: 'analysis.run_gps_uplift',
        title: '评估连续资源投入强度',
        summary: '估计曝光和折扣在不同剂量下的边际收益，并比较 Top、Mid、LongTail 与 Payday/NonPayday 的异质性。',
        evidence: [
          `曝光尾部边际收益 ${keemartReportFacts.exposureTailGain}`,
          `折扣尾部边际收益 ${keemartReportFacts.discountTailGain}`,
          `LongTail 高曝光尾部收益 ${keemartReportFacts.longTailExposureTailGain}，NonPayday 折扣尾部收益 ${keemartReportFacts.nonPaydayDiscountTailGain}`,
        ],
      },
      {
        type: 'tool',
        action: 'strategy.generate',
        title: '生成 Uplift 四象限策略',
        summary: '按照 Persuadables、Sure Things、Lost Causes、Do Not Disturb 组织下一轮投放优先级。',
        evidence: [
          '曝光 Persuadables：一次性杯子、天然矿泉水、奶油酱、研磨咖啡',
          '折扣 Persuadables：乳液/面霜、橙味汽水、牙膏/牙粉、香皂',
          '折扣增量集中在前 20%-30% 高敏感样本，不适合大范围平均加深',
        ],
      },
      {
        type: 'artifact',
        title: '结果看板已更新',
        content: '已把总体效果、增量拆解、资源响应和策略建议同步到结果看板，可切换到 Dashboard 查看。',
      },
      {
        type: 'assistant',
        title: '回答：下一轮怎么投',
        content:
          '建议把曝光作为扩大交易规模的主引擎，优先保障头部和高响应品类；把折扣作为提升转化的微调器，只投给少数价格敏感品类和关键发薪窗口。具体节奏上，发薪日后 2-3 天集中释放曝光和定向折扣，非发薪期严格控盘。品类上，曝光优先关注一次性杯子、天然矿泉水、奶油酱、研磨咖啡；折扣优先关注乳液/面霜、橙味汽水、牙膏/牙粉、香皂，同时减少长尾和低响应品类的粗放投入。',
      },
    ],
  },
  {
    id: 'explain-exposure',
    label: '解释曝光贡献',
    prompt: '为什么这里把曝光贡献作为主引擎？请结合看板里的净增量、LocalGap 和 Uplift 结果解释。',
    goal: '把结果看板中的增量分解和策略分层解释成业务可理解的资源逻辑。',
    events: [
      {
        type: 'assistant',
        title: '追问理解',
        content:
          '我会把看板中的 GMV 净增量、LocalGap 分解和 Uplift 四象限放在一起解释，判断曝光为什么适合作为主资源，而不是只看单个指标。',
      },
      {
        type: 'tool',
        action: 'analysis.explain_dashboard_metric',
        title: '读取看板证据链',
        summary: '汇总顶部 KPI、LocalGap 增量分解、GPS/Uplift 排序与策略卡片，形成可解释证据。',
        evidence: [
          '净增量为正，且增长主要来自订单量扩张',
          'LocalGap 分解显示曝光贡献高于折扣贡献',
          'Uplift 结果显示曝光 Persuadables 可形成下一轮优先加码池',
        ],
      },
      {
        type: 'assistant',
        title: '回答：为什么曝光是主引擎',
        content:
          '曝光被定义为主引擎，是因为它对应的是交易规模扩张：看板中的净增量为正，订单量贡献高于客单价贡献，LocalGap 也显示曝光贡献是主要增量来源。折扣更像转化微调器，它对少数价格敏感品类有效，但大范围加深会带来边际收益衰减。因此下一轮应先保障高响应品类的曝光触达，再把折扣集中到发薪窗口和高敏感样本。',
      },
    ],
  },
]

export type KeemartMemoryCandidateStatus = 'pending' | 'approved' | 'rejected'

export type KeemartMemoryCandidate = {
  id: string
  title: string
  scope: string
  source: string
  confidence: string
  status: KeemartMemoryCandidateStatus
  content: string
  tags: string[]
}

export const keemartMemoryCandidates: KeemartMemoryCandidate[] = [
  {
    id: 'mem-effect-identification',
    title: '活动效果识别口径',
    scope: 'project',
    source: 'PSM-DID 评估、安慰剂检验',
    confidence: '高',
    status: 'approved',
    tags: ['活动复盘', '因果识别', '发薪周期'],
    content:
      '本项目在评估月末促销时，不能直接把活动期 GMV 抬升等同于活动效果。需要先控制月末发薪自然高峰、活动前品类差异和历史消费基础，再用 PSM-DID 判断是否存在可归因增量。本轮复盘显示，高曝光和高折扣加码品类在控制自然周期后仍存在正向抬升。',
  },
  {
    id: 'mem-resource-role',
    title: '曝光与折扣的资源角色',
    scope: 'project',
    source: 'LocalGap、GPS/Uplift 结果',
    confidence: '高',
    status: 'pending',
    tags: ['资源配置', '曝光', '折扣'],
    content:
      '曝光更适合作为扩大交易规模的主引擎，优先用于高响应品类和活动关键窗口；折扣更适合作为转化微调器，应集中到少数价格敏感品类和发薪窗口。非发薪期继续加深折扣存在边际收益衰减风险。',
  },
  {
    id: 'mem-category-policy',
    title: '下一轮品类分层策略',
    scope: 'project',
    source: '连续 Uplift 四象限',
    confidence: '中高',
    status: 'pending',
    tags: ['品类分层', '投放策略', '复用规则'],
    content:
      '下一轮活动建议沿用四类动作组织资源：优先加码品类用于扩大曝光触达，稳定维持品类保持基础权益，控制折扣品类降低优惠强度，避免打扰品类减少额外触达。代表品类需在新一轮数据接入后重新刷新。',
  },
  {
    id: 'mem-risk-boundary',
    title: '边际收益风险边界',
    scope: 'project',
    source: 'GPS 剂量响应',
    confidence: '中',
    status: 'pending',
    tags: ['风险提示', '边际收益', '活动中监控'],
    content:
      '活动中需要持续监控曝光、折扣与 GMV 的联动变化。当长尾品类高曝光尾部收益转负，或非发薪期折扣尾部收益转负时，应触发资源控盘提醒，避免把预算继续投向低响应样本。',
  },
]

export const keemartStoredProjectMemory = `## Keemart 月末促销项目记忆

- 评估促销效果时，优先控制发薪周期、品类差异和活动前历史基础，避免把自然高峰误判为活动增量。
- 本轮复盘中，曝光更接近扩量主引擎，折扣更接近关键窗口内的转化微调器。
- 下一轮活动应优先复核高响应品类池，并把折扣集中到发薪窗口和价格敏感样本。
- 活动后复盘需要持续更新四象限策略池，避免沿用上一轮代表品类而不重新校验。`

export const keemartMemoryReuseRules = [
  '新活动立项时，Agent 优先读取项目记忆中的效果识别口径。',
  '字段映射和面板构建完成后，自动核验发薪窗口与活动窗口是否重叠。',
  '策略生成时复用曝光主引擎、折扣微调器的资源角色，但代表品类随新数据刷新。',
  '同步到用户级记忆前必须经过显式确认，原始订单明细不进入长期记忆。',
]

const trendBase: Array<Omit<TrendDatum, 'gmv'> & { net: number }> = [
  { date: '09-08', baselineGmv: 72000, net: 12000, isActivityDay: false, isPayday: false, period: 'pre' },
  { date: '09-27', baselineGmv: 85000, net: 25000, isActivityDay: true, isPayday: true, period: 'during' },
  { date: '09-29', baselineGmv: 103000, net: 44000, isActivityDay: true, isPayday: true, period: 'during' },
  { date: '10-08', baselineGmv: 88000, net: 18000, isActivityDay: false, isPayday: false, period: 'post' },
  { date: '10-27', baselineGmv: 110000, net: 52000, isActivityDay: true, isPayday: true, period: 'during' },
  { date: '10-29', baselineGmv: 124000, net: 62000, isActivityDay: true, isPayday: true, period: 'during' },
  { date: '11-08', baselineGmv: 94000, net: 22000, isActivityDay: false, isPayday: false, period: 'post' },
  { date: '11-27', baselineGmv: 128000, net: 50000, isActivityDay: true, isPayday: true, period: 'during' },
  { date: '11-29', baselineGmv: 142000, net: 58000, isActivityDay: true, isPayday: true, period: 'during' },
  { date: '11-30', baselineGmv: 41564.34, net: 4203.34, isActivityDay: false, isPayday: true, period: 'post' },
]

const trend: TrendDatum[] = trendBase.map((item) => ({
  date: item.date,
  gmv: Number((item.baselineGmv + item.net).toFixed(2)),
  baselineGmv: item.baselineGmv,
  exposure: Number((item.net * (keemartReportFacts.orderContribution / keemartReportFacts.incrementalGmv)).toFixed(2)),
  discount: Number((item.net * (keemartReportFacts.aovContribution / keemartReportFacts.incrementalGmv)).toFixed(2)),
  isActivityDay: item.isActivityDay,
  isPayday: item.isPayday,
  period: item.period,
}))

export const keemartDashboardSummary: DashboardSummary = {
  conclusion: '活动存在可归因净增量；曝光是扩量主引擎，折扣应收束到发薪窗口与高敏感样本。',
  kpis: [
    {
      key: 'gmv_increment',
      label: 'GMV 净增量',
      value: '34.72',
      unit: '万元',
      subText: '较反事实基线 +35.16%',
      trendText: '+35.16%',
      trendDirection: 'up',
      color: 'green',
      chartType: 'line',
      signed: true,
      series: trend.map((item) => ({
        label: item.date,
        value: Number((item.gmv - item.baselineGmv).toFixed(2)),
      })),
    },
    {
      key: 'exposure_contribution',
      label: '订单量贡献',
      value: '+20.46',
      unit: '万元',
      subText: '占 GMV 增量 58.92%',
      trendText: '58.92%',
      trendDirection: 'up',
      color: 'blue',
      chartType: 'bar',
      signed: false,
      series: trend.map((item) => ({
        label: item.date,
        value: Math.round((item.gmv - item.baselineGmv) * 0.5892),
      })),
    },
    {
      key: 'discount_contribution',
      label: '客单价贡献',
      value: '+14.26',
      unit: '万元',
      subText: '占 GMV 增量 41.08%',
      trendText: '41.08%',
      trendDirection: 'up',
      color: 'orange',
      chartType: 'line',
      signed: true,
      series: trend.map((item) => ({
        label: item.date,
        value: Math.round((item.gmv - item.baselineGmv) * 0.4108),
      })),
    },
    {
      key: 'boost_categories',
      label: '折扣优先品类',
      value: '6',
      unit: '个',
      subText: 'Persuadables 高敏感样本',
      trendText: '6',
      trendDirection: 'flat',
      color: 'purple',
      chartType: 'line',
      signed: false,
      series: [
        { label: '09', value: 5 },
        { label: '10', value: 6 },
        { label: '11', value: 6 },
      ],
    },
  ],
  pareto: [
    { category: '一段婴儿奶粉', gmv: 80000, cumulativeRatio: 6 },
    { category: '可乐汽水', gmv: 70000, cumulativeRatio: 11 },
    { category: '夹心巧克力', gmv: 69080, cumulativeRatio: 16 },
    { category: '方便面', gmv: 36000, cumulativeRatio: 19 },
    { category: '洗衣液', gmv: 34000, cumulativeRatio: 22 },
    { category: '天然矿泉水', gmv: 31000, cumulativeRatio: 24 },
    { category: '乳液/面霜', gmv: 29000, cumulativeRatio: 26 },
    { category: '牙膏/牙粉', gmv: 26000, cumulativeRatio: 28 },
    { category: '一次性杯子', gmv: 22000, cumulativeRatio: 30 },
    { category: '研磨咖啡', gmv: 19100, cumulativeRatio: 31 },
  ],
  localGap: [
    { name: '反事实GMV', value: 987564.34, type: 'baseline' },
    { name: '订单量贡献', value: 204588.4, type: 'positive' },
    { name: '客单价贡献', value: 142614.94, type: 'positive' },
    { name: '残差校准', value: 0, type: 'positive' },
    { name: '实际GMV', value: 1334767.68, type: 'total' },
  ],
  trend,
  quadrants: [
    {
      category: '天然矿泉水',
      resourceType: '曝光',
      quadrant: 'Persuadables',
      contribution: 6.8,
      x: 36,
      y: 73,
      size: 6.8,
      group: 'boost',
      color: '#22c55e',
      suggestedAction: '曝光响应高，建议优先扩大触达',
    },
    {
      category: '一次性杯子',
      resourceType: '曝光',
      quadrant: 'Persuadables',
      contribution: 5.9,
      x: 27,
      y: 65,
      size: 5.9,
      group: 'boost',
      color: '#16a34a',
      suggestedAction: '曝光带来明显净增，适合加码触达',
    },
    {
      category: '乳液/面霜',
      resourceType: '折扣',
      quadrant: 'Persuadables',
      contribution: 4.7,
      x: 43,
      y: 61,
      size: 4.7,
      group: 'boost',
      color: '#10b981',
      suggestedAction: '折扣高敏感，建议精准发券',
    },
    {
      category: '研磨咖啡',
      resourceType: '曝光',
      quadrant: 'Persuadables',
      contribution: 4.2,
      x: 31,
      y: 78,
      size: 4.2,
      group: 'boost',
      color: '#059669',
      suggestedAction: '曝光后增量弹性较好，可进入优先池',
    },
    {
      category: '一段婴儿奶粉',
      resourceType: '曝光',
      quadrant: 'Sure Things',
      contribution: 8.6,
      x: 70,
      y: 73,
      size: 8.6,
      group: 'watch',
      color: '#3b82f6',
      suggestedAction: '自然转化强，维持基础曝光即可',
    },
    {
      category: '可乐汽水',
      resourceType: '曝光',
      quadrant: 'Sure Things',
      contribution: 7.4,
      x: 80,
      y: 65,
      size: 7.4,
      group: 'watch',
      color: '#2563eb',
      suggestedAction: '稳定贡献品类，保持常规权益',
    },
    {
      category: '夹心巧克力',
      resourceType: '折扣',
      quadrant: 'Sure Things',
      contribution: 6.5,
      x: 66,
      y: 61,
      size: 6.5,
      group: 'watch',
      color: '#1d4ed8',
      suggestedAction: '基线表现好，折扣维持不加深',
    },
    {
      category: '洗衣液',
      resourceType: '折扣',
      quadrant: 'Sure Things',
      contribution: 5.6,
      x: 83,
      y: 76,
      size: 5.6,
      group: 'watch',
      color: '#3b82f6',
      suggestedAction: '权益维护即可，避免额外折扣',
    },
    {
      category: '一次性手套',
      resourceType: '折扣',
      quadrant: 'Lost Causes',
      contribution: 2.2,
      x: 26,
      y: 36,
      size: 2.2,
      group: 'control_discount',
      color: '#f59e0b',
      suggestedAction: '折扣响应弱，建议收缩优惠',
    },
    {
      category: '保鲜膜/套',
      resourceType: '折扣',
      quadrant: 'Lost Causes',
      contribution: 1.9,
      x: 38,
      y: 43,
      size: 1.9,
      group: 'control_discount',
      color: '#f97316',
      suggestedAction: '非必要折扣品类，控制发券强度',
    },
    {
      category: '发膜',
      resourceType: '折扣',
      quadrant: 'Lost Causes',
      contribution: 1.6,
      x: 30,
      y: 28,
      size: 1.6,
      group: 'control_discount',
      color: '#ea580c',
      suggestedAction: '折扣效率偏低，建议降档观察',
    },
    {
      category: '拉拉裤',
      resourceType: '折扣',
      quadrant: 'Lost Causes',
      contribution: 1.3,
      x: 43,
      y: 32,
      size: 1.3,
      group: 'control_discount',
      color: '#c2410c',
      suggestedAction: '边际折扣回报不足，减少投入',
    },
    {
      category: '黑巧克力',
      resourceType: '曝光',
      quadrant: 'Do Not Disturb',
      contribution: 1.5,
      x: 72,
      y: 41,
      size: 1.5,
      group: 'avoid',
      color: '#8b5cf6',
      suggestedAction: '自然购买强但资源响应弱，避免过度触达',
    },
    {
      category: '冰杯',
      resourceType: '曝光',
      quadrant: 'Do Not Disturb',
      contribution: 1.2,
      x: 83,
      y: 34,
      size: 1.2,
      group: 'avoid',
      color: '#a855f7',
      suggestedAction: '触达增量有限，控制干扰',
    },
    {
      category: '方便汤',
      resourceType: '曝光',
      quadrant: 'Do Not Disturb',
      contribution: 1,
      x: 66,
      y: 29,
      size: 1,
      group: 'avoid',
      color: '#9333ea',
      suggestedAction: '不宜加码曝光，保持低频触达',
    },
    {
      category: '其他冰淇淋',
      resourceType: '曝光',
      quadrant: 'Do Not Disturb',
      contribution: 0.9,
      x: 82,
      y: 44,
      size: 0.9,
      group: 'avoid',
      color: '#7c3aed',
      suggestedAction: '存在过度触达风险，避免追加资源',
    },
  ],
  recommendations: [
    {
      key: 'boost',
      title: '优先加码',
      description: '曝光优先给高响应品类，折扣只给少量高敏感品类',
      count: 6,
      countLabel: '6 个重点品类',
      categories: ['一次性杯子', '天然矿泉水', '奶油酱', '研磨咖啡', '乳液/面霜', '牙膏/牙粉'],
      color: 'green',
    },
    {
      key: 'control_discount',
      title: '控制折扣',
      description: '折扣不做粗放扩张，非发薪期严格控盘',
      count: 4,
      countLabel: '4 类风险品类',
      categories: ['一次性手套', '保鲜膜/套', '发膜', '拉拉裤'],
      color: 'orange',
    },
    {
      key: 'watch',
      title: '稳定维持',
      description: '高基线、高稳定品类保持曝光，少量权益维护转化',
      count: 4,
      countLabel: '4 个代表品类',
      categories: ['一段婴儿奶粉', '可乐汽水', '夹心巧克力', '洗衣液'],
      color: 'blue',
    },
    {
      key: 'avoid',
      title: '避免打扰',
      description: '边际收益低或存在回落风险，减少过度触达',
      count: 4,
      countLabel: '4 个代表品类',
      categories: ['其他冰淇淋', '冰杯', '方便汤', '黑巧克力'],
      color: 'purple',
    },
  ],
}
