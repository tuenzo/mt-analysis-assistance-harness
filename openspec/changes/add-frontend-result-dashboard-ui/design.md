## Overview

Result Dashboard 展示分析结果的核心图表和数据。数据来源是 ArtifactService 中注册的 artifact（图表文件）和 latest_result.json。

## 页面布局

```
┌─────────────────────────────────────────────────────────────┐
│  Result Dashboard                        [Export] [Refresh] │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  ┌───────────┐ ┌───────────┐ ┌───────────┐ ┌───────────┐    │
│  │ GMV 变化   │ │ LocalGap  │ │ Persuade  │ │ GPS R²   │    │
│  │ +23.5%    │ │ +¥1.2M   │ │ 15.3%    │ │ 0.87     │    │
│  └───────────┘ └───────────┘ └───────────┘ └───────────┘    │
│                                                             │
│  ┌─────────────────────────────────────────────────────┐    │
│  │ GMV Trend                                             │    │
│  │ [折线图: activity vs non-activity]                    │    │
│  └─────────────────────────────────────────────────────┘    │
│                                                             │
│  ┌────────────────────────┐ ┌────────────────────────────┐  │
│  │ LocalGap 瀑布图         │ │ GPS Dose Response          │  │
│  │ baseline → exposure    │ │ [剂量响应曲线]             │  │
│  │ → discount → payday    │ │                            │  │
│  └────────────────────────┘ └────────────────────────────┘  │
│                                                             │
│  ┌─────────────────────────────────────────────────────┐    │
│  │ Strategy Matrix                                       │    │
│  │        │ High Payoff │ Medium Payoff │ Low Payoff   │    │
│  │ High % │  Persuadable│  Sure Thing  │  Dormant     │    │
│  │ Medium%│  Switch     │  Habitual    │  Dormant     │    │
│  │ Low %  │  Lost Cause │  Lost Cause  │  No Touch    │    │
│  └─────────────────────────────────────────────────────┘    │
│                                                             │
│  ┌─────────────────────────────────────────────────────┐    │
│  │ Uplift Ranking Table                                  │    │
│  │ Category    │ GPS Uplift │ Persuade% │ Recommendation │  │
│  │ 生鲜       │ +18.2%    │ 22.1%     │ 重点投入      │   │
│  │ 母婴       │ +12.5%    │ 15.3%     │ 适度投入      │   │
│  └─────────────────────────────────────────────────────┘    │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

## 组件设计

### ResultSummary

```tsx
interface SummaryMetrics {
  gmvChange: string        // "+23.5%"
  localgapTotal: string    // "+¥1.2M"
  persuadablesPct: string  // "15.3%"
  gpsRSquared: string      // "0.87"
}

function ResultSummary({ metrics }: { metrics: SummaryMetrics }) {
  // 4 个卡片，每个卡片显示一个核心指标
  // 点击卡片可跳转到对应详细图表
}
```

### GMVTrendChart

```tsx
function GMVTrendChart({ artifactId }: { artifactId: string }) {
  // 从 ArtifactService 获取图表 URL
  // 使用 img 标签或 recharts/visx 渲染
  // 显示 activity vs non-activity 两条线
  // X 轴: 日期, Y 轴: GMV
  // 支持 tooltip
}
```

### LocalGapChart

```tsx
function LocalGapChart({ result }: { result: LocalGapResult }) {
  // 瀑布图: baseline → +exposure → +discount → +payday → +interaction → actual
  // 使用 recharts 或 visx 实现
  // 每段颜色区分正负贡献
}
```

### GPSDoseResponseChart

```tsx
function GPSDoseResponseChart({ result }: { result: GPSResult }) {
  // 散点图 + 拟合曲线
  // X 轴: GPS dose (exposure 或 discount)
  // Y 轴: uplift
  // 显示置信区间
}
```

### StrategyMatrix

```tsx
interface StrategyCell {
  category: string
  tier: 'high' | 'medium' | 'low'  // GPS uplift tier
  payoff: 'high' | 'medium' | 'low'  // payoff level
  type: 'Persuadables' | 'Sure Things' | 'Lost Causes' | 'Do Not Disturb'
  count: number
  recommendation: string
}

function StrategyMatrix({ cells }: { cells: StrategyCell[] }) {
  // 3x3 矩阵 (tier × payoff)
  // 每个格子显示类型 + 数量 + 建议
  // 颜色区分: Persuadables(绿), Sure Things(蓝), Lost Causes(橙), Do Not Disturb(灰)
}
```

### UpliftRankingTable

```tsx
interface UpliftRow {
  category: string
  gpsUplift: string
  persuadablesPct: string
  recommendation: string
}

function UpliftRankingTable({ rows }: { rows: UpliftRow[] }) {
  // 表格按 gpsUplift 降序排列
  // 列: Category, GPS Uplift, Persuade%, Recommendation
  // 推荐列使用 Badge 显示建议类型
}
```

## 数据获取

```typescript
// 图表数据来源: ArtifactService
const charts = await api.listArtifacts(projectId, { type: 'chart' })
const gmvTrend = charts.find(a => a.name === 'gmv_trend')
const localgapChart = charts.find(a => a.name === 'localgap_total')
const gpsChart = charts.find(a => a.name === 'gps_dose_response')

// latest_result.json
const state = await api.getProjectState(projectId)
const result = state.latestResult
```

## 图表库选择

推荐使用 **recharts**（React 原生，轻量）或 **visx**（D3 支持）：

```bash
npm install recharts
```

## 验收标准

1. Result Summary 显示 4 个核心指标
2. GMV Trend 图表正确渲染
3. LocalGap 瀑布图正确渲染
4. GPS Dose Response 图表正确渲染
5. Strategy Matrix 正确显示 3x3 分类
6. Uplift Ranking Table 按 uplift 降序排列
