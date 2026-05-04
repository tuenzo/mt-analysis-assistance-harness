## Tasks

### Phase 1: 数据校验 (data.validate)

- [ ] **T1.1** — 创建 `backend/app/analysis/pipelines/build_panel.py` — 数据校验部分
  ```python
  def validate_input_files(project_id: str) -> ValidationResult:
      # 检查 data/raw/ 下是否存在：
      # - order_info.csv（或 order_info_*.csv glob）
      # - exposure_info.csv
      # - activity_timeline.csv
      # 返回：
      {
          "ok": true/false,
          "files_found": ["order_info.csv"],
          "files_missing": ["exposure_info.csv"],
          "issues": [{"file": "order_info.csv", "issue": "missing date column"}]
      }
  ```
- [ ] **T1.2** — 创建 `validate_files()` 函数，读取 CSV header 检查必要字段
- [ ] **T1.3** — 在 `data_tools.py` 中接入 `validate_files()`

### Phase 2: Panel Build (panel.build_category_day)

- [ ] **T2.1** — 实现 `build_category_day_panel(project_id: str) -> PanelResult`
  ```python
  def build_category_day_panel(project_id: str) -> PanelResult:
      # 1. 读取 order_info.csv，按 date + category 聚合 GMV、discount、order_count、user_count
      # 2. 读取 exposure_info.csv，按 date + category 合并 exposure、exposure_rate
      # 3. 读取 activity_timeline.csv，标记 is_payday、is_activity、is_payday_activity
      # 4. 输出 data/processed/category_day_panel.parquet
      # 5. 注册 artifact type=panel
  ```
- [ ] **T2.2** — 注册 panel_tools.py 中的 `panel_build_category_day()`
- [ ] **T2.3** — 单元测试：`test_build_panel.py`

### Phase 3: Diagnostics (analysis.run_diagnostics)

- [ ] **T3.1** — 实现 `run_diagnostics(project_id: str) -> DiagnosticsResult`
  - GMV trend（按日期折线图数据）
  - activity vs non-activity 统计
  - payday overlap 分析
  - category concentration top10
- [ ] **T3.2** — 输出 JSON 结果到 `.analysis/diagnostics_result.json`
- [ ] **T3.3** — 注册到 analysis_tools.py

### Phase 4: LocalGap (analysis.run_localgap)

- [ ] **T4.1** — 实现 `run_localgap(project_id: str) -> LocalGapResult`
  ```python
  def run_localgap(project_id: str) -> LocalGapResult:
      # 1. 读取 category_day_panel.parquet
      # 2. 对于每个 category：
      #    - 非活动期均值作为 LocalBaseline
      #    - 活动期 LocalGap = actual_gmv - baseline
      #    - 分解：exposure_gap, discount_gap, payday_gap, interaction, residual
      # 3. 聚合 total gap by component
      # 4. 输出 localgap_total.png（堆叠柱状图）
      # 5. 输出 localgap_result.json
  ```
- [ ] **T4.2** — 注册到 analysis_tools.py

### Phase 5: PSM-DID (analysis.run_psm_did)

- [ ] **T5.1** — 实现简化版 `run_psm_did(project_id: str) -> PSMDIDResult`（第一版可先做简化，不支持复杂协变量）
- [ ] **T5.2** — 注册到 analysis_tools.py

### Phase 6: GPS-Uplift (analysis.run_gps_uplift) — Stub

- [ ] **T6.1** — 创建 stub 实现（返回 method_status="stub"，生成占位文件）
  ```python
  def run_gps_uplift(project_id: str) -> GPSResult:
      return GPSResult(
          ok=true,
          method_status="stub",
          summary="GPS-Uplift not yet implemented",
          artifacts=[],
          state_patch={}
      )
  ```
- [ ] **T6.2** — 标记后续需要完整实现

### Phase 7: Full Pipeline (analysis.run_full_pipeline)

- [ ] **T7.1** — 创建 `backend/app/analysis/pipelines/full_pipeline.py`
  ```python
  async def run_full_pipeline(project_id: str) -> AsyncIterator[dict]:
      steps = [
          ("data.validate", validate_input_files),
          ("panel.build_category_day", build_category_day_panel),
          ("analysis.run_diagnostics", run_diagnostics),
          ("analysis.run_localgap", run_localgap),
          ("analysis.run_gps_uplift", run_gps_uplift),
          ("chart.render", render_key_charts),
      ]
      for step_name, step_func in steps:
          yield {"step": step_name, "status": "started"}
          result = await step_func(project_id)
          yield {"step": step_name, "status": "finished", "result": result}
  ```
- [ ] **T7.2** — 注册到 analysis_tools.py

### Phase 8: Chart Render

- [ ] **T8.1** — 创建 `backend/app/analysis/chart_renderer.py`
  ```python
  def render_key_charts(project_id: str) -> list[Artifact]:
      # 读取 latest_result.json
      # 使用 matplotlib/plotly 生成：
      # - trend.png（GMV 时间序列）
      # - localgap_total.png（增量分解堆叠图）
      # - gps_dose_response.png（剂量响应曲线）
      # - uplift_curve.png（ uplift 曲线）
      # 保存到 artifacts/charts/
      # 注册 artifact
  ```
- [ ] **T8.2** — 注册到 chart_tools.py

### Phase 9: Job Orchestrator 接入

- [ ] **T9.1** — 创建 `backend/app/jobs/orchestrator.py`
  ```python
  class JobOrchestrator:
      def submit_job(self, project_id: str, action: str, input: dict) -> Job:
          # 创建 Job record (status: queued)
          # 放入 job queue（可用 asyncio queue 或简单 list）
          # 返回 job_id
  ```
- [ ] **T9.2** — 创建 `backend/app/jobs/runner.py`
  ```python
  class JobRunner:
      async def run(self, job_id: str):
          # 从 queue 取 job
          # 更新 status = running
          # 执行 action 对应的 pipeline
          # yield progress events
          # 更新 status = succeeded/failed
  ```

### Phase 10: 测试

- [ ] **T10.1** — `test_validate.py` — 缺少文件返回正确错误
- [ ] **T10.2** — `test_build_panel.py` — 生成 panel.parquet
- [ ] **T10.3** — `test_diagnostics.py` — 输出 trend 数据
- [ ] **T10.4** — `test_localgap.py` — 输出分解结果和图表
- [ ] **T10.5** — `test_full_pipeline.py` — 端到端测试
- [ ] **T10.6** — 运行所有测试，修复问题

---

## 验收标准

1. `data.validate` 正确检测三张表的存在性和字段
2. `panel.build_category_day` 生成 `.parquet` 文件和 type=panel artifact
3. `analysis.run_localgap` 输出分解图和 JSON 结果
4. `analysis.run_full_pipeline` 顺序执行所有步骤并发送 job 事件
5. chart.render 生成图表并注册为 artifact
6. GPS-Uplift stub 返回 method_status="stub"
7. 所有测试通过