## Why

报告生成是 MVP 3 的核心交付物。当前 report-memory-system 的 proposal 只定义了 `report.generate` action 和基本 API，没有独立设计 ReportRenderer、report template、exporter 和完整 Reports API。分析结果必须通过结构化报告才能变成可分享的业务交付物。

## What Changes

- **新增** `ReportRenderer` — 基于 report template 生成 markdown 报告
- **新增** report templates（promo_analysis_default）— 包含摘要、数据说明、分析方法、核心结果、策略建议、限制说明、下周期建议
- **新增** `report.export` — md → PDF / LaTeX 导出（第一版 PDF）
- **新增** Reports API：`POST /api/projects/{project_id}/reports/generate`, `GET /api/projects/{project_id}/reports/latest`, `POST /api/reports/{report_id}/export`
- **新增** `Report` 表的完整字段：report_type、template_name、content_md、file_path、exported_path、metadata

## Capabilities

### New Capabilities
- `report-service`: 报告渲染与导出

### Modified Capabilities
- `analysis-pipelines`: full_pipeline 完成后触发报告生成
- `artifact-service`: 报告注册为 artifact（type=report_source）

## Impact

- **新建**: `backend/app/reports/renderer.py` — ReportRenderer
- **新建**: `backend/app/reports/templates/promo_analysis_default.md`
- **新建**: `backend/app/reports/exporters.py` — PDF exporter
- **新建**: `backend/app/reports/service.py` — ReportService（整合 renderer + exporter）
- **修改**: `backend/app/reports/models.py` — Report model 扩展
- **测试**: 报告生成测试、导出测试
