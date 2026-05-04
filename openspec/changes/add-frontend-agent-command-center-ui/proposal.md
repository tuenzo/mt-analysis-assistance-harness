## Why

Agent Command Center 是系统的唯一自然语言交互入口。根据 spec.md P1，所有用户输入必须先进入统一消息入口 `POST /api/agent/messages`，Agent Command Center 必须展示完整的交互过程：assistant message、tool call、approval 请求、artifact 创建、run status。没有这个页面，MVP 0 的验收标准"前端显示事件"无法达成。

## What Changes

- **新增** `MessageList` 组件 — 展示对话历史（user message、assistant message delta、final answer）
- **新增** `MessageInput` 组件 — 用户输入框，支持 Enter 发送、Shift+Enter 换行
- **新增** `ToolCallItem` 组件 — 展示 tool call 详情（action、payload、status）
- **新增** `ApprovalBanner` 组件 — 高风险操作需要用户审批
- **新增** `JobProgressIndicator` 组件 — 展示 job 进度（data.validate → panel → diagnostics → ... → report）
- **新增** `ArtifactCreatedToast` — artifact 创建时的 toast 提示
- **新增** `AgentPage` 页面 — `/projects/[project_id]/agent`
- **新增** SSE 事件驱动的状态更新逻辑

## Capabilities

### New Capabilities
- `agent-command-center-ui`: 完整的消息交互界面

### Modified Capabilities
- `frontend-skeleton`: 扩展 agent-store 的事件处理（新增 tool_call、approval、job 相关状态）

## Impact

- **新建**: `frontend/src/features/agent/message-list.tsx`
- **新建**: `frontend/src/features/agent/message-input.tsx`
- **新建**: `frontend/src/features/agent/tool-call-item.tsx`
- **新建**: `frontend/src/features/agent/approval-banner.tsx`
- **新建**: `frontend/src/features/agent/job-progress-indicator.tsx`
- **新建**: `frontend/src/features/agent/agent-page.tsx`
- **修改**: `frontend/src/store/agent-store.ts` — 新增 tool_calls、approvals、jobs 状态
- **测试**: Agent Command Center smoke test
