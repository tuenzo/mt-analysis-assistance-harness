## Tasks

### Phase 1: Report 数据模型

- [ ] **T1.1** — 扩展 `backend/app/reports/models.py`
  ```python
  class ReportType(str, Enum):
      PROMO_ANALYSIS = "promo_analysis"
      EXECUTIVE_SUMMARY = "executive_summary"

  class Report(Base):
      __tablename__ = "reports"
      id: Mapped[str] = mapped_column(String, primary_key=True)
      project_id: Mapped[str] = mapped_column(String, ForeignKey("projects.id"))
      report_type: Mapped[ReportType]
      template_name: Mapped[str] = mapped_column(String, default="promo_analysis_default")
      title: Mapped[str]
      content_md: Mapped[str]
      file_path: Mapped[str]
      exported_path: Mapped[str | None]
      metadata_json: Mapped[dict] = mapped_column(JSON, default=dict)
      created_by_job_id: Mapped[str | None] = mapped_column(String, ForeignKey("jobs.id"))
      created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
  ```

### Phase 2: Report Template

- [ ] **T2.1** — 创建 `backend/app/reports/templates/promo_analysis_default.md`
  - 包含摘要、数据说明、分析方法、核心结果、策略建议、限制说明、下周期建议
  - 占位符使用 `{}` 格式（如 `{project_name}`）

### Phase 3: ReportRenderer

- [ ] **T3.1** — 创建 `backend/app/reports/renderer.py`
  ```python
  class ReportRenderer:
      def __init__(self, template_name: str = "promo_analysis_default")
      def render(self, project_id: str, result: LatestResult) -> str
      def _load_template(self, name: str) -> str
      def _build_context(self, project_id: str, result: LatestResult) -> dict
  ```

- [ ] **T3.2** — `_build_context` 需要：
  - 从 project_manifest 获取 project_name
  - 从 latest_result 获取 date_range、data_summary
  - 从 ArtifactService 获取图表路径
  - 从 gps_result 获取 strategy_matrix

### Phase 4: Exporter

- [ ] **T4.1** — 创建 `backend/app/reports/exporters.py`
  ```python
  class Exporter:
      @staticmethod
      def to_pdf(markdown_path: str, output_path: str) -> str:
          # 使用 markdown + weasyprint
          # 返回 output_path
  ```

- [ ] **T4.2** — 添加 `weasyprint` 到 `requirements.txt`

### Phase 5: ReportService

- [ ] **T5.1** — 创建 `backend/app/reports/service.py`
  ```python
  class ReportService:
      def generate(self, project_id: str, report_type: ReportType, template_name: str, result: LatestResult) -> Report
      def get_latest(self, project_id: str) -> Report | None
      def list_by_project(self, project_id: str) -> list[Report]
      def export(self, report_id: str, format: str = "pdf") -> Report
  ```

- [ ] **T5.2** — 生成报告后注册为 artifact（type=report_source）

### Phase 6: Reports API

- [ ] **T6.1** — 创建 `backend/app/api/reports.py`
  ```python
  @router.post("/projects/{project_id}/reports/generate")
  def generate_report(project_id: str, body: ReportGenerateRequest)

  @router.get("/projects/{project_id}/reports")
  def list_reports(project_id: str)

  @router.get("/projects/{project_id}/reports/latest")
  def get_latest_report(project_id: str)

  @router.get("/reports/{report_id}")
  def get_report(report_id: str)

  @router.post("/reports/{report_id}/export")
  def export_report(report_id: str, body: ReportExportRequest)

  @router.get("/reports/{report_id}/download")
  def download_report(report_id: str, format: str = "md")
  ```

- [ ] **T6.2** — 注册到 `main.py`

### Phase 7: Pipeline 集成

- [ ] **T7.1** — 修改 `full_pipeline.py`：末尾调用 `ReportService.generate()`

### Phase 8: 测试

- [ ] **T8.1** — `test_report_renderer.py` — 渲染占位符填充测试
- [ ] **T8.2** — `test_report_service.py` — generate、export 测试
- [ ] **T8.3** — `test_reports_api.py` — API 测试

---

## 验收标准

1. `POST /api/projects/{project_id}/reports/generate` 返回报告内容
2. 报告 markdown 包含所有 sections
3. 图表引用路径正确（通过 ArtifactService）
4. PDF 导出生成文件
5. 所有测试通过
