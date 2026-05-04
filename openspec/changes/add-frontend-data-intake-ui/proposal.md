## Why

Data Intake 是用户上传数据、进行字段映射、数据质量检查的核心页面。根据 spec.md 第 163 行，这是 7 个核心页面之一，也是 MVP 1 的主要入口。没有 Data Intake 页面，用户无法完成数据上传和字段映射。

## What Changes

- **新增** `DataIntakePage` — `/projects/[project_id]/data-intake`
- **新增** `FileUploadZone` — 拖拽上传三张表（order_info / exposure_info / activity_timeline）
- **新增** `FileList` — 已上传文件列表，支持删除
- **新增** `SchemaInferPanel` — 字段识别结果展示，自动识别为 order/exposure/activity
- **新增** `FieldMappingTable` — 字段映射配置（源字段 → 目标字段）
- **新增** `DataQualityReport` — validation result 可视化（issues / warnings）
- **新增** `UploadProgress` — 上传进度条

## Capabilities

### New Capabilities
- `data-intake-ui`: 数据上传、字段映射、数据质量报告

### Modified Capabilities
- `frontend-skeleton`: 扩展 api-client 的 files API

## Impact

- **新建**: `frontend/src/features/data-intake/data-intake-page.tsx`
- **新建**: `frontend/src/features/data-intake/file-upload-zone.tsx`
- **新建**: `frontend/src/features/data-intake/file-list.tsx`
- **新建**: `frontend/src/features/data-intake/schema-infer-panel.tsx`
- **新建**: `frontend/src/features/data-intake/field-mapping-table.tsx`
- **新建**: `frontend/src/features/data-intake/data-quality-report.tsx`
- **修改**: `src/lib/api-client.ts` — 补充 files API 类型
