## Why

Mock adapter 只能验证流程，无法真正利用 Claude 的推理能力。真实 Claude Agent SDK adapter 才能实现完整的 agent loop、session 持久化、streaming input mode 和 hooks/permissions 控制。这是系统从"骨架"到"可用的商业产品"的关键一步。

## What Changes

- **新增** `ClaudeAgentSDKAdapter` — 真实 Claude Agent SDK 集成
- **新增** in-process MCP server 注册 `business_analysis` 工具
- **新增** streaming input mode 配置
- **新增** session persistence（external_session_id 持久化）
- **新增** permission mode 配置（dontAsk / manual）
- **新增** hooks 配置（tool_call、session_start、execution_stop）
- **新增** `allow_builtin_read_tools` 配置项（可选开启 Read/Grep）
- **新增** 文档说明如何启用真实 adapter（环境变量、配置项）
- **保留** MockClaudeRuntimeAdapter 作为 fallback

## Capabilities

### New Capabilities
- `claude-agent-sdk-integration`: 真实 Claude Agent SDK 运行时接入

### Modified Capabilities
- `agent-message-runtime`: 替换 Mock 为真实 adapter 时 MessageRuntime 无需改动（接口一致）

## Impact

- **新建**: `backend/app/agent/claude_agent_sdk_adapter.py` — ClaudeAgentSDKAdapter
- **修改**: `backend/app/agent/claude_adapter.py` — 添加配置项说明
- **修改**: `config.py` — 添加 agent_runtime 配置
- **文档**: `CLAUDE.md` 或 `docs/CLAUDE_ADAPTER_SETUP.md` — 如何启用真实 SDK
- **测试**: 真实 adapter 集成测试（需要 ANTHROPIC_API_KEY）