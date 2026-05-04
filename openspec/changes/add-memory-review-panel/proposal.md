## Why

Memory Review Panel 是 MVP 4 的核心 UI 组件，让用户确认哪些分析结论可以同步到长期记忆。当前 report-memory-system 的 proposal 只定义了 `memory.propose_update` action 和基本 API，没有独立设计 Memory Review Panel 的后端数据接口。没有这些接口，前端无法展示记忆候选列表，也无法执行 approve/reject 操作。

## What Changes

- **新增** MemoryCandidates API：`GET /api/projects/{project_id}/memory/candidates`, `GET /api/memory/candidates/{id}`, `POST /api/memory/candidates/{id}/approve`, `POST /api/memory/candidates/{id}/reject`
- **新增** MemoryCandidate 表的完整字段：scope（project/user_preference/global_business_memory）、category（conclusion/preference/methodology）、content、source_artifact_ids
- **新增** `MemorySyncService` — 处理 approve 后的同步逻辑（写入 .analysis/memory_candidates.md 或导出到用户级 memory）
- **新增** 记忆候选生成策略：从 latest_result 自动生成项目摘要、从 gps_result 生成策略模式结论

## Capabilities

### New Capabilities
- `memory-review-panel-api`: 记忆候选列表、approve/reject、sync

### Modified Capabilities
- `report-memory-system`: 扩展 memory.propose_update 的触发时机和内容类型

## Impact

- **新建**: `backend/app/memory/sync.py` — MemorySyncService
- **修改**: `backend/app/memory/models.py` — MemoryCandidate 字段扩展
- **新建**: `backend/app/api/memory.py` — Memory API（已有 proposal，需要补充 scope/category）
- **测试**: 记忆候选 approve/reject 测试、sync 逻辑测试
