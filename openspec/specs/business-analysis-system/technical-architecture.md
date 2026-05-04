---
name: technical-architecture
description: 技术架构文档 - 后端模块结构、前端页面、技术选型
type: spec
parent: business-analysis-system
---

# 技术架构文档

## 1. 后端架构

```
backend/
  app/
    api/
      projects.py      # 项目 CRUD
      files.py         # 文件上传、schema 推断、字段映射
      agent_messages.py  # 统一消息入口
      jobs.py          # 任务创建与状态
      artifacts.py     # artifact 查询
      reports.py       # 报告生成与导出
      memory.py        # 记忆候选
      approvals.py     # 审批操作

    core/
      config.py        # 配置管理
      database.py      # 数据库连接
      auth.py          # 认证
      permissions.py   # 权限等级 (Level 0-4)
      events.py        # 事件类型定义
      errors.py        # 统一错误格式

    projects/
      models.py        # Project, ProjectFile ORM
      schemas.py       # Pydantic schemas
      service.py       # 业务逻辑

    workspace/
      manager.py       # WorkspaceManager
      manifest.py      # project_manifest.json 维护
      scanner.py       # 文件扫描、checksum
      checksums.py     # checksum 计算
      checkpoints.py   # workspace 快照
      context_summary.py  # context_summary.md 生成

    agent/
      message_runtime.py   # MessageRuntime
      claude_adapter.py    # ClaudeRuntimeAdapter
      context_builder.py   # ContextBuilder
      prompt_composer.py   # PromptComposer
      session_store.py     # SessionStore
      event_mapper.py      # EventMapper
      schemas.py           # Agent 相关 schema

    tools/
      gateway.py       # AnalysisToolGateway
      registry.py     # ToolRegistry
      schemas.py      # action enum、payload schema
      project_tools.py    # project.get_state, artifact.read
      data_tools.py       # data.ingest, data.validate, schema.infer, schema.apply_mapping
      panel_tools.py      # panel.build_category_day
      analysis_tools.py   # analysis.run_diagnostics, run_psm_did, run_localgap, run_gps_uplift, run_full_pipeline
      chart_tools.py      # chart.render
      report_tools.py     # report.generate
      memory_tools.py     # memory.propose_update

    jobs/
      orchestrator.py # JobOrchestrator
      runner.py       # JobRunner
      queue.py        # JobQueue
      status.py       # JobStatus

    analysis/
      pipelines/
        build_panel.py     # 品类×日期面板构建
        diagnostics.py     # 描述性诊断
        psm_did.py         # PSM-DID 因果推断
        localgap.py        # LocalGap 增量分解
        gps_uplift.py      # GPS-Uplift 剂量响应
        full_pipeline.py   # 完整 pipeline

    artifacts/
      service.py      # ArtifactService
      manifest.py     # artifact manifest

    reports/
      renderer.py     # 报告渲染
      exporters.py    # PDF/DOCX 导出
      templates/      # 报告模板

    memory/
      bridge.py       # MemoryBridge
      summarizer.py   # 记忆摘要生成
      store.py        # 记忆存储
```

## 2. 数据库模型

### 核心表

- **projects** — 项目基本信息、状态、当前阶段
- **project_files** — 上传文件记录、role、checksum、schema
- **analysis_sessions** — Claude SDK session 映射
- **agent_turns** — 每次用户消息的 turn
- **agent_events** — 事件流（user_message、tool_call、job_started 等）
- **tool_calls** — business_analysis 工具调用记录
- **jobs** — 长任务（panel build、full pipeline、report generation）
- **artifacts** — 图表、表格、模型结果、报告
- **reports** — 报告文件路径、状态
- **approval_requests** — 高风险操作审批
- **memory_candidates** — 记忆候选、审批状态
- **workspace_checkpoints** — workspace 快照

### Workspace Manifest

路径：`workspaces/{project_id}/.analysis/project_manifest.json`

管理文件事实状态：checksum、schema_hash、derived_assets。

### Context Summary

路径：`workspaces/{project_id}/.analysis/context_summary.md`

给 Claude 读取的项目事实摘要。

## 3. API 概览

### Projects
- `POST /api/projects` — 创建项目
- `GET /api/projects` — 列表
- `GET /api/projects/{project_id}` — 详情
- `GET /api/projects/{project_id}/state` — 项目状态（包含文件、session、jobs、artifacts、report、memory count、下一步建议）

### Files
- `POST /api/projects/{project_id}/files` — 上传文件
- `GET /api/projects/{project_id}/files` — 文件列表
- `POST /api/projects/{project_id}/files/infer-schema` — 自动识别 schema
- `POST /api/projects/{project_id}/schema/apply` — 应用字段映射
- `POST /api/projects/{project_id}/files/validate` — 数据校验

### Agent Messages
- `POST /api/agent/messages` — 统一消息入口
- `GET /api/agent/sessions/{session_id}/events` — SSE 事件流
- `POST /api/agent/sessions/{session_id}/interrupt` — 中断 session

### Jobs
- `POST /api/projects/{project_id}/jobs` — 创建 job
- `GET /api/projects/{project_id}/jobs` — 列表
- `GET /api/jobs/{job_id}` — 状态

### Artifacts
- `GET /api/projects/{project_id}/artifacts` — 查询
- `GET /api/artifacts/{artifact_id}` — 读取

### Reports
- `POST /api/projects/{project_id}/reports/generate` — 生成报告
- `GET /api/projects/{project_id}/reports/latest` — 最新报告
- `POST /api/reports/{report_id}/export` — 导出

### Memory
- `GET /api/projects/{project_id}/memory/candidates` — 候选列表
- `POST /api/memory/candidates/{candidate_id}/approve` — 批准
- `POST /api/memory/candidates/{candidate_id}/reject` — 拒绝

### Approvals
- `POST /api/approvals/{approval_id}/approve` — 批准工具调用
- `POST /api/approvals/{approval_id}/reject` — 拒绝工具调用

## 4. business_analysis 工具 Action Enum

```python
class BusinessAnalysisAction(str, Enum):
    # 项目状态
    PROJECT_GET_STATE = "project.get_state"
    
    # 数据操作
    DATA_INGEST = "data.ingest"
    DATA_VALIDATE = "data.validate"
    
    # Schema 操作
    SCHEMA_INFER = "schema.infer"
    SCHEMA_APPLY_MAPPING = "schema.apply_mapping"
    
    # 面板构建
    PANEL_BUILD_CATEGORY_DAY = "panel.build_category_day"
    
    # 分析
    ANALYSIS_RUN_DIAGNOSTICS = "analysis.run_diagnostics"
    ANALYSIS_RUN_PSM_DID = "analysis.run_psm_did"
    ANALYSIS_RUN_LOCALGAP = "analysis.run_localgap"
    ANALYSIS_RUN_GPS_UPLIFT = "analysis.run_gps_uplift"
    ANALYSIS_RUN_FULL_PIPELINE = "analysis.run_full_pipeline"
    
    # 结果与 artifact
    RESULT_GET_LATEST = "result.get_latest"
    ARTIFACT_READ = "artifact.read"
    
    # 可视化
    CHART_RENDER = "chart.render"
    
    # 报告
    REPORT_GENERATE = "report.generate"
    
    # 记忆
    MEMORY_PROPOSE_UPDATE = "memory.propose_update"
```

## 5. 事件类型 Enum

```python
class AgentEventType(str, Enum):
    USER_MESSAGE = "user_message"
    ASSISTANT_MESSAGE_DELTA = "assistant_message_delta"
    ASSISTANT_MESSAGE = "assistant_message"
    TOOL_CALL_STARTED = "tool_call_started"
    TOOL_CALL_FINISHED = "tool_call_finished"
    TOOL_CALL_FAILED = "tool_call_failed"
    JOB_STARTED = "job_started"
    JOB_PROGRESS = "job_progress"
    JOB_FINISHED = "job_finished"
    ARTIFACT_CREATED = "artifact_created"
    APPROVAL_REQUIRED = "approval_required"
    APPROVAL_RESOLVED = "approval_resolved"
    MEMORY_CANDIDATE_CREATED = "memory_candidate_created"
    REPORT_GENERATED = "report_generated"
    RUNTIME_ERROR = "runtime_error"
    FINAL_ANSWER = "final_answer"
```

## 6. 权限等级

```python
class PermissionLevel(IntEnum):
    READ_STATE = 0      # 读取项目状态、结果摘要、artifact
    SAFE_COMPUTE = 1    # 数据校验、字段识别、生成只读诊断
    WRITE_ARTIFACT = 2   # 生成图表、表格、报告草稿
    MODIFY_WORKSPACE = 3  # 写入脚本、覆盖中间结果、删除旧 artifact
    EXTERNAL_SYNC = 4   # 写入用户级 Claude memory、调用外部 API、导出到外部系统
```

## 7. 技术选型建议

- **后端**：FastAPI + SQLAlchemy + SQLite（MVP）
- **前端**：Vite + React（升级现有 demo）
- **运行时**：Claude Agent SDK（streaming input mode）
- **通信**：SSE for event stream
- **文件存储**：本地 workspace 目录

## 8. Claude Adapter 接口

```python
class ClaudeRuntimeAdapter(ABC):
    @abstractmethod
    def create_session(self, project_id: str) -> str:
        """创建 session，返回 external_session_id"""
        pass
    
    @abstractmethod
    def resume_session(self, session_id: str, project_id: str) -> None:
        """恢复已有 session"""
        pass
    
    @abstractmethod
    def send_message(self, session_id: str, message: str, context: dict) -> Generator[dict, None, None]:
        """发送消息，yield events"""
        pass
    
    @abstractmethod
    def interrupt(self, session_id: str) -> None:
        """中断当前运行"""
        pass


class MockClaudeRuntimeAdapter(ClaudeRuntimeAdapter):
    """Mock 实现，用于 MVP 阶段"""
    pass


class ClaudeAgentSDKAdapter(ClaudeRuntimeAdapter):
    """真实 Claude Agent SDK 接入"""
    pass
```