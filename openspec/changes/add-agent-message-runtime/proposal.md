## Why

Message-first 架构的核心是统一消息入口 `POST /api/agent/messages`。Claude 无法直接调用内部工具，需要通过 MessageRuntime 接收用户消息、调用 Claude Adapter（mock 或真实 SDK）、接收事件流并转发给前端。没有 message runtime 就没有真正的 agent loop。

## What Changes

- **新增** `POST /api/agent/messages` — 统一消息入口，创建 AgentTurn，调用 Claude Adapter
- **新增** `GET /api/agent/sessions/{session_id}/events` — SSE 事件流
- **新增** `POST /api/agent/sessions/{session_id}/interrupt` — 中断 session
- **新增** `AnalysisSession`, `AgentTurn`, `AgentEvent` 表的 CRUD 操作
- **新增** `MockClaudeRuntimeAdapter` — 返回模拟响应 + 触发 tool call 事件
- **新增** `PromptComposer` — 构造发送给 Claude 的 prompt（包含项目状态、可用 actions）
- **新增** `ContextBuilder` — 构建 message context envelope

## Capabilities

### New Capabilities
- `agent-message-runtime`: 统一消息循环、SSE 事件流、会话管理
- `mock-claude-adapter`: MVP 阶段 Mock 实现，供前端调试和验证流程

### Modified Capabilities
- 无

## Impact

- **新建**: `backend/app/agent/message_runtime.py` — MessageRuntime 主循环
- **新建**: `backend/app/agent/claude_adapter.py` — ClaudeRuntimeAdapter 接口 + MockClaudeRuntimeAdapter
- **新建**: `backend/app/agent/context_builder.py` — ContextBuilder
- **新建**: `backend/app/agent/prompt_composer.py` — PromptComposer
- **新建**: `backend/app/agent/session_store.py` — SessionStore
- **新建**: `backend/app/agent/event_mapper.py` — EventMapper
- **新建**: `backend/app/api/agent_messages.py` — Agent Messages API
- **测试**: message loop 测试、SSE 流测试、mock adapter 测试