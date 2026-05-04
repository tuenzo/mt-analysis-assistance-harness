## Why

报告是用户交付商业分析结果的主要形式。Memory Review 则实现"伴随式个人助手体验"——让用户确认哪些分析结论可以同步到长期记忆，形成跨项目复用的偏好和知识。没有这两个，系统只产出数据结果，无法形成可分享的报告和可持续的记忆。

## What Changes

- **新增** `report.generate` — 基于 latest_result.json 生成 report.md（摘要、数据说明、分析流程、核心结果、策略建议、限制说明、artifact 引用）
- **新增** `report.export` — 支持 PDF/LaTeX/DOCX 导出（第一版先支持 md，后续扩展）
- **新增** Reports API：`POST /api/projects/{project_id}/reports/generate`, `GET /api/projects/{project_id}/reports/latest`, `POST /api/reports/{report_id}/export`
- **新增** MemoryCandidate 表 + MemoryBridge
- **新增** `memory.propose_update` — 从分析结果生成记忆候选（项目摘要、用户偏好、业务结论）
- **新增** Memory API：`GET /api/projects/{project_id}/memory/candidates`, `POST /api/memory/candidates/{id}/approve`, `POST /api/memory/candidates/{id}/reject`
- **新增** Memory Review Panel 数据接口（approve 后写入 `.analysis/memory_candidates.md` 或用户级 memory）

## Capabilities

### New Capabilities
- `report-generation`: 分析报告生成与导出
- `memory-bridge`: 记忆候选生成与审批同步

### Modified Capabilities
- 无

## Impact

- **新建**: `backend/app/reports/renderer.py` — Markdown 报告渲染
- **新建**: `backend/app/reports/exporters.py` — PDF/LaTeX/DOCX exporter
- **新建**: `backend/app/reports/templates/` — 报告模板
- **新建**: `backend/app/memory/bridge.py` — MemoryBridge
- **新建**: `backend/app/memory/summarizer.py` — 记忆摘要生成
- **新建**: `backend/app/memory/store.py` — 记忆存储
- **新建**: `backend/app/api/reports.py` — Reports API
- **新建**: `backend/app/api/memory.py` — Memory API
- **修改**: `backend/app/tools/memory_tools.py` — 接入 MemoryBridge
- **测试**: 报告生成测试、记忆候选 approve/reject 测试