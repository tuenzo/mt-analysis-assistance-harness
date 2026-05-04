## Tasks

### Phase 1: 依赖安装

- [ ] **T1.1** — 安装 recharts
  ```bash
  npm install recharts
  ```

### Phase 2: API 类型扩展

- [ ] **T2.1** — 扩展 `src/lib/api-types.ts`
  ```typescript
  interface SummaryMetrics { ... }
  interface LocalGapResult { ... }
  interface GPSResult { ... }
  interface StrategyCell { ... }
  interface UpliftRow { ... }
  ```

### Phase 3: 组件实现

- [ ] **T3.1** — `src/features/dashboard/result-dashboard-page.tsx`
  - 页面布局，组合子组件

- [ ] **T3.2** — `src/features/dashboard/result-summary.tsx`
  - 4 个核心指标卡片

- [ ] **T3.3** — `src/features/dashboard/gmv-trend-chart.tsx`
  - GMV 折线图（recharts LineChart）

- [ ] **T3.4** — `src/features/dashboard/localgap-chart.tsx`
  - 瀑布图（recharts BarChart）

- [ ] **T3.5** — `src/features/dashboard/gps-dose-response-chart.tsx`
  - 散点图 + 拟合曲线（recharts ScatterChart）

- [ ] **T3.6** — `src/features/dashboard/strategy-matrix.tsx`
  - 3x3 矩阵表格

- [ ] **T3.7** — `src/features/dashboard/uplift-ranking-table.tsx`
  - 排名表格

### Phase 4: 页面路由

- [ ] **T4.1** — 确保 `src/app/projects/[project_id]/dashboard/page.tsx` 渲染 ResultDashboardPage

### Phase 5: 验收测试

- [ ] **T5.1** — 有数据时图表正确渲染
- [ ] **T5.2** — 无数据时显示空状态骨架屏

---

## 验收标准

1. 所有图表组件正确渲染
2. 数据来自 API（ArtifactService），无硬编码
3. 无数据时优雅降级（骨架屏或空状态）
4. 图表支持基本交互（tooltip）
