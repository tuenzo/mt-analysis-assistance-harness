## Overview

本变更实现数据库 ORM models + Projects/Files API。后端使用 FastAPI + SQLAlchemy + SQLite（MVP）。WorkspaceManager 在 project 创建时自动初始化 workspace 目录结构。

## Architecture

```
backend/app/
├── core/
│   ├── config.py          # Settings（workspace_root 等）
│   └── database.py        # SQLAlchemy engine + session
├── projects/
│   ├── models.py          # 所有 12 张表 ORM models
│   ├── schemas.py         # Pydantic request/response schemas
│   └── service.py         # ProjectService 业务逻辑
├── workspace/
│   ├── manager.py         # WorkspaceManager（已在上个变更实现）
│   └── manifest.py        # ProjectManifest（已在上个变更实现）
└── api/
    ├── projects.py        # Projects API 路由
    └── files.py           # Files API 路由
```

## Database Schema

使用 SQLite，12 张表。Models 定义参考 `specs/business-analysis-system/data-model.md`。

关键索引：
- `projects.id` — PRIMARY KEY
- `project_files.project_id` — FOREIGN KEY + index
- `analysis_sessions.project_id` — FOREIGN KEY + index
- `agent_turns.session_id` — FOREIGN KEY + index

## API 设计

### Projects API

```
POST /api/projects
  Request: {name, description?, domain?}
  Response: {id, name, workspace_path, status, current_stage}
  副作用: 创建 workspace 目录 + 初始化 manifest

GET /api/projects
  Response: [{id, name, status, created_at}, ...]

GET /api/projects/{project_id}
  Response: {id, name, workspace_path, status, current_stage, ...}

GET /api/projects/{project_id}/state
  Response: {project, files, latest_session, latest_jobs, latest_artifacts,
             latest_report, memory_candidates_count, next_actions}
```

### Files API

```
POST /api/projects/{project_id}/files
  Form: file(binary), role(order_info|exposure_info|activity_timeline|unknown)
  Response: {file_id, role, original_name, status, checksum}
  副作用: 文件写入 data/raw/ + ProjectFile record + manifest 更新

GET /api/projects/{project_id}/files
  Response: [{file_id, role, original_name, current_path, status, checksum}, ...]

POST /api/projects/{project_id}/files/infer-schema
  Response: {files: [{file_id, role_guess, columns: [{name, dtype, mapped_to, confidence}]}]}
  逻辑: 读取 CSV header，匹配已知列名模式（order_id, pay_time, gmv, discount, category 等）

POST /api/projects/{project_id}/schema/apply
  Request: {mappings: {file_id: {col: mapped_to}}}
  Response: {status: "mapped"}
  副作用: 更新 ProjectFile.schema_json
```

## Key Implementation Decisions

1. **事务**: 每个 API 操作在 db session 内完成，失败自动 rollback
2. **Workspace 联动**: ProjectService.create_project() 调用 WorkspaceManager.create_workspace()
3. **文件存储**: 不存数据库，只存 workspace 路径 + checksum；文件本体在 data/raw/
4. **Schema 推断**: 第一版用简单字符串匹配（"order_id"→"order_id", "payday"→"date"），不引入 ML
5. **UUID 生成**: 使用 `uuid.uuid4().hex` 作为主键