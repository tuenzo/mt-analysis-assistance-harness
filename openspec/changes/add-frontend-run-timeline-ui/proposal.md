## Why

Run Timeline 展示分析 pipeline 的执行过程（data → panel → diagnostics → causal → uplift → report）。根据 spec.md 第 165 行，这是 7 个核心页面之一。用户可以在这里看到每个步骤的执行状态、耗时、产出 artifact。

## What Changes

- **新增** `RunTimelinePage` — `/projects/[project_id]/timeline`
- **新增** `PipelineStepsTimeline` — 可视化 pipeline 8 步骤执行过程
- **新增** `StepDetail` — 单个步骤详情（输入、输出、耗时、状态）
- **新增** `Artifact produced` 标记 — 步骤完成后显示 artifact 链接
- **新增** `RunHistory` — 历史运行记录列表

## Capabilities

### New Capabilities
- `run-timeline-ui`: Pipeline 执行过程可视化

### Modified Capabilities
- `frontend-skeleton`: 扩展 api-client 的 jobs API

## Impact

- **新建**: `frontend/src/features/timeline/run-timeline-page.tsx`
- **新建**: `frontend/src/features/timeline/pipeline-steps-timeline.tsx`
- **新建**: `frontend/src/features/timeline/step-detail.tsx`
- **新建**: `frontend/src/features/timeline/run-history.tsx`
