---
name: data-model
description: 数据模型文档 - 数据库实体、Workspace Manifest、Context Summary 格式
type: spec
parent: business-analysis-system
---

# 数据模型文档

## 1. 设计原则

1. 数据库记录结构化状态
2. workspace 保存真实文件和 artifact
3. project_manifest.json 保存文件事实状态
4. Claude session 不作为事实源
5. agent_turn 是主对象，job/tool_call 是 turn 中的动作
6. artifact 必须可追踪来源 job、tool_call 和输入文件版本

## 2. 数据库实体

```
User
Project
ProjectFile
AnalysisSession
AgentTurn
AgentEvent
ToolCall
Job
Artifact
Report
ApprovalRequest
MemoryCandidate
WorkspaceCheckpoint
```

MVP 可用 SQLite。ORM 建议 SQLAlchemy 或 Prisma。

## 3. 表结构

### projects

```sql
CREATE TABLE projects (
  id TEXT PRIMARY KEY,
  name TEXT NOT NULL,
  description TEXT,
  workspace_path TEXT NOT NULL,
  domain TEXT DEFAULT 'promo_analysis',
  status TEXT NOT NULL DEFAULT 'created',
  current_stage TEXT DEFAULT 'created',
  created_at TIMESTAMP NOT NULL,
  updated_at TIMESTAMP NOT NULL
);
```

**status enum**:
- `created`
- `data_uploaded`
- `validated`
- `panel_ready`
- `analysis_ready`
- `report_ready`
- `archived`
- `error`

**current_stage enum**:
- `created`
- `data_intake`
- `schema_mapping`
- `data_validation`
- `panel_build`
- `diagnostics`
- `psm_did`
- `localgap`
- `gps_uplift`
- `strategy`
- `report`
- `memory_review`

### project_files

```sql
CREATE TABLE project_files (
  id TEXT PRIMARY KEY,
  project_id TEXT NOT NULL,
  role TEXT NOT NULL,
  original_name TEXT NOT NULL,
  current_path TEXT NOT NULL,
  mime_type TEXT,
  size_bytes INTEGER,
  checksum TEXT NOT NULL,
  schema_hash TEXT,
  schema_json TEXT,
  status TEXT NOT NULL DEFAULT 'uploaded',
  created_at TIMESTAMP NOT NULL,
  updated_at TIMESTAMP NOT NULL,
  FOREIGN KEY(project_id) REFERENCES projects(id)
);
```

**role enum**:
- `order_info`
- `exposure_info`
- `activity_timeline`
- `auxiliary`
- `unknown`

**status enum**:
- `uploaded`
- `recognized`
- `mapped`
- `validated`
- `invalid`
- `missing`
- `changed`
- `stale`

### analysis_sessions

```sql
CREATE TABLE analysis_sessions (
  id TEXT PRIMARY KEY,
  project_id TEXT NOT NULL,
  runtime_provider TEXT NOT NULL DEFAULT 'claude_agent_sdk',
  external_session_id TEXT,
  status TEXT NOT NULL DEFAULT 'active',
  created_at TIMESTAMP NOT NULL,
  updated_at TIMESTAMP NOT NULL,
  FOREIGN KEY(project_id) REFERENCES projects(id)
);
```

**status enum**: `active`, `paused`, `completed`, `interrupted`, `error`

### agent_turns

```sql
CREATE TABLE agent_turns (
  id TEXT PRIMARY KEY,
  session_id TEXT NOT NULL,
  project_id TEXT NOT NULL,
  user_message TEXT NOT NULL,
  assistant_message TEXT,
  intent TEXT,
  status TEXT NOT NULL DEFAULT 'running',
  created_at TIMESTAMP NOT NULL,
  completed_at TIMESTAMP,
  error_message TEXT,
  FOREIGN KEY(session_id) REFERENCES analysis_sessions(id),
  FOREIGN KEY(project_id) REFERENCES projects(id)
);
```

**intent enum**:
- `conversation`
- `status_query`
- `data_operation`
- `analysis_request`
- `report_request`
- `memory_request`
- `unknown`

intent 只用于记录和辅助 UI，不应成为硬路由的唯一依据。

### agent_events

```sql
CREATE TABLE agent_events (
  id TEXT PRIMARY KEY,
  session_id TEXT NOT NULL,
  turn_id TEXT,
  project_id TEXT NOT NULL,
  type TEXT NOT NULL,
  payload_json TEXT NOT NULL,
  created_at TIMESTAMP NOT NULL,
  FOREIGN KEY(session_id) REFERENCES analysis_sessions(id),
  FOREIGN KEY(turn_id) REFERENCES agent_turns(id),
  FOREIGN KEY(project_id) REFERENCES projects(id)
);
```

**type enum**:
- `user_message`
- `assistant_message_delta`
- `assistant_message`
- `tool_call_started`
- `tool_call_finished`
- `tool_call_failed`
- `job_started`
- `job_progress`
- `job_finished`
- `artifact_created`
- `approval_required`
- `approval_resolved`
- `memory_candidate_created`
- `report_generated`
- `runtime_error`
- `final_answer`

### tool_calls

```sql
CREATE TABLE tool_calls (
  id TEXT PRIMARY KEY,
  session_id TEXT NOT NULL,
  turn_id TEXT NOT NULL,
  project_id TEXT NOT NULL,
  tool_name TEXT NOT NULL,
  action TEXT NOT NULL,
  payload_json TEXT NOT NULL,
  payload_hash TEXT NOT NULL,
  reason TEXT,
  status TEXT NOT NULL DEFAULT 'pending',
  result_json TEXT,
  error_message TEXT,
  permission_level INTEGER NOT NULL DEFAULT 0,
  approval_request_id TEXT,
  created_at TIMESTAMP NOT NULL,
  completed_at TIMESTAMP,
  FOREIGN KEY(session_id) REFERENCES analysis_sessions(id),
  FOREIGN KEY(turn_id) REFERENCES agent_turns(id),
  FOREIGN KEY(project_id) REFERENCES projects(id)
);
```

**status enum**: `pending`, `waiting_approval`, `running`, `succeeded`, `failed`, `rejected`

### jobs

```sql
CREATE TABLE jobs (
  id TEXT PRIMARY KEY,
  project_id TEXT NOT NULL,
  session_id TEXT,
  turn_id TEXT,
  tool_call_id TEXT,
  action TEXT NOT NULL,
  status TEXT NOT NULL DEFAULT 'queued',
  progress REAL DEFAULT 0,
  input_json TEXT,
  output_json TEXT,
  error_message TEXT,
  started_at TIMESTAMP,
  finished_at TIMESTAMP,
  created_at TIMESTAMP NOT NULL,
  FOREIGN KEY(project_id) REFERENCES projects(id),
  FOREIGN KEY(tool_call_id) REFERENCES tool_calls(id)
);
```

**status enum**: `queued`, `running`, `succeeded`, `failed`, `cancelled`

### artifacts

```sql
CREATE TABLE artifacts (
  id TEXT PRIMARY KEY,
  project_id TEXT NOT NULL,
  job_id TEXT,
  tool_call_id TEXT,
  type TEXT NOT NULL,
  title TEXT NOT NULL,
  path TEXT NOT NULL,
  mime_type TEXT,
  metadata_json TEXT,
  checksum TEXT,
  created_at TIMESTAMP NOT NULL,
  FOREIGN KEY(project_id) REFERENCES projects(id),
  FOREIGN KEY(job_id) REFERENCES jobs(id),
  FOREIGN KEY(tool_call_id) REFERENCES tool_calls(id)
);
```

**type enum**:
- `dataset`
- `validation_report`
- `panel`
- `chart`
- `table`
- `model_output`
- `result_summary`
- `report_source`
- `report_pdf`
- `report_docx`
- `memory_summary`
- `log`

### reports

```sql
CREATE TABLE reports (
  id TEXT PRIMARY KEY,
  project_id TEXT NOT NULL,
  job_id TEXT,
  status TEXT NOT NULL DEFAULT 'draft',
  title TEXT,
  source_md_path TEXT,
  source_tex_path TEXT,
  pdf_path TEXT,
  docx_path TEXT,
  metadata_json TEXT,
  created_at TIMESTAMP NOT NULL,
  updated_at TIMESTAMP NOT NULL,
  FOREIGN KEY(project_id) REFERENCES projects(id),
  FOREIGN KEY(job_id) REFERENCES jobs(id)
);
```

**status enum**: `draft`, `generated`, `exported`, `failed`

### approval_requests

```sql
CREATE TABLE approval_requests (
  id TEXT PRIMARY KEY,
  project_id TEXT NOT NULL,
  session_id TEXT,
  turn_id TEXT,
  tool_call_id TEXT,
  action TEXT NOT NULL,
  reason TEXT,
  risk_level TEXT NOT NULL,
  payload_json TEXT NOT NULL,
  status TEXT NOT NULL DEFAULT 'pending',
  created_at TIMESTAMP NOT NULL,
  resolved_at TIMESTAMP,
  resolved_by TEXT,
  FOREIGN KEY(project_id) REFERENCES projects(id)
);
```

**risk_level enum**: `low`, `medium`, `high`, `critical`

**status enum**: `pending`, `approved`, `rejected`, `expired`

### memory_candidates

```sql
CREATE TABLE memory_candidates (
  id TEXT PRIMARY KEY,
  project_id TEXT NOT NULL,
  session_id TEXT,
  turn_id TEXT,
  scope TEXT NOT NULL,
  content TEXT NOT NULL,
  source_artifact_ids TEXT,
  status TEXT NOT NULL DEFAULT 'pending',
  created_at TIMESTAMP NOT NULL,
  resolved_at TIMESTAMP,
  FOREIGN KEY(project_id) REFERENCES projects(id)
);
```

**scope enum**:
- `project`
- `user_preference`
- `global_business_memory`

**status enum**: `pending`, `approved`, `rejected`, `synced`

### workspace_checkpoints

```sql
CREATE TABLE workspace_checkpoints (
  id TEXT PRIMARY KEY,
  project_id TEXT NOT NULL,
  label TEXT,
  manifest_snapshot_json TEXT NOT NULL,
  created_at TIMESTAMP NOT NULL,
  FOREIGN KEY(project_id) REFERENCES projects(id)
);
```

## 4. Workspace Manifest

路径：`workspaces/{project_id}/.analysis/project_manifest.json`

```json
{
  "project_id": "proj_001",
  "version": 1,
  "current_stage": "panel_ready",
  "files": [
    {
      "file_id": "file_order",
      "role": "order_info",
      "original_name": "order_info.csv",
      "current_path": "data/raw/order_info.csv",
      "checksum": "sha256:...",
      "schema_hash": "sha256:...",
      "status": "validated",
      "last_verified_at": "2026-05-04T10:00:00Z"
    }
  ],
  "derived_assets": [
    {
      "asset_id": "panel_001",
      "role": "category_day_panel",
      "path": "data/processed/category_day_panel.parquet",
      "source_file_ids": ["file_order", "file_exposure", "file_activity"],
      "checksum": "sha256:..."
    }
  ],
  "latest_result": {
    "artifact_id": "result_001",
    "path": ".analysis/latest_result.json"
  }
}
```

## 5. Context Summary

路径：`workspaces/{project_id}/.analysis/context_summary.md`

给 Claude 读取的项目事实摘要。必须包含：
- 项目名称
- 当前阶段
- 数据文件状态
- 字段映射状态
- 已完成任务
- 最新 artifact
- 核心结论
- 待确认事项
- 下一步建议