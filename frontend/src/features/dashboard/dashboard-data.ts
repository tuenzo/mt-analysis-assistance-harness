import type { DashboardSummary } from '@/types/dashboard'
import type { Artifact, LatestReport, ProjectState } from '@/lib/api-types'

export function buildDashboardSummary(source: {
  state: ProjectState | null
  artifacts: Artifact[]
  report: LatestReport | null
}): DashboardSummary {
  void source

  return {
    conclusion: '建议优先加码 drinks，曝光仍是增量驱动，折扣更适合 payday 精准刺激。',
    kpis: [
      {
        key: 'gmv_increment',
        label: 'GMV 净增量',
        value: '1,290',
        unit: '万元',
        subText: '较基线 +61.2%',
        trendText: '+61.2%',
        trendDirection: 'up',
        color: 'green',
        sparkline: [42, 39, 47, 58, 64, 60, 66, 61, 69, 74],
      },
      {
        key: 'exposure_contribution',
        label: '曝光贡献',
        value: '+980',
        unit: '万元',
        subText: '占净增量 75.9%',
        trendText: '75.9%',
        trendDirection: 'up',
        color: 'blue',
        sparkline: [22, 31, 48, 45, 42, 58, 61, 57, 66, 72],
      },
      {
        key: 'discount_contribution',
        label: '折扣贡献',
        value: '+180',
        unit: '万元',
        subText: '占净增量 14.0%',
        trendText: '14.0%',
        trendDirection: 'flat',
        color: 'orange',
        sparkline: [18, 16, 22, 19, 24, 21, 30, 22, 27, 38],
      },
      {
        key: 'boost_categories',
        label: '建议优先加码品类数',
        value: '4',
        unit: '个',
        subText: '较上期 +1 个',
        trendText: '+1',
        trendDirection: 'up',
        color: 'purple',
        sparkline: [2, 3, 3, 2, 3, 3, 4, 3, 4, 5],
      },
    ],
    pareto: [
      { category: '饮料', gmv: 2150, cumulativeRatio: 38 },
      { category: '零食', gmv: 1180, cumulativeRatio: 58 },
      { category: '生鲜', gmv: 650, cumulativeRatio: 70 },
      { category: '母婴', gmv: 360, cumulativeRatio: 78 },
      { category: '家清', gmv: 260, cumulativeRatio: 85 },
      { category: '个护', gmv: 180, cumulativeRatio: 90 },
      { category: '粮油', gmv: 120, cumulativeRatio: 95 },
      { category: '酒水', gmv: 85, cumulativeRatio: 98 },
      { category: '其他', gmv: 55, cumulativeRatio: 100 },
    ],
    localGap: [
      { name: '基线GMV', value: 800, type: 'baseline' },
      { name: '曝光贡献', value: 300, type: 'positive' },
      { name: '折扣贡献', value: 180, type: 'positive' },
      { name: '发薪日贡献', value: 120, type: 'positive' },
      { name: '交互/渠道', value: -110, type: 'negative' },
      { name: '实际GMV', value: 1290, type: 'total' },
    ],
    trend: [
      { date: '05-06', gmv: 280, exposure: 120, discount: 40 },
      { date: '05-11', gmv: 520, exposure: 260, discount: 85 },
      { date: '05-16', gmv: 890, exposure: 520, discount: 140, isActivityDay: true, isPayday: true },
      { date: '05-21', gmv: 500, exposure: 330, discount: 88, isActivityDay: true },
      { date: '05-26', gmv: 980, exposure: 610, discount: 155, isActivityDay: true, isPayday: true },
      { date: '05-31', gmv: 560, exposure: 350, discount: 95 },
      { date: '06-04', gmv: 760, exposure: 420, discount: 110 },
    ],
    quadrants: [
      { category: '饮料', x: 78, y: 70, size: 42, group: 'boost', color: '#60a5fa', suggestedAction: '优先加码曝光与排面' },
      { category: '零食', x: 62, y: 62, size: 30, group: 'boost', color: '#a3e635', suggestedAction: '维持曝光，加一点折扣' },
      { category: '个护', x: 88, y: 54, size: 24, group: 'maintain', color: '#bfdbfe', suggestedAction: '保护基本盘' },
      { category: '母婴', x: 22, y: 64, size: 24, group: 'maintain', color: '#bfdbfe', suggestedAction: '小规模试验' },
      { category: '酒水', x: 34, y: 68, size: 22, group: 'avoid', color: '#ddd6fe', suggestedAction: '减少泛触达' },
      { category: '生鲜', x: 56, y: 34, size: 26, group: 'reduce', color: '#fdba74', suggestedAction: '控制折扣投入' },
      { category: '家清', x: 74, y: 26, size: 20, group: 'reduce', color: '#fde68a', suggestedAction: '观察渠道扰动' },
      { category: '粮油', x: 18, y: 22, size: 18, group: 'avoid', color: '#fda4af', suggestedAction: '减少打扰' },
      { category: '乳品', x: 66, y: 20, size: 20, group: 'reduce', color: '#bbf7d0', suggestedAction: '待评估观察' },
    ],
    recommendations: [
      {
        key: 'boost',
        title: '优先加码',
        description: '依据分解结果和预算，建议优先高曝光与排面',
        count: 4,
        countLabel: '4 个品类',
        categories: ['饮料', '零食', '乳品', '个护'],
        color: 'green',
      },
      {
        key: 'control_discount',
        title: '控制折扣',
        description: '折扣贡献有限，建议精准投放',
        count: 3,
        countLabel: '3 个品类',
        categories: ['酒水', '零食', '个护'],
        color: 'orange',
      },
      {
        key: 'watch',
        title: '重点观察',
        description: '表现中等，建议持续观察验证',
        count: 2,
        countLabel: '2 个品类',
        categories: ['母婴', '乳品'],
        color: 'blue',
      },
      {
        key: 'avoid',
        title: '避免打扰',
        description: '效果较弱且干扰，建议减少触达',
        count: 2,
        countLabel: '2 个品类',
        categories: ['粮油', '家清'],
        color: 'purple',
      },
    ],
  }
}
