## Overview

本变更实现统一工具网关。AnalysisToolGateway 是 `business_analysis` 工具的唯一执行入口，负责 action 校验、payload 验证、权限检查、审批路由、日志审计，然后分发到内部工具。

## Action Enum

16 个 action，分为 5 类：

**项目状态类**:
- `project.get_state` → READ_STATE (Level 0)

**数据操作类**:
- `data.ingest` → MODIFY_WORKSPACE (Level 3)
- `data.validate` → SAFE_COMPUTE (Level 1)
- `schema.infer` → READ_STATE (Level 0)
- `schema.apply_mapping` → MODIFY_WORKSPACE (Level 3)

**面板构建类**:
- `panel.build_category_day` → MODIFY_WORKSPACE (Level 3)

**分析类**:
- `analysis.run_diagnostics` → SAFE_COMPUTE (Level 1)
- `analysis.run_psm_did` → SAFE_COMPUTE (Level 1)
- `analysis.run_localgap` → SAFE_COMPUTE (Level 1)
- `analysis.run_gps_uplift` → SAFE_COMPUTE (Level 1)
- `analysis.run_full_pipeline` → MODIFY_WORKSPACE (Level 3)

**结果与可视化类**:
- `result.get_latest` → READ_STATE (Level 0)
- `artifact.read` → READ_STATE (Level 0)
- `chart.render` → WRITE_ARTIFACT (Level 2)
- `report.generate` → WRITE_ARTIFACT (Level 2)
- `memory.propose_update` → EXTERNAL_SYNC (Level 4)

## Gateway 执行流程

```
execute(tool_call_id, project_id, action, payload, reason)
  │
  ├─ 1. 校验 action 是有效枚举值（不是任意字符串）
  ├─ 2. 校验 payload 符合该 action 的 schema
  ├─ 3. 获取 required_permission_level
  ├─ 4. 检查当前用户/项目权限级别
  ├─ 5. 判断 risk_level：
  │     high_risk_actions = {memory.propose_update, analysis.run_full_pipeline}
  │     if action in high_risk_actions → 创建 ApprovalRequest，暂停
  ├─ 6. 记录 ToolCall(pending)
  ├─ 7. 写入 logs/tool_calls.jsonl
  ├─ 8. 执行工具函数或提交 Job
  ├─ 9. 记录 ToolCall(succeeded/failed)
  ├─ 10. 返回 ToolResult
```

## ToolResult 格式

```python
@dataclass
class ToolResult:
    ok: bool
    action: str
    summary: str
    artifacts: list[ArtifactRef] = field(default_factory=list)
    state_patch: dict = field(default_factory=dict)
    assistant_hint: str = ""
    error: ToolError | None = None

@dataclass
class ToolError:
    code: str  # VALIDATION_ERROR, PERMISSION_DENIED, PANEL_NOT_READY, ...
    message: str
    details: dict
```

## Permission Check

```python
def check_permission(level: int, action: BusinessAnalysisAction) -> bool:
    required = ACTION_PERMISSION_MAP[action]
    return level >= required
```

**高风险判断**：
- `analysis.run_full_pipeline` — 修改 workspace、运行多步分析
- `memory.propose_update` — 写入外部记忆
- `panel.build_category_day` — 覆盖中间结果

这些 action 触发审批流程，但不阻塞普通执行路径。

## Approval Flow

```
ToolCall (action=analysis.run_full_pipeline, status=waiting_approval)
  ↓
前端收到 approval_required 事件
  ↓
用户在 UI 审批（approve / reject）
  ↓
/api/approvals/{id}/approve → ToolCall(status=pending) + 继续执行
       reject → ToolCall(status=rejected) + tool_call_rejected event
```

## Tool Registry

```python
class ToolRegistry:
    _tools: dict[BusinessAnalysisAction, tuple[callable, int]]

    def register(self, action, func, permission_level):
        ...

    def get(self, action) -> tuple[callable, int] | None:
        ...

    def list_available(self) -> list[BusinessAnalysisAction]:
        ...
```

内部工具注册（应用启动时）：
```python
def register_all_tools(gateway: AnalysisToolGateway):
    registry = gateway.registry
    registry.register(BusinessAnalysisAction.DATA_VALIDATE, data_validate, Level.SAFE_COMPUTE)
    registry.register(BusinessAnalysisAction.PANEL_BUILD_CATEGORY_DAY, panel_build, Level.MODIFY_WORKSPACE)
    ...
```

## 日志格式

`logs/tool_calls.jsonl` 每行：
```json
{"timestamp": "2026-05-04T10:00:00Z", "tool_call_id": "tc_001", "action": "data.validate", "payload_hash": "sha256:xxx", "status": "succeeded", "duration_ms": 234}
```