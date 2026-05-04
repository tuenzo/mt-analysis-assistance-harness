## Overview

Project Home 展示项目整体状态，让用户快速了解"项目走到哪一步了"、"数据齐不齐"、"下一步该做什么"。

## 页面布局

```
┌─────────────────────────────────────────────────────────────┐
│  [项目名称]                               [Settings] [Help]  │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  ┌─────────────────────┐  ┌─────────────────────────────┐  │
│  │ ProjectStatusCard    │  │ QuickActions                │  │
│  │ 当前阶段: 分析中     │  │ [上传数据] [开始分析] [报告] │  │
│  │ 阶段进度: Step 3/8   │  └─────────────────────────────┘  │
│  └─────────────────────┘                                    │
│                                                             │
│  ┌───────────────────────────────────────────────────────┐  │
│  │ DataStatusPanel                                       │  │
│  │ ✅ order_info.csv  (1.2M rows, 2024-06-01~06-30)    │  │
│  │ ✅ exposure_info.csv (3.4M rows)                     │  │
│  │ ⚠️ activity_timeline.csv (缺失 payday 字段)          │  │
│  └───────────────────────────────────────────────────────┘  │
│                                                             │
│  ┌───────────────────────────────────────────────────────┐  │
│  │ LatestResultPanel                                     │  │
│  │ 最新分析: 2024-06-28                                  │  │
│  │ GMV 变化: +23.5% | LocalGap: +¥1.2M | GPS Uplift:  │  │
│  │ [查看详情 →] [生成报告]                               │  │
│  └───────────────────────────────────────────────────────┘  │
│                                                             │
│  ┌───────────────────────────────────────────────────────┐  │
│  │ NextStepSuggestions                                   │  │
│  │ 1. ⚠️ 请补充 activity_timeline.csv 的 payday 字段    │  │
│  │ 2. 建议先运行 diagnostics 了解数据整体情况             │  │
│  │ 3. 当前阶段适合开始 run_full_pipeline                 │  │
│  └───────────────────────────────────────────────────────┘  │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

## 组件设计

### ProjectStatusCard

```tsx
const PROJECT_STAGES = {
  data_intake: { label: '数据接入', color: 'blue' },
  schema_mapping: { label: '字段映射', color: 'blue' },
  analysis: { label: '分析中', color: 'green' },
  report: { label: '报告生成', color: 'green' },
  memory: { label: '记忆复盘', color: 'purple' },
}

function ProjectStatusCard({ stage, step, totalSteps }: Props) {
  // 阶段名称 + Badge
  // 步骤进度: Step {step}/{totalSteps}
  // 根据 stage 显示对应颜色
}
```

### DataStatusPanel

```tsx
interface DataFileStatus {
  role: 'order_info' | 'exposure_info' | 'activity_timeline'
  filename: string
  rowCount?: number
  dateRange?: string
  quality: 'ok' | 'warning' | 'error' | 'missing'
  issues?: string[]  // quality=warning/error 时的问题列表
}

function DataStatusPanel({ files }: { files: DataFileStatus[] }) {
  // 列表展示每个文件的角色、名称、状态
  // quality=warning 显示⚠️ + issues
  // quality=error 显示❌ + issues
  // quality=missing 显示❌ + "未上传"
}
```

### LatestResultPanel

```tsx
function LatestResultPanel({ result }: { result: LatestResult | null }) {
  if (!result) return (
    <Card>
      <CardContent>暂无分析结果，建议先上传数据并运行分析</CardContent>
    </Card>
  )

  return (
    <Card>
      <CardHeader>最新分析结果</CardHeader>
      <CardContent>
        <p>分析时间: {result.analysisDate}</p>
        <p>GMV 变化: {result.gmvChange}</p>
        <p>LocalGap: {result.localgapTotal}</p>
        <p>Persuadables: {result.persuadablesPct}</p>
        <Button variant="outline" onClick={() => navigate(`/projects/${projectId}/dashboard`)}>
          查看详情 →
        </Button>
        <Button onClick={() => navigate(`/projects/${projectId}/reports`)}>
          生成报告
        </Button>
      </CardContent>
    </Card>
  )
}
```

### NextStepSuggestions

```tsx
function NextStepSuggestions({ projectState }: { projectState: ProjectState }) {
  // 根据当前阶段生成 2-3 条建议
  // data_intake 阶段: "请上传三张表"
  // schema_mapping 阶段: "请检查字段映射"
  // analysis 阶段: "建议运行 diagnostics"
  // 每个建议可点击，直接导航或触发 action
}
```

### QuickActions

```tsx
function QuickActions({ projectState, onAction }: Props) {
  // 根据当前阶段显示可用操作
  // data_intake: [上传数据] [检查字段]
  // schema_mapping: [应用映射] [开始分析]
  // analysis: [运行分析] [查看结果]
  // 每个 action 按钮调用 onAction
}
```

## 数据获取

```typescript
// ProjectHomePage
const { project, projectState } = useProject(projectId)
// projectState.files → DataStatusPanel
// projectState.latestResult → LatestResultPanel
// projectState.currentStage → ProjectStatusCard
// generateSuggestions(projectState) → NextStepSuggestions
```

## 验收标准

1. 页面正确显示项目名称、当前阶段
2. DataStatusPanel 正确反映文件上传状态
3. LatestResultPanel 在有结果时显示摘要，无结果时显示空状态
4. NextStepSuggestions 根据当前阶段生成合理建议
5. QuickActions 根据当前阶段显示正确操作
