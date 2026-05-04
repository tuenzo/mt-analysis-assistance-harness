## Overview

Agent Command Center 是用户与 Claude Agent 交互的唯一入口。页面分为三区：消息列表区（左侧/中部）、工具调用详情区（右侧可折叠）、底部输入区。SSE 事件驱动实时更新。

## 页面布局

```
┌─────────────────────────────────────────────────────────────┐
│  Agent Command Center                    [Interrupt] [Clear] │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  ┌─────────────────────────────────┐  ┌──────────────────┐  │
│  │ MessageList                      │  │ ToolCallDetail   │  │
│  │                                  │  │ (可选展开)        │  │
│  │ [User Message]                   │  │                  │  │
│  │ [Assistant Delta...]             │  │ action: data.val │  │
│  │ [ToolCall: data.validate]        │  │ payload: {...}   │  │
│  │ [Job Progress: 3/7]              │  │ status: running  │  │
│  │ [Assistant Final Answer]         │  │ result: ok       │  │
│  │                                  │  │                  │  │
│  │ [Approval Banner]                │  └──────────────────┘  │
│  │ [Artifact Created: gmv_trend]    │                        │
│  │                                  │                        │
│  └─────────────────────────────────┘                        │
│                                                             │
├─────────────────────────────────────────────────────────────┤
│  [MessageInput: 输入自然语言...                    ] [Send] │
└─────────────────────────────────────────────────────────────┘
```

## 组件设计

### MessageList

```tsx
// 展示消息历史，按时间顺序
interface Message {
  id: string
  role: 'user' | 'assistant'
  content: string  // 完整回答或增量 delta
  delta?: string   // streaming delta（增量模式）
  toolCalls?: ToolCall[]
  status?: 'streaming' | 'done' | 'error'
}

function MessageList({ messages }: { messages: Message[] }) {
  // 自动滚动到底部（latest message）
  // user message 右对齐，assistant 左对齐
  // assistant message streaming 时显示 cursor 或 delta
  // tool call 显示为嵌套卡片
  // job progress 显示进度条
  // approval banner 突出显示
}
```

### ToolCallItem

```tsx
interface ToolCall {
  id: string
  action: string           // 'data.validate', 'analysis.run_localgap' 等
  payload: object          // action 对应的参数
  status: 'pending' | 'running' | 'success' | 'error'
  result?: object
  startedAt?: string
  finishedAt?: string
}

function ToolCallItem({ toolCall, expanded, onToggle }: Props) {
  // 折叠状态：只显示 action 名称 + status badge
  // 展开状态：显示完整 payload + result
  // status badge: pending(灰), running(蓝), success(绿), error(红)
}
```

### ApprovalBanner

```tsx
interface ApprovalRequest {
  id: string
  action: string
  reason: string            // 为什么要执行这个 action
  riskLevel: 'low' | 'medium' | 'high'
  payload: object
}

function ApprovalBanner({
  request,
  onApprove,
  onReject,
}: {
  request: ApprovalRequest
  onApprove: () => void
  onReject: () => void
}) {
  // 高风险（high）显示红色边框，medium 黄色，low 绿色
  // 显示 action + reason + 简要 payload
  // [Approve] [Reject] 按钮
  // 倒计时或等待状态
}
```

### JobProgressIndicator

```tsx
const PIPELINE_STEPS = [
  { key: 'data_validate', label: '数据校验' },
  { key: 'panel_build', label: '面板构建' },
  { key: 'diagnostics', label: '诊断分析' },
  { key: 'psm_did', label: '因果推断' },
  { key: 'localgap', label: '增量分解' },
  { key: 'gps_uplift', label: '剂量响应' },
  { key: 'chart_render', label: '图表生成' },
  { key: 'report', label: '报告生成' },
]

function JobProgressIndicator({ jobId, steps }: Props) {
  // 当前步骤高亮
  // 已完成步骤打勾
  // 未完成步骤置灰
  // 显示当前步骤的 progress message（如有）
}
```

### MessageInput

```tsx
function MessageInput({
  onSend,
  disabled,
}: {
  onSend: (message: string) => void
  disabled: boolean
}) {
  // textarea，Enter 发送，Shift+Enter 换行
  // disabled 时显示加载状态
  // 最小高度 48px，最大高度 200px（自动扩展）
  // 发送后清空输入框
}
```

### ArtifactCreatedToast

```tsx
// 使用 sonner 或 react-hot-toast
// 显示 artifact 创建通知
toast.success(`Artifact created: ${artifactName}`, {
  description: artifactType,
  action: { label: 'View', onClick: () => navigate(`/projects/${projectId}/dashboard`) }
})
```

## SSE 事件处理

```typescript
// agent-store 中的 SSE 事件处理

handleSSEEvent(event: SSEEvent) {
  switch (event.type) {
    case 'assistant_message_delta':
      // 追加 delta 到当前 assistant message
      this.appendDelta(event.turn_id, event.delta)
      break

    case 'tool_call_started':
      // 新增 tool call 到 message.toolCalls
      this.addToolCall(event.turn_id, event.action)
      break

    case 'tool_call_finished':
      // 更新 tool call status
      this.updateToolCallStatus(event.action, event.ok)
      break

    case 'job_started':
      this.addJob(event.job_id)
      break

    case 'job_progress':
      this.updateJobProgress(event.job_id, event.progress, event.message)
      break

    case 'job_finished':
      this.completeJob(event.job_id, event.ok)
      break

    case 'approval_requested':
      this.addApprovalRequest(event.approval_id, event)
      break

    case 'final_answer':
      this.finalizeMessage(event.turn_id, event.message)
      break
  }
}
```

## API 集成

```typescript
// AgentPage 初始化时
const { sessionId } = await agentStore.createSession(projectId)

// 发送消息
const handleSend = async (message: string) => {
  await agentStore.sendMessage(sessionId, message)
}

// 审批
const handleApprove = async (approvalId: string) => {
  await api.approveApproval(approvalId)
}
```

## 与后端 SSE 事件的对应关系

| SSE 事件类型 | 前端组件行为 |
|-------------|------------|
| `assistant_message_delta` | 追加到 MessageList，streaming 显示 |
| `tool_call_started` | 显示 ToolCallItem（pending → running）|
| `tool_call_finished` | ToolCallItem 更新状态，显示 result 摘要 |
| `job_started` | JobProgressIndicator 高亮当前步骤 |
| `job_progress` | JobProgressIndicator 更新 progress bar |
| `job_finished` | JobProgressIndicator 标记步骤完成 |
| `artifact_created` | Toast 通知，可点击跳转到 Dashboard |
| `approval_requested` | ApprovalBanner 显示 |
| `final_answer` | MessageList 显示完整回答 |
| `error` | MessageList 显示错误状态 |

## 验收标准

1. 用户输入消息 → SSE 收到 `assistant_message_delta` → 实时显示 streaming 回答
2. 工具调用时 MessageList 显示 ToolCallItem
3. 高风险操作触发 ApprovalBanner，用户可 approve/reject
4. Pipeline 执行时 JobProgressIndicator 显示进度
5. Artifact 创建时显示 toast 通知
6. Interrupt 按钮能中断当前 session
