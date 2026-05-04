## Tasks

### Phase 1: Report Generation (report.generate)

- [ ] **T1.1** — 创建 `backend/app/reports/renderer.py`
  ```python
  def generate_report(project_id: str, template: str = "promo_analysis_default") -> ReportResult:
      # 1. 读取 .analysis/latest_result.json
      # 2. 读取 .analysis/diagnostics_result.json
      # 3. 读取 project_manifest.json
      # 4. 按 template 渲染 markdown
      # 模板 sections:
      #   - # 摘要
      #   - ## 数据说明
      #   - ## 分析流程
      #   - ## 核心结果（引用 artifact 图表）
      #   - ## 策略建议
      #   - ## 限制说明
      #   - ## 下周期建议
      # 5. 保存到 reports/report.md
      # 6. 注册 artifact type=report_source
  ```
- [ ] **T1.2** — 创建 `backend/app/reports/templates/promo_analysis_default.md`
- [ ] **T1.3** — 注册到 `report_tools.py`
- [ ] **T1.4** — 创建 `backend/app/reports/exporters.py`
  ```python
  def export_report(report_id: str, format: str) -> ExportResult:
      # format: "pdf" | "docx" | "tex"
      # pandoc 转换 或 python-docx/tex、反回路径
  ```
- [ ] **T1.5** — Reports API
  ```python
  @router.post("/projects/{project_id}/reports/generate")
  def generate_report(project_id: str, body: ReportGenerateRequest): ...

  @router.get("/projects/{project_id}/reports/latest")
  def get_latest_report(project_id: str): ...

  @router.post("/reports/{report_id}/export")
  def export_report(report_id: str, body: ReportExportRequest): ...
  ```

### Phase 2: Memory Bridge

- [ ] **T2.1** — 创建 `backend/app/memory/summarizer.py`
  ```python
  def generate_memory_candidate(project_id: str, scope: str) -> MemoryCandidate:
      # 从 latest_result.json + context_summary.md 生成摘要
      # scope: "project" | "user_preference" | "global_business_memory"
      # content 包括：
      #   - 项目核心结论（3-5 条）
      #   - 数据口径说明
      #   - 分析方法偏好
      #   - 策略模式（可选）
      #   - 不包含原始数据
  ```
- [ ] **T2.2** — 创建 `backend/app/memory/store.py`
  ```python
  def sync_to_project_memory(candidate_id: str):
      # approved scope=project → 写入 .analysis/memory_candidates.md

  def sync_to_global_memory(candidate_id: str):
      # approved scope=global_business_memory → 写入 .analysis/global_memory_export.md
      # 不要直接写 ~/.claude（除非配置 allow_global_memory_write=true）
  ```
- [ ] **T2.3** — 创建 `backend/app/memory/bridge.py`
  ```python
  class MemoryBridge:
      def propose_update(self, project_id: str, content: str, scope: str, source_artifact_ids: list[str]) -> MemoryCandidate
      def approve(self, candidate_id: str, scope: str) -> bool
      def reject(self, candidate_id: str) -> bool
  ```
- [ ] **T2.4** — 注册 `memory_tools.py` 中的 `memory_propose_update()`

### Phase 3: Memory API

- [ ] **T3.1** — 创建 `backend/app/api/memory.py`
  ```python
  @router.get("/projects/{project_id}/memory/candidates")
  def list_memory_candidates(project_id: str): ...

  @router.post("/memory/candidates/{candidate_id}/approve")
  def approve_memory_candidate(candidate_id: str, body: ApproveRequest): ...

  @router.post("/memory/candidates/{candidate_id}/reject")
  def reject_memory_candidate(candidate_id: str): ...
  ```

### Phase 4: 工具调用集成

- [ ] **T4.1** — `report.generate` 接入 ReportService
- [ ] **T4.2** — `memory.propose_update` 接入 MemoryBridge
- [ ] **T4.3** — AnalysisToolGateway 处理这两个 action

### Phase 5: 测试

- [ ] **T5.1** — `test_report_generation.py` — 生成 report.md 并包含正确 sections
- [ ] **T5.2** — `test_memory_propose.py` — 生成 memory candidate
- [ ] **T5.3** — `test_memory_approve_reject.py` — approve 写入 memory store，reject 保持 pending
- [ ] **T5.4** — `test_global_memory_boundary.py` — 验证不直接写 ~/.claude
- [ ] **T5.5** — 运行所有测试，修复问题

---

## 验收标准

1. `report.generate` 生成包含摘要、数据说明、结果、策略、限制的 markdown 报告
2. 报告引用 artifact 图表（使用相对路径）
3. `memory.propose_update` 生成结构化 memory candidate（不包含原始数据）
4. approve 后 scope=project 写入 `.analysis/memory_candidates.md`
5. approve 后 scope=global 写入 `.analysis/global_memory_export.md`（不直接写 ~/.claude）
6. reject 后 candidate 保持 pending 状态
7. 所有测试通过