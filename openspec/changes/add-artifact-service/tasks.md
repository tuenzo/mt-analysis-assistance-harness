## Tasks

### Phase 1: Artifact 数据模型

- [ ] **T1.1** — 扩展 `backend/app/projects/models.py` 中的 Artifact model
  ```python
  class ArtifactType(str, Enum):
      CHART = "chart"
      TABLE = "table"
      MODEL_OUTPUT = "model_output"
      REPORT_SOURCE = "report_source"
      VALIDATION_REPORT = "validation_report"

  class Artifact(Base):
      __tablename__ = "artifacts"
      id: Mapped[str] = mapped_column(String, primary_key=True)
      project_id: Mapped[str] = mapped_column(String, ForeignKey("projects.id"))
      artifact_type: Mapped[ArtifactType]
      name: Mapped[str]
      version: Mapped[int] = mapped_column(Integer, default=1)
      file_path: Mapped[str]
      checksum: Mapped[str]
      tags: Mapped[list[str]] = mapped_column(JSON, default=list)
      metadata_json: Mapped[dict] = mapped_column(JSON, default=dict)
      created_by_job_id: Mapped[str | None] = mapped_column(String, ForeignKey("jobs.id"))
      created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
      latest_version: Mapped[bool] = mapped_column(Boolean, default=True)
  ```

- [ ] **T1.2** — 创建 `backend/app/artifacts/models.py`（从 projects/models.py 分离）

### Phase 2: ArtifactService

- [ ] **T2.1** — 创建 `backend/app/artifacts/service.py`
  ```python
  class ArtifactService:
      def register(self, project_id, artifact_type, name, file_path, tags, metadata, created_by_job_id=None) -> Artifact
      def get(self, artifact_id: str) -> Artifact
      def get_latest(self, project_id: str, name: str) -> Artifact | None
      def list_by_project(self, project_id, artifact_type=None, tags=None) -> list[Artifact]
      def list_versions(self, project_id: str, name: str) -> list[Artifact]
      def delete(self, artifact_id: str) -> None
      def compute_checksum(self, file_path: str) -> str
  ```

- [ ] **T2.2** — version 递增逻辑：注册时检查同名 artifact，设置旧版 latest_version=False

- [ ] **T2.3** — file_path 验证：确保文件存在且在 workspace 内（安全检查）

### Phase 3: Artifacts API

- [ ] **T3.1** — 创建 `backend/app/api/artifacts.py`
  ```python
  @router.get("/projects/{project_id}/artifacts")
  def list_artifacts(project_id: str, type: ArtifactType | None = None, tags: str | None = None)

  @router.get("/artifacts/{artifact_id}")
  def get_artifact(artifact_id: str)

  @router.get("/artifacts/{artifact_id}/download")
  def download_artifact(artifact_id: str)

  @router.get("/projects/{project_id}/artifacts/{name}/versions")
  def list_artifact_versions(project_id: str, name: str)

  @router.delete("/artifacts/{artifact_id}")
  def delete_artifact(artifact_id: str)
  ```

- [ ] **T3.2** — 注册到 `main.py` 的 `app.include_router(router)`

### Phase 4: Pipeline 集成

- [ ] **T4.1** — 修改 `full_pipeline.py`：diagnostics 完成后注册图表 artifact
- [ ] **T4.2** — 修改 `full_pipeline.py`：localgap 完成后注册 localgap_total artifact
- [ ] **T4.3** — 修改 `full_pipeline.py`：gps 完成后注册 gps_dose_response artifact
- [ ] **T4.4** — 修改 `full_pipeline.py`：data.validate 完成后注册 validation_report artifact

### Phase 5: Report 集成

- [ ] **T5.1** — 修改 `ReportRenderer`：通过 ArtifactService.get_latest 获取图表路径
- [ ] **T5.2** — 报告生成后注册 report artifact

### Phase 6: 测试

- [ ] **T6.1** — `test_artifact_service.py` — register、get_latest、version 递增测试
- [ ] **T6.2** — `test_artifacts_api.py` — CRUD API 测试
- [ ] **T6.3** — `test_pipeline_artifact_registration.py` — pipeline 完成后 artifact 已注册

---

## 验收标准

1. `ArtifactService.register()` 后数据库有记录，version=1
2. 同一 name 再次 register，version=2，旧版 latest_version=False
3. `GET /api/projects/{project_id}/artifacts?type=chart` 返回图表列表
4. `GET /api/artifacts/{artifact_id}/download` 返回文件流
5. pipeline 完成后 `artifacts` 表有对应记录
6. 所有测试通过
