## Overview

Data Intake 页面负责数据接入的完整流程：上传文件 → 字段识别 → 字段映射 → 数据质量验证。

## 页面布局

```
┌─────────────────────────────────────────────────────────────┐
│  Data Intake                              [Check Quality]   │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  ┌───────────────────────────────────────────────────────┐  │
│  │ FileUploadZone (拖拽区域)                              │  │
│  │                                                       │  │
│  │  拖拽 CSV 文件到此处，或 [点击上传]                    │  │
│  │  支持: order_info.csv, exposure_info.csv,              │  │
│  │        activity_timeline.csv                          │  │
│  │  [已上传: order_info.csv ✅]                          │  │
│  │  [已上传: exposure_info.csv ✅]                       │  │
│  │  [未上传: activity_timeline.csv ❌]                  │  │
│  └───────────────────────────────────────────────────────┘  │
│                                                             │
│  ┌───────────────────────────────────────────────────────┐  │
│  │ SchemaInferPanel                                       │  │
│  │ 自动识别结果:                                          │  │
│  │  order_info.csv → [订单表] ✅                         │  │
│  │  exposure_info.csv → [曝光表] ✅                     │  │
│  │  activity_timeline.csv → [活动表] ✅                  │  │
│  └───────────────────────────────────────────────────────┘  │
│                                                             │
│  ┌───────────────────────────────────────────────────────┐  │
│  │ FieldMappingTable                                       │  │
│  │  源字段           目标字段          状态               │  │
│  │  order_id    →    order_id          ✅                │  │
│  │  gmv         →    gmv              ✅                │  │
│  │  create_time →    date              ⚠️ 需确认格式    │  │
│  └───────────────────────────────────────────────────────┘  │
│                                                             │
│  ┌───────────────────────────────────────────────────────┐  │
│  │ DataQualityReport (可折叠)                             │  │
│  │ ⚠️ 3 issues, 2 warnings                               │  │
│  │  - [activity_timeline] payday 字段缺失                 │  │
│  │  - [order_info] 2024-06-15 日期格式不一致              │  │
│  └───────────────────────────────────────────────────────┘  │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

## 组件设计

### FileUploadZone

```tsx
interface FileUploadState {
  filename: string
  role: 'order_info' | 'exposure_info' | 'activity_timeline'
  status: 'uploading' | 'done' | 'error'
  progress?: number
  error?: string
}

function FileUploadZone({ onUpload }: { onUpload: (file: File, role: string) => void }) {
  // 拖拽区域，支持 drop 文件
  // 点击上传触发 file input
  // 限制 .csv 文件
  // 拖拽时显示高亮
  // 已上传文件列表（上方显示）
}
```

### FileList

```tsx
function FileList({ files }: { files: FileUploadState[] }) {
  // 每个文件一行，显示：文件名、角色、状态、上传进度
  // 删除按钮（X）
  // 状态 badge：uploading(蓝)、done(绿)、error(红)
}
```

### SchemaInferPanel

```tsx
interface SchemaInferResult {
  filename: string
  inferredRole: 'order_info' | 'exposure_info' | 'activity_timeline'
  confidence: number  // 0-1
  columns: string[]
}

function SchemaInferPanel({ result }: { result: SchemaInferResult[] }) {
  // 展示每个文件的识别结果
  // 高置信度(>0.8) ✅，中(0.5-0.8) ⚠️，低(<0.5) ❌
  // 用户可手动修正识别结果
}
```

### FieldMappingTable

```tsx
interface FieldMapping {
  sourceField: string
  targetField: string
  mapped: boolean
  issues?: string[]
}

function FieldMappingTable({ mappings }: { mappings: FieldMapping[] }) {
  // 表格展示：源字段 → 目标字段
  // 映射成功 ✅，未映射 ❌，有问题 ⚠️
  // 用户可点击单元格修改映射
}
```

### DataQualityReport

```tsx
interface QualityIssue {
  file: string
  field?: string
  type: 'error' | 'warning'
  message: string
  rowCount?: number
}

function DataQualityReport({ issues }: { issues: QualityIssue[] }) {
  // 可折叠面板
  // issues 列表，按 type 分组
  // error 红色，warning 黄色
  // 点击 issue 可跳转到对应文件和字段
}
```

## 数据流

```
用户上传文件
    │
    ▼
POST /api/projects/{project_id}/files (uploadFile)
    │
    ▼
文件保存 → ProjectFile record 创建
    │
    ▼
POST /api/projects/{project_id}/files/infer-schema (inferSchema)
    │
    ▼
SchemaInferPanel 显示识别结果
    │
    ▼
用户确认/修改映射
    │
    ▼
POST /api/projects/{project_id}/schema/apply (applySchema)
    │
    ▼
调用 data.validate → DataQualityReport 显示问题
```

## 验收标准

1. 用户可拖拽上传 CSV 文件
2. 上传后自动触发 schema 推断
3. 字段映射表格可编辑
4. 数据质量报告正确显示 issues/warnings
5. Apply Schema 后更新 project_manifest
