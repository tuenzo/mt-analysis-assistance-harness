## Tasks

### Phase 1: Memory 模型扩展

- [ ] **T1.1** — 扩展 `backend/app/memory/models.py`
  ```python
  class MemoryScope(str, Enum):
      PROJECT = "project"
      USER_PREFERENCE = "user_preference"
      GLOBAL_BUSINESS_MEMORY = "global_business_memory"

  class MemoryCategory(str, Enum):
      CONCLUSION = "conclusion"
      PREFERENCE = "preference"
      METHODOLOGY = "methodology"
      DATA_CALIBRATION = "data_calibration"

  class MemoryCandidate(Base):
      __tablename__ = "memory_candidates"
      id: Mapped[str]
      project_id: Mapped[str]
      scope: Mapped[MemoryScope]
      category: MemoryCategory
      content: Mapped[str]
      source_artifact_ids: Mapped[list[str]] = mapped_column(JSON, default=list)
      status: Mapped[str] = mapped_column(String, default="pending")
      approved_at: Mapped[datetime | None]
      rejected_at: Mapped[datetime | None]
      created_at: Mapped[datetime]
  ```

### Phase 2: MemorySyncService

- [ ] **T2.1** — 创建 `backend/app/memory/sync.py`
  ```python
  class MemorySyncService:
      def sync_to_project_memory(self, candidate: MemoryCandidate) -> str
      def export_for_global_memory(self, candidate: MemoryCandidate) -> str
      def get_project_memory(self, project_id: str) -> list[MemoryCandidate]
  ```

- [ ] **T2.2** — `.analysis/memory_candidates.md` 格式：
  ```markdown
  ## 项目记忆

  ### {created_at} | scope={scope} | category={category}
  {content}
  ```

- [ ] **T2.3** — `.analysis/global_memory_export.md` 格式（供用户手动同步到全局记忆）

### Phase 3: 候选生成策略

- [ ] **T3.1** — 创建 `backend/app/memory/generator.py`
  ```python
  class MemoryCandidateGenerator:
      def generate_from_result(self, project_id: str, result: LatestResult) -> list[MemoryCandidate]
      def _generate_project_summary(self, project_id, result) -> MemoryCandidate
      def _generate_strategy_insights(self, project_id, result) -> list[MemoryCandidate]
      def _generate_data_calibration(self, project_id, result) -> list[MemoryCandidate]
  ```

- [ ] **T3.2** — `full_pipeline.py` 末尾调用 `MemoryCandidateGenerator.generate_from_result()`

### Phase 4: Memory API 扩展

- [ ] **T4.1** — 扩展 `backend/app/api/memory.py`
  ```python
  @router.get("/projects/{project_id}/memory/candidates")
  def list_candidates(project_id: str, scope: MemoryScope | None, status: str | None)

  @router.get("/memory/candidates/{candidate_id}")
  def get_candidate(candidate_id: str)

  @router.post("/memory/candidates/{candidate_id}/approve")
  def approve_candidate(candidate_id: str, body: ApproveRequest)

  @router.post("/memory/candidates/{candidate_id}/reject")
  def reject_candidate(candidate_id: str)

  @router.post("/projects/{project_id}/memory/generate-candidates")
  def generate_candidates(project_id: str)
  ```

- [ ] **T4.2** — `approve` 处理逻辑：
  - 更新 status=approved，approved_at=now
  - 调用 MemorySyncService.sync_to_project_memory() 或 export_for_global_memory()

### Phase 5: 测试

- [ ] **T5.1** — `test_memory_sync.py` — sync_to_project_memory、export_for_global_memory 测试
- [ ] **T5.2** — `test_memory_generator.py` — 候选生成测试（无原始数据）
- [ ] **T5.3** — `test_memory_api.py` — approve/reject API 测试

---

## 验收标准

1. `GET /api/projects/{project_id}/memory/candidates?status=pending` 返回待确认列表
2. approve 后 status=approved，文件已写入
3. reject 后 status=rejected
4. pipeline 完成后自动生成 3+ 个候选
5. 候选内容无原始数据
6. 所有测试通过
