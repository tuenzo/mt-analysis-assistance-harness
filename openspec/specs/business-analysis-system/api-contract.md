---
name: api-contract
description: API 契约文档 - 所有端点请求/响应格式、事件流格式
type: spec
parent: business-analysis-system
---

# API 契约文档

## 1. 通用响应格式

### 成功

```json
{
  "ok": true,
  "data": {},
  "error": null
}
```

### 失败

```json
{
  "ok": false,
  "data": null,
  "error": {
    "code": "VALIDATION_ERROR",
    "message": "Invalid file role.",
    "details": {}
  }
}
```

## 2. Projects API

### 创建项目

```
POST /api/projects
```

**Request**:
```json
{
  "name": "Keemart Payday Promotion",
  "description": "周期性促销效果评估",
  "domain": "promo_analysis"
}
```

**Response** (200):
```json
{
  "ok": true,
  "data": {
    "id": "proj_001",
    "name": "Keemart Payday Promotion",
    "workspace_path": "workspaces/proj_001",
    "status": "created",
    "current_stage": "created"
  }
}
```

### 获取项目

```
GET /api/projects/{project_id}
```

### 获取项目状态

```
GET /api/projects/{project_id}/state
```

**Response** (200):
```json
{
  "ok": true,
  "data": {
    "project": {},
    "files": [],
    "latest_session": {},
    "latest_jobs": [],
    "latest_artifacts": [],
    "latest_report": {},
    "memory_candidates_count": 0,
    "next_actions": ["upload_required_files", "validate_data"]
  }
}
```

## 3. Files API

### 上传文件

```
POST /api/projects/{project_id}/files
Content-Type: multipart/form-data
```

**Form fields**:
- `file`: binary (required)
- `role`: order_info | exposure_info | activity_timeline | unknown

**Response** (200):
```json
{
  "ok": true,
  "data": {
    "file_id": "file_001",
    "role": "order_info",
    "original_name": "order_info.csv",
    "status": "uploaded",
    "checksum": "sha256:..."
  }
}
```

### 自动识别 schema

```
POST /api/projects/{project_id}/files/infer-schema
```

**Response** (200):
```json
{
  "ok": true,
  "data": {
    "files": [
      {
        "file_id": "file_001",
        "role_guess": "order_info",
        "columns": [
          {
            "name": "order_id",
            "dtype": "string",
            "mapped_to": "order_id",
            "confidence": 0.98
          }
        ]
      }
    ]
  }
}
```

### 应用字段映射

```
POST /api/projects/{project_id}/schema/apply
```

**Request**:
```json
{
  "mappings": {
    "file_001": {
      "order_id": "order_id",
      "pay_time": "date",
      "gmv": "gmv",
      "discount": "discount_amount",
      "category": "category_name"
    }
  }
}
```

**Response** (200):
```json
{
  "ok": true,
  "data": {
    "status": "mapped"
  }
}
```

### 数据校验

```
POST /api/projects/{project_id}/files/validate
```

**Response** (200):
```json
{
  "ok": true,
  "data": {
    "job_id": "job_validate_001",
    "status": "queued"
  }
}
```

## 4. Agent Messages API

### 发送消息（统一消息入口）

```
POST /api/agent/messages
```

**Request**:
```json
{
  "project_id": "proj_001",
  "session_id": "sess_001",
  "message": "帮我分析这批 payday promotion 数据，并生成报告",
  "ui_context": {
    "active_view": "agent_command_center",
    "selected_artifact_id": null
  }
}
```

**Response** (200):
```json
{
  "ok": true,
  "data": {
    "turn_id": "turn_001",
    "session_id": "sess_001",
    "status": "running",
    "event_stream_url": "/api/agent/sessions/sess_001/events"
  }
}
```

### 事件流

```
GET /api/agent/sessions/{session_id}/events
Accept: text/event-stream
```

**Event examples**:

```json
{
  "type": "assistant_message_delta",
  "turn_id": "turn_001",
  "delta": "我会先检查数据完整性..."
}
```

```json
{
  "type": "tool_call_started",
  "turn_id": "turn_001",
  "tool": "business_analysis",
  "action": "data.validate"
}
```

```json
{
  "type": "artifact_created",
  "artifact_id": "art_001",
  "artifact_type": "validation_report",
  "title": "数据质量报告"
}
```

```json
{
  "type": "final_answer",
  "turn_id": "turn_001",
  "message": "分析已完成，核心结论是..."
}
```

### 中断 session

```
POST /api/agent/sessions/{session_id}/interrupt
```

## 5. Jobs API

### 创建 job

```
POST /api/projects/{project_id}/jobs
```

**Request**:
```json
{
  "action": "analysis.run_full_pipeline",
  "input": {
    "use_cached_panel": true
  }
}
```

**Response** (200):
```json
{
  "ok": true,
  "data": {
    "job_id": "job_001",
    "status": "queued"
  }
}
```

### 获取 job 状态

```
GET /api/jobs/{job_id}
```

**Response** (200):
```json
{
  "ok": true,
  "data": {
    "job_id": "job_001",
    "action": "analysis.run_full_pipeline",
    "status": "running",
    "progress": 0.45,
    "current_step": "analysis.run_localgap"
  }
}
```

## 6. Artifacts API

### 获取项目 artifacts

```
GET /api/projects/{project_id}/artifacts
```

**Query params**:
- `?type=chart`
- `?job_id=job_001`

**Response** (200):
```json
{
  "ok": true,
  "data": [
    {
      "id": "art_001",
      "type": "chart",
      "title": "活动期 LocalGap 总量分解",
      "path": "artifacts/charts/localgap_total.png",
      "created_at": "..."
    }
  ]
}
```

### 读取 artifact

```
GET /api/artifacts/{artifact_id}
```

## 7. Reports API

### 生成报告

```
POST /api/projects/{project_id}/reports/generate
```

**Request**:
```json
{
  "format": ["md", "pdf"],
  "template": "promo_analysis_default",
  "include_artifacts": true
}
```

**Response** (200):
```json
{
  "ok": true,
  "data": {
    "job_id": "job_report_001",
    "status": "queued"
  }
}
```

### 获取最新报告

```
GET /api/projects/{project_id}/reports/latest
```

### 导出报告

```
POST /api/reports/{report_id}/export
```

**Request**:
```json
{
  "format": "pdf"
}
```

## 8. Memory API

### 获取候选记忆

```
GET /api/projects/{project_id}/memory/candidates
```

### 审批候选记忆

```
POST /api/memory/candidates/{candidate_id}/approve
```

**Request**:
```json
{
  "scope": "global_business_memory"
}
```

### 拒绝候选记忆

```
POST /api/memory/candidates/{candidate_id}/reject
```

## 9. Approvals API

### 批准工具调用

```
POST /api/approvals/{approval_id}/approve
```

### 拒绝工具调用

```
POST /api/approvals/{approval_id}/reject
```

## 10. ToolResult 格式

business_analysis 工具调用返回格式：

**成功**:
```json
{
  "ok": true,
  "action": "analysis.run_localgap",
  "summary": "LocalGap analysis completed.",
  "artifacts": [
    {
      "artifact_id": "art_001",
      "type": "chart",
      "path": "artifacts/charts/localgap_total.png"
    }
  ],
  "state_patch": {
    "latest_stage": "localgap_done"
  },
  "assistant_hint": "You can now explain where the increment comes from."
}
```

**失败**:
```json
{
  "ok": false,
  "action": "analysis.run_localgap",
  "error": {
    "code": "PANEL_NOT_READY",
    "message": "category_day_panel.parquet not found. Run panel.build first.",
    "details": {}
  },
  "assistant_hint": "Run panel.build_category_day first."
}
```