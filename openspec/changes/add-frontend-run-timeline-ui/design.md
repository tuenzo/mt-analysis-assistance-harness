## Overview

Run Timeline 页面可视化展示分析 pipeline 的 8 个步骤执行过程，以及历史运行记录。

## Pipeline 8 步骤

```
1. data.validate    (数据校验)
2. panel.build     (面板构建)
3. diagnostics     (描述性诊断)
4. psm_did         (因果推断)
5. localgap        (增量分解)
6. gps_uplift      (剂量响应)
7. chart.render    (图表生成)
8. report          (报告生成)
```

## 页面布局

```
┌─────────────────────────────────────────────────────────────┐
│  Run Timeline                              [Run Pipeline]   │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  当前运行                                                   │
│  ┌─────────────────────────────────────────────────────┐   │
│  │ Step 1: 数据校验          [██████████] 完成 2.3s   │   │
│  │ Step 2: 面板构建          [████████░░░░░░] 67% 5.1s │   │
│  │ Step 3: 描述性诊断         [░░░░░░░░░░░░░░░░░] 等待 │   │
│  │ Step 4: 因果推断           [░░░░░░░░░░░░░░░░░] 等待 │   │
│  │ ...                                                 │   │
│  └─────────────────────────────────────────────────────┘   │
│                                                             │
│  历史运行                                                   │
│  ┌─────────────────────────────────────────────────────┐   │
│  │ 2024-06-28 14:30  ✅ 完成  (8/8 steps) 耗时 45s     │   │
│  │ 2024-06-27 10:15  ✅ 完成  (8/8 steps) 耗时 52s     │   │
│  │ 2024-06-25 16:40  ❌ 失败  Step 4 (psm_did)         │   │
│  └─────────────────────────────────────────────────────┘   │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

## 组件设计

### PipelineStepsTimeline

```tsx
interface PipelineStep {
  key: string
  label: string
  status: 'pending' | 'running' | 'success' | 'error' | 'skipped'
  progress?: number  // 0-100 (running 时)
  duration?: number  // 秒数
  artifactIds?: string[]  // 产生的 artifact
  error?: string  // error 时
}

function PipelineStepsTimeline({
  steps,
  currentStep,
}: {
  steps: PipelineStep[]
  currentStep: number  // 当前执行到第几步
}) {
  // 垂直时间线布局
  // 每一步: 圆形图标 + 标签 + 耗时 + 状态
  // running 时显示 progress bar
  // success 时 ✅ 图标
  // error 时 ❌ 图标
  // artifactIds 显示 artifact 链接
}
```

### StepDetail

```tsx
function StepDetail({ step }: { step: PipelineStep }) {
  // 展开时显示 step 详情
  // 输入: 依赖的前序步骤产出
  // 输出: artifact 列表（可点击）
  // 日志摘要: 最后 10 行（可选）
  // 错误信息: error 时显示完整 stack trace
}
```

### RunHistory

```tsx
interface RunRecord {
  id: string
  startedAt: string
  finishedAt: string
  status: 'success' | 'error' | 'interrupted'
  stepsCompleted: number
  totalSteps: number
  failedStep?: string
}

function RunHistory({ runs }: { runs: RunRecord[] }) {
  // 历史运行列表
  // 每行: 时间、状态、成功步骤数、耗时
  // 点击可查看详情
}
```

## 数据获取

```typescript
// SSE 事件实时更新当前运行
// GET /api/projects/{project_id}/jobs → 历史运行列表
```

## 验收标准

1. Pipeline 8 步骤正确显示
2. 当前运行步骤实时更新（通过 SSE）
3. 历史运行记录正确显示
4. 点击 artifact 链接可跳转 Dashboard
