## Why

Artifact（图表、表格、模型结果、报告文件）是分析交付物的核心载体。当前 analysis-pipelines 和 report-memory-system 都会生成 artifact，但没有任何 proposal 定义 ArtifactService 的统一职责：注册、读取、版本管理、清理。没有 ArtifactService，分析结果就无法统一管理和展示。

## What Changes

- **新增** `ArtifactService` — 统一管理所有 artifact 的注册、读取、列表、删除
- **新增** `Artifact` 表扩展字段：artifact_type（chart/table/model_output/report_source）、tags、checksum
- **新增** Artifacts API：`GET /api/projects/{project_id}/artifacts`, `GET /api/artifacts/{artifact_id}`, `DELETE /api/artifacts/{artifact_id}`
- **新增** artifact 版本管理：同 artifact_id 多版本，latest_version 指针
- **新增** artifact 关联：分析 job 完成后自动注册 artifact 到 service

## Capabilities

### New Capabilities
- `artifact-service`: 分析产物统一管理

### Modified Capabilities
- `analysis-pipelines`: pipeline 完成后通过 ArtifactService 注册 artifact
- `report-memory-system`: 报告依赖 artifact registry 获取图表引用

## Impact

- **新建**: `backend/app/artifacts/service.py` — ArtifactService
- **新建**: `backend/app/artifacts/models.py` — Artifact ORM model 扩展
- **新建**: `backend/app/api/artifacts.py` — Artifacts API
- **修改**: `backend/app/analysis/pipelines/full_pipeline.py` — 接入 ArtifactService
