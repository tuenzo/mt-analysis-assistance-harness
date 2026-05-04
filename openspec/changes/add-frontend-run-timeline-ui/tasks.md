## Tasks

### Phase 1: API 类型扩展

- [ ] **T1.1** — 扩展 `src/lib/api-types.ts`
  ```typescript
  interface PipelineStep { ... }
  interface RunRecord { ... }
  ```

### Phase 2: 组件实现

- [ ] **T2.1** — `src/features/timeline/run-timeline-page.tsx`
  - 页面布局

- [ ] **T2.2** — `src/features/timeline/pipeline-steps-timeline.tsx`
  - 8 步骤时间线

- [ ] **T2.3** — `src/features/timeline/step-detail.tsx`
  - 步骤详情

- [ ] **T2.4** — `src/features/timeline/run-history.tsx`
  - 历史运行记录

### Phase 3: 页面路由

- [ ] **T3.1** — 确保 `src/app/projects/[project_id]/timeline/page.tsx` 渲染 RunTimelinePage

### Phase 4: 验收测试

- [ ] **T4.1** — 当前运行步骤实时更新
- [ ] **T4.2** — 历史运行记录正确显示

---

## 验收标准

1. Pipeline 8 步骤正确显示
2. SSE 事件实时更新步骤状态
3. 历史运行记录正确显示
4. artifact 链接可点击
