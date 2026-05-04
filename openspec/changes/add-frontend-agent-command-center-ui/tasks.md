## Tasks

### Phase 1: agent-store 扩展

- [ ] **T1.1** — 扩展 `src/store/agent-store.ts` 新增类型
  ```typescript
  interface ToolCall {
    id: string
    turnId: string
    action: string
    payload: object
    status: 'pending' | 'running' | 'success' | 'error'
    result?: object
    startedAt?: string
    finishedAt?: string
  }

  interface ApprovalRequest {
    id: string
    turnId: string
    action: string
    reason: string
    riskLevel: 'low' | 'medium' | 'high'
    payload: object
  }

  interface JobStatus {
    id: string
    turnId: string
    currentStep: string
    totalSteps: number
    progress: number
    message: string
  }
  ```

- [ ] **T1.2** — 扩展 agent-store 状态
  ```typescript
  interface AgentStore {
    // 新增
    toolCalls: Record<string, ToolCall[]>  // turnId -> toolCalls
    approvalRequests: ApprovalRequest[]
    jobs: Record<string, JobStatus>
  }
  ```

- [ ] **T1.3** — 实现 SSE 事件分发到上述新状态

### Phase 2: MessageList 组件

- [ ] **T2.1** — 创建 `src/features/agent/message-list.tsx`
  - 消息按 role 对齐（user 右，assistant 左）
  - assistant message streaming 时追加 delta
  - 自动滚动到底部

- [ ] **T2.2** — 创建 `src/features/agent/message-item.tsx`
  - 区分 user/assistant message 样式
  - 显示 timestamp

### Phase 3: ToolCallItem 组件

- [ ] **T3.1** — 创建 `src/features/agent/tool-call-item.tsx`
  - 折叠/展开 payload
  - status badge (pending/running/success/error)
  - 展示 result 摘要（成功时）

- [ ] **T3.2** — 创建 `src/features/agent/tool-call-detail.tsx`
  - 右侧可折叠面板显示 tool call 详情

### Phase 4: ApprovalBanner 组件

- [ ] **T4.1** — 创建 `src/features/agent/approval-banner.tsx`
  - 颜色区分 riskLevel
  - 显示 action + reason
  - Approve / Reject 按钮

- [ ] **T4.2** — 创建 `src/lib/api-client.ts` 中的 approval API
  ```typescript
  api.approveApproval(approvalId: string): Promise<void>
  api.rejectApproval(approvalId: string): Promise<void>
  ```

### Phase 5: JobProgressIndicator 组件

- [ ] **T5.1** — 创建 `src/features/agent/job-progress-indicator.tsx`
  - 8 步骤 pipeline 进度条
  - 当前步骤高亮，已完成打勾

### Phase 6: MessageInput 组件

- [ ] **T6.1** — 创建 `src/features/agent/message-input.tsx`
  - Enter 发送，Shift+Enter 换行
  - disabled 状态
  - auto-resize textarea

### Phase 7: ArtifactCreatedToast

- [ ] **T7.1** — 安装 `sonner` 或 `react-hot-toast`
  ```bash
  npm install sonner
  ```

- [ ] **T7.2** — 在 AgentPage 中集成 toast
  - `artifact_created` 事件触发 toast

### Phase 8: AgentPage 页面

- [ ] **T8.1** — 创建 `src/app/projects/[project_id]/agent/page.tsx`
  - 布局：MessageList + ToolCallDetail（右侧）+ MessageInput
  - 初始化 session
  - 连接 SSE 事件流

- [ ] **T8.2** — Interrupt 按钮
  - 调用 `api.interruptSession(sessionId)`
  - 更新 session 状态

- [ ] **T8.3** — Clear 按钮
  - 清空 message 列表（但不关闭 session）

### Phase 9: 集成测试

- [ ] **T9.1** — 手动测试：发送"你好" → 收到 streaming 回复
- [ ] **T9.2** — 手动测试：发送"帮我分析" → 看到 tool call + job progress
- [ ] **T9.3** — 手动测试：高风险操作触发 approval banner
- [ ] **T9.4** — 确认无 console error

---

## 验收标准

1. 发送消息后 SSE 事件流正确驱动 MessageList 更新
2. tool_call_started / tool_call_finished 正确显示 ToolCallItem
3. approval_requested 正确显示 ApprovalBanner
4. job_progress 正确更新 JobProgressIndicator
5. artifact_created 触发 toast 通知
6. Interrupt 能中断正在运行的 session
7. 所有组件无 TypeScript 错误
