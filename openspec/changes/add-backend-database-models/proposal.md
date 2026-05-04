## Why

Message runtime 需要数据库记录 session、turn、events；files API 需要存储文件元数据。没有这些 ORM model，后续的 agent message runtime、tool gateway、job orchestrator 都无法持久化状态或追踪来源。Project 和 ProjectFile 是整个系统的事实记录起点。

## What Changes

- **新增** SQLAlchemy ORM models：`Project`, `ProjectFile`, `AnalysisSession`, `AgentTurn`, `AgentEvent`, `ToolCall`, `Job`, `Artifact`, `Report`, `ApprovalRequest`, `MemoryCandidate`, `WorkspaceCheckpoint`
- **新增** Pydantic schemas 用于 API 请求/响应验证
- **新增** Projects API：`POST /api/projects`, `GET /api/projects`, `GET /api/projects/{project_id}`, `GET /api/projects/{project_id}/state`
- **新增** Files API：`POST /api/projects/{project_id}/files`, `GET /api/projects/{project_id}/files`, `POST /api/projects/{project_id}/files/infer-schema`, `POST /api/projects/{project_id}/schema/apply`
- **新增** WorkspaceManager 与数据库的联动：创建 project 时自动初始化 workspace 目录

## Capabilities

### New Capabilities
- `database-models`: 定义 12 张数据库表结构、ORM models、索引
- `projects-api`: 项目 CRUD 与状态 API
- `files-api`: 文件上传、schema 推断、字段映射 API

### Modified Capabilities
- `project-workspace-structure`: 扩展以联动数据库创建

## Impact

- **新建**: `backend/app/core/database.py` — SQLAlchemy engine、session
- **新建**: `backend/app/projects/models.py` — ORM models
- **新建**: `backend/app/projects/schemas.py` — Pydantic schemas
- **新建**: `backend/app/projects/service.py` — ProjectService
- **新建**: `backend/app/api/projects.py` — Projects API 路由
- **新建**: `backend/app/api/files.py` — Files API 路由
- **修改**: `backend/app/workspace/manager.py` — 创建 project 时联动初始化 workspace
- **测试**: API 集成测试、model 测试