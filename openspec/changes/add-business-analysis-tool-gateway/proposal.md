## Why

business_analysis 是系统唯一对外暴露的工具。所有 Claude 对工具的调用都经过 AnalysisToolGateway，必须在此做 action 校验、payload 校验、permission check、审批判断、审计日志，然后分发到内部工具。没有 tool gateway 就没有安全的工具执行。

## What Changes

- **新增** `BusinessAnalysisAction` enum（16 个 action）
- **新增** `AnalysisToolGateway` — 统一入口，校验 + 路由 + 审计
- **新增** `ToolRegistry` — 内部工具注册表
- **新增** `ToolCall` 表记录（payload、status、result、approval_request_id）
- **新增** `ApprovalRequest` 表 + `/api/approvals/{id}/approve|reject`
- **新增** 内部工具实现：project_tools、data_tools、panel_tools、analysis_tools、chart_tools、report_tools、memory_tools
- **新增** Level 0-4 权限校验逻辑
- **新增** `/api/agent/approvals/{approval_id}/approve|reject`

## Capabilities

### New Capabilities
- `tool-gateway`: 统一工具网关、action 校验、权限控制
- `permission-system`: Level 0-4 权限等级、高风险操作审批

### Modified Capabilities
- 无

## Impact

- **新建**: `backend/app/tools/gateway.py` — AnalysisToolGateway
- **新建**: `backend/app/tools/registry.py` — ToolRegistry
- **新建**: `backend/app/tools/schemas.py` — action enum、payload schemas
- **新建**: `backend/app/tools/project_tools.py` — project.get_state, artifact.read
- **新建**: `backend/app/tools/data_tools.py` — data.ingest, data.validate, schema.infer, schema.apply_mapping
- **新建**: `backend/app/tools/panel_tools.py` — panel.build_category_day
- **新建**: `backend/app/tools/analysis_tools.py` — analysis.run_* 系列
- **新建**: `backend/app/tools/chart_tools.py` — chart.render
- **新建**: `backend/app/tools/report_tools.py` — report.generate
- **新建**: `backend/app/tools/memory_tools.py` — memory.propose_update
- **修改**: `backend/app/api/agent_messages.py` — 接入 AnalysisToolGateway
- **测试**: action 校验测试、权限测试、tool call 日志测试