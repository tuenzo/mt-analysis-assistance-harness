## Why

Result Dashboard 展示分析结果（趋势图、LocalGap、GPS、Uplift、策略矩阵）。根据 spec.md 第 166 行，这是 7 个核心页面之一。没有 Result Dashboard，分析结果无法可视化呈现给用户。

## What Changes

- **新增** `ResultDashboardPage` — `/projects/[project_id]/dashboard`
- **新增** `GMVTrendChart` — GMV 时间序列趋势图
- **新增** `LocalGapChart` — LocalGap 增量分解瀑布图
- **新增** `GPSDoseResponseChart` — GPS 剂量响应曲线
- **新增** `UpliftRankingTable` — Uplift 排名表（Persuadables / Sure Things / Lost Causes / Do Not Disturb）
- **新增** `StrategyMatrix` — 策略矩阵（按 category × payoff 分层）
- **新增** `ResultSummary` — 核心指标摘要卡片

## Capabilities

### New Capabilities
- `result-dashboard-ui`: 分析结果图表可视化

### Modified Capabilities
- `frontend-skeleton`: 扩展 api-client 的 artifacts API（获取图表 URL）
- `add-artifact-service`: Dashboard 通过 ArtifactService 获取已注册的 artifact

## Impact

- **新建**: `frontend/src/features/dashboard/result-dashboard-page.tsx`
- **新建**: `frontend/src/features/dashboard/gmv-trend-chart.tsx`
- **新建**: `frontend/src/features/dashboard/localgap-chart.tsx`
- **新建**: `frontend/src/features/dashboard/gps-dose-response-chart.tsx`
- **新建**: `frontend/src/features/dashboard/uplift-ranking-table.tsx`
- **新建**: `frontend/src/features/dashboard/strategy-matrix.tsx`
- **新建**: `frontend/src/features/dashboard/result-summary.tsx`
