## Tasks

### Phase 1: API 类型扩展

- [ ] **T1.1** — 扩展 `src/lib/api-types.ts`
  ```typescript
  interface DataFileStatus {
    role: 'order_info' | 'exposure_info' | 'activity_timeline'
    filename: string
    rowCount?: number
    dateRange?: string
    quality: 'ok' | 'warning' | 'error' | 'missing'
    issues?: string[]
  }
  ```

### Phase 2: 组件实现

- [ ] **T2.1** — `src/features/project/project-home-page.tsx`
  - 页面布局，组合子组件

- [ ] **T2.2** — `src/features/project/project-status-card.tsx`
  - 阶段 Badge + 进度

- [ ] **T2.3** — `src/features/project/data-status-panel.tsx`
  - 文件列表 + 状态

- [ ] **T2.4** — `src/features/project/latest-result-panel.tsx`
  - 最新结果摘要

- [ ] **T2.5** — `src/features/project/next-step-suggestions.tsx`
  - 根据阶段生成建议

- [ ] **T2.6** — `src/features/project/quick-actions.tsx`
  - 快捷操作按钮

### Phase 3: 页面路由

- [ ] **T3.1** — 确保 `src/app/projects/[project_id]/page.tsx` 渲染 ProjectHomePage

### Phase 4: 验收测试

- [ ] **T4.1** — 有项目数据时页面正确渲染
- [ ] **T4.2** — 无项目数据时页面不崩溃（空状态）

---

## 验收标准

1. Project Home 页面正确组合所有子组件
2. 数据状态、文件状态、结果状态正确显示
3. 下一步建议基于当前阶段生成
4. 快捷操作按钮能触发正确导航
