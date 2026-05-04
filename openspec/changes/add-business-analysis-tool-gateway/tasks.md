## Tasks

### Phase 1: Action Enum & Schemas

- [ ] **T1.1** — 创建 `backend/app/tools/schemas.py`
  ```python
  class BusinessAnalysisAction(str, Enum):
      PROJECT_GET_STATE = "project.get_state"
      DATA_INGEST = "data.ingest"
      DATA_VALIDATE = "data.validate"
      SCHEMA_INFER = "schema.infer"
      SCHEMA_APPLY_MAPPING = "schema.apply_mapping"
      PANEL_BUILD_CATEGORY_DAY = "panel.build_category_day"
      ANALYSIS_RUN_DIAGNOSTICS = "analysis.run_diagnostics"
      ANALYSIS_RUN_PSM_DID = "analysis.run_psm_did"
      ANALYSIS_RUN_LOCALGAP = "analysis.run_localgap"
      ANALYSIS_RUN_GPS_UPLIFT = "analysis.run_gps_uplift"
      ANALYSIS_RUN_FULL_PIPELINE = "analysis.run_full_pipeline"
      RESULT_GET_LATEST = "result.get_latest"
      ARTIFACT_READ = "artifact.read"
      CHART_RENDER = "chart.render"
      REPORT_GENERATE = "report.generate"
      MEMORY_PROPOSE_UPDATE = "memory.propose_update"
  ```
- [ ] **T1.2** — 定义每种 action 的 payload schema（如 `data.validate` 需要 `{}`，`analysis.run_localgap` 可能需要 `{"category_filter": [...]}`）

### Phase 2: Tool Registry

- [ ] **T2.1** — 创建 `backend/app/tools/registry.py`
  ```python
  class ToolRegistry:
      def __init__(self):
          self._tools: dict[BusinessAnalysisAction, callable] = {}

      def register(self, action: BusinessAnalysisAction, func: callable, permission_level: int):
          self._tools[action] = (func, permission_level)

      def get_tool(self, action: BusinessAnalysisAction) -> tuple[callable, int] | None:
          return self._tools.get(action)

      def list_actions(self) -> list[BusinessAnalysisAction]:
          return list(self._tools.keys())
  ```
- [ ] **T2.2** — 创建内部工具注册函数 `register_all_tools()`，在应用启动时调用

### Phase 3: Analysis Tool Gateway

- [ ] **T3.1** — 创建 `backend/app/tools/gateway.py`
  ```python
  class AnalysisToolGateway:
      def __init__(self, registry: ToolRegistry, session_store: SessionStore):
          self.registry = registry
          self.session_store = session_store

      def execute(self, tool_call_id: str, project_id: str, action: BusinessAnalysisAction, payload: dict, reason: str) -> ToolResult:
          # 1. 校验 action enum（不是任意字符串）
          # 2. 校验 payload schema（pydantic 验证）
          # 3. 获取 permission level 并校验
          # 4. 判断是否需要 ApprovalRequest（Level >= 3 或 high risk action）
          # 5. 记录 ToolCall 到数据库
          # 6. 写入 logs/tool_calls.jsonl
          # 7. 执行工具函数或创建 Job
          # 8. 返回 ToolResult {ok, action, summary, artifacts, state_patch, assistant_hint}
  ```

### Phase 4: Permission System

- [ ] **T4.1** — 创建 `backend/app/core/permissions.py`
  ```python
  class PermissionLevel(IntEnum):
      READ_STATE = 0
      SAFE_COMPUTE = 1
      WRITE_ARTIFACT = 2
      MODIFY_WORKSPACE = 3
      EXTERNAL_SYNC = 4

  def check_permission(user_level: int, required_level: int) -> bool: ...

  def action_to_permission_level(action: BusinessAnalysisAction) -> int:
      # mapping 如：
      # project.get_state → READ_STATE
      # data.validate → SAFE_COMPUTE
      # panel.build_category_day → MODIFY_WORKSPACE
      # report.generate → WRITE_ARTIFACT
      # memory.propose_update → EXTERNAL_SYNC
  ```
- [ ] **T4.2** — ApprovalRequest 高风险判断：
  ```python
  HIGH_RISK_ACTIONS = {"panel.build_category_day", "analysis.run_full_pipeline", "memory.propose_update"}
  RISK_LEVEL_MAP = {"memory.propose_update": "high", "data.validate": "low", ...}
  ```

### Phase 5: Approval API

- [ ] **T5.1** — 创建 `backend/app/api/approvals.py`
  ```python
  @router.post("/approvals/{approval_id}/approve")
  def approve_tool_call(approval_id: str):
      # 更新 ApprovalRequest.status = "approved"
      # 继续执行 tool_call（resume）

  @router.post("/approvals/{approval_id}/reject")
  def reject_tool_call(approval_id: str):
      # 更新 ApprovalRequest.status = "rejected"
      # ToolCall.status = "rejected"
      # yield tool_call_rejected event
  ```

### Phase 6: 内部工具实现（Stub）

- [ ] **T6.1** — 创建 `backend/app/tools/project_tools.py`
  ```python
  def project_get_state(project_id: str, payload: dict) -> ToolResult:
      # 读取 project_manifest.json，返回当前状态摘要
  ```
- [ ] **T6.2** — 创建 `backend/app/tools/data_tools.py`（stub）
  ```python
  def data_ingest(project_id: str, payload: dict) -> ToolResult: ...
  def data_validate(project_id: str, payload: dict) -> ToolResult: ...
  def schema_infer(project_id: str, payload: dict) -> ToolResult: ...
  def schema_apply_mapping(project_id: str, payload: dict) -> ToolResult: ...
  ```
- [ ] **T6.3** — 创建其余 stub：`panel_tools.py`, `analysis_tools.py`, `chart_tools.py`, `report_tools.py`, `memory_tools.py`（每个只返回 `ToolResult(ok=true, summary="stub")`）

### Phase 7: Message Runtime 接入

- [ ] **T7.1** — 修改 `message_runtime.py`：tool_call_started 事件触发 `AnalysisToolGateway.execute()`
- [ ] **T7.2** — tool result 转为 `tool_call_finished` / `tool_call_failed` 事件并 SSE 推送

### Phase 8: 测试

- [ ] **T8.1** — `test_action_enum.py` — action 只能是 enum 值
- [ ] **T8.2** — `test_payload_validation.py` — 无效 payload 被拒绝
- [ ] **T8.3** — `test_permission_check.py` — 权限不足返回错误
- [ ] **T8.4** — `test_tool_call_logging.py` — tool_calls.jsonl 有记录
- [ ] **T8.5** — `test_approval_flow.py` — 高风险 action 创建 ApprovalRequest
- [ ] **T8.6** — 运行所有测试，修复问题

---

## 验收标准

1. 无效 action 字符串被拒绝（400 错误）
2. 无效 payload schema 被拒绝
3. 权限不足时返回 `ToolResult(ok=false, error="permission denied")`
4. 每个 tool call 写入 `logs/tool_calls.jsonl`
5. 高风险 action 创建 ApprovalRequest 并暂停执行
6. approve 后继续执行，reject 后返回 tool_call_rejected 事件
7. 所有测试通过