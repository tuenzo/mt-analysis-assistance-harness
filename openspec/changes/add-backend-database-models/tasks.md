## Tasks

### Phase 1: 数据库基础

- [ ] **T1.1** — 创建 `backend/app/core/database.py`
  ```python
  from sqlalchemy import create_engine
  from sqlalchemy.orm import sessionmaker, declarative_base

  Base = declarative_base()

  def get_engine():
      return create_engine("sqlite:///./business_analysis.db")

  def get_session():
      return sessionmaker(bind=get_engine())()
  ```
- [ ] **T1.2** — 定义 12 张表 models（参考 `specs/business-analysis-system/data-model.md`）
  - Project, ProjectFile, AnalysisSession, AgentTurn, AgentEvent
  - ToolCall, Job, Artifact, Report, ApprovalRequest, MemoryCandidate, WorkspaceCheckpoint
- [ ] **T1.3** — 创建 `backend/app/projects/models.py` — 所有 models
- [ ] **T1.4** — 创建初始 migration 或 `Base.metadata.create_all()`

### Phase 2: Pydantic Schemas

- [ ] **T2.1** — 创建 `backend/app/projects/schemas.py`
  ```python
  # Project schemas
  class ProjectCreate(BaseModel): ...
  class ProjectResponse(BaseModel): ...
  class ProjectStateResponse(BaseModel): ...

  # File schemas
  class FileUploadResponse(BaseModel): ...
  class SchemaInferResponse(BaseModel): ...
  class FieldMappingRequest(BaseModel): ...
  ```
- [ ] **T2.2** — 创建 `backend/app/workspace/schemas.py`（如果需要）

### Phase 3: Project Service

- [ ] **T3.1** — 创建 `backend/app/projects/service.py`
  ```python
  class ProjectService:
      def create_project(self, name, domain) -> Project
      def get_project(self, project_id) -> Project
      def get_project_state(self, project_id) -> dict
      def list_projects(self) -> list[Project]
  ```
- [ ] **T3.2** — 联动：创建 project 时调用 `WorkspaceManager.create_workspace(project_id)`

### Phase 4: Projects API

- [ ] **T4.1** — 创建 `backend/app/api/projects.py`
  ```python
  @router.post("/projects")
  def create_project(body: ProjectCreate): ...

  @router.get("/projects")
  def list_projects(): ...

  @router.get("/projects/{project_id}")
  def get_project(project_id: str): ...

  @router.get("/projects/{project_id}/state")
  def get_project_state(project_id: str): ...
  ```
- [ ] **T4.2** — 注册到 `main.py` 的 `app.include_router(router)`

### Phase 5: Files API

- [ ] **T5.1** — 创建 `backend/app/api/files.py`
  ```python
  @router.post("/projects/{project_id}/files")
  def upload_file(project_id: str, file: UploadFile, role: str): ...

  @router.get("/projects/{project_id}/files")
  def list_files(project_id: str): ...

  @router.post("/projects/{project_id}/files/infer-schema")
  def infer_schema(project_id: str): ...

  @router.post("/projects/{project_id}/schema/apply")
  def apply_schema(project_id: str, body: FieldMappingRequest): ...
  ```
- [ ] **T5.2** — `upload_file` 需要：
  - 保存文件到 `workspace_path/data/raw/`
  - 计算 checksum
  - 创建 ProjectFile record
  - 更新 project_manifest
- [ ] **T5.3** — `infer_schema` 实现列名推断（读取 CSV header，匹配已知模式）
- [ ] **T5.4** — `apply_schema` 保存字段映射到 ProjectFile.schema_json

### Phase 6: FastAPI App 入口

- [ ] **T6.1** — 创建 `backend/app/main.py`
  ```python
  from fastapi import FastAPI
  from app.api import projects, files

  app = FastAPI()
  app.include_router(projects.router, prefix="/api")
  app.include_router(files.router, prefix="/api")
  ```
- [ ] **T6.2** — 添加 CORS、静态文件服务（SSE 前端测试用）

### Phase 7: 测试

- [ ] **T7.1** — `test_projects_api.py` — CRUD 测试
- [ ] **T7.2** — `test_files_api.py` — 上传、schema 推断测试
- [ ] **T7.3** — `test_project_workspace_linkage.py` — 创建 project 后 workspace 存在
- [ ] **T7.4** — 运行所有测试，修复问题

---

## 验收标准

1. `POST /api/projects` 能创建项目并同时创建 workspace 目录
2. `GET /api/projects/{project_id}/state` 返回完整状态
3. 上传文件后 `project_files` 表有记录，文件保存在 workspace 内
4. `infer-schema` 返回列信息
5. `apply-schema` 能保存字段映射
6. 所有测试通过