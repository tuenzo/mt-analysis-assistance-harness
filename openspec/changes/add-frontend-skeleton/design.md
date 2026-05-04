## Overview

本变更实现前端 skeleton：Next.js 14 项目、目录结构、API client、SSE 事件流、Zustand stores、基础 UI 组件。

## 项目结构

```
frontend/
├── public/
├── src/
│   ├── app/                          # Next.js App Router
│   │   ├── layout.tsx                # 根布局（Sidebar + Header）
│   │   ├── page.tsx                 # 根页面（重定向 /projects）
│   │   ├── globals.css
│   │   ├── projects/
│   │   │   ├── page.tsx             # Project Rail（项目列表）
│   │   │   └── [project_id]/
│   │   │       ├── layout.tsx       # 项目布局（ProjectSidebar + 主内容区）
│   │   │       ├── page.tsx        # Project Home
│   │   │       ├── data-intake/page.tsx
│   │   │       ├── agent/page.tsx  # Agent Command Center
│   │   │       ├── timeline/page.tsx
│   │   │       ├── dashboard/page.tsx
│   │   │       ├── reports/page.tsx
│   │   │       └── memory/page.tsx
│   │   └── api/                     # API proxy（如需要）
│   │
│   ├── components/                   # 共享 UI 组件
│   │   └── ui/                     # 基础组件
│   │       ├── button.tsx
│   │       ├── card.tsx
│   │       ├── input.tsx
│   │       ├── select.tsx
│   │       ├── badge.tsx
│   │       └── modal.tsx
│   │
│   ├── features/                    # Feature 模块
│   │   ├── layout/
│   │   │   ├── sidebar.tsx
│   │   │   ├── header.tsx
│   │   │   └── project-layout.tsx
│   │   ├── project/
│   │   │   ├── project-list.tsx
│   │   │   └── project-card.tsx
│   │   ├── agent/
│   │   │   ├── message-list.tsx
│   │   │   ├── message-input.tsx
│   │   │   ├── tool-call-item.tsx
│   │   │   └── approval-banner.tsx
│   │   ├── data-intake/
│   │   │   ├── file-upload.tsx
│   │   │   └── schema-mapper.tsx
│   │   ├── timeline/
│   │   │   └── run-timeline.tsx
│   │   ├── dashboard/
│   │   │   └── result-dashboard.tsx
│   │   ├── reports/
│   │   │   └── report-studio.tsx
│   │   └── memory/
│   │       └── memory-review.tsx
│   │
│   ├── lib/                         # 工具库
│   │   ├── api-client.ts           # API 客户端
│   │   ├── api-types.ts            # API 请求/响应类型
│   │   └── sse-hooks.ts            # SSE hooks
│   │
│   └── store/                       # Zustand stores
│       ├── project-store.ts
│       ├── agent-store.ts
│       └── ui-store.ts
│
├── package.json
├── next.config.js
├── tailwind.config.ts
├── tsconfig.json
└── .env.local
```

## API Client 设计

### 核心 API 函数

```typescript
// src/lib/api-client.ts

// ===== Projects API =====
api.createProject(name: string, domain: string): Promise<Project>
api.listProjects(): Promise<Project[]>
api.getProject(projectId: string): Promise<Project>
api.getProjectState(projectId: string): Promise<ProjectState>

// ===== Files API =====
api.uploadFile(projectId: string, file: File, role: string): Promise<FileUploadResponse>
api.listFiles(projectId: string): Promise<ProjectFile[]>
api.inferSchema(projectId: string): Promise<SchemaInferResponse>
api.applySchema(projectId: string, mapping: FieldMapping): Promise<void>

// ===== Agent API =====
api.createMessage(projectId: string, message: string): Promise<MessageResponse>
api.getSessionEvents(sessionId: string): EventSource  // SSE

// ===== Artifacts API =====
api.listArtifacts(projectId: string, filters?: ArtifactsFilter): Promise<Artifact[]>
api.getArtifact(artifactId: string): Promise<Artifact>

// ===== Reports API =====
api.generateReport(projectId: string, reportType: string): Promise<Report>
api.getLatestReport(projectId: string): Promise<Report>
api.exportReport(reportId: string, format: string): Promise<string>

// ===== Memory API =====
api.listMemoryCandidates(projectId: string, filters?: MemoryFilter): Promise<MemoryCandidate[]>
api.approveMemoryCandidate(candidateId: string, syncTarget: string): Promise<MemoryCandidate>
api.rejectMemoryCandidate(candidateId: string): Promise<MemoryCandidate>
```

### API Response 统一格式

```typescript
// 所有 API 响应符合统一格式
interface ApiResponse<T> {
  ok: boolean
  data: T | null
  error: string | null
}
```

### SSE 事件类型

```typescript
// src/lib/api-types.ts

type SSEEvent =
  | { type: 'assistant_message_delta'; turn_id: string; delta: string }
  | { type: 'tool_call_started'; turn_id: string; tool: string; action: string }
  | { type: 'tool_call_finished'; turn_id: string; action: string; ok: boolean }
  | { type: 'job_started'; turn_id: string; job_id: string }
  | { type: 'job_progress'; turn_id: string; job_id: string; progress: number; message: string }
  | { type: 'job_finished'; turn_id: string; job_id: string; ok: boolean }
  | { type: 'artifact_created'; turn_id: string; artifact_id: string; name: string }
  | { type: 'approval_requested'; turn_id: string; approval_id: string; action: string; reason: string }
  | { type: 'final_answer'; turn_id: string; message: string }
  | { type: 'error'; turn_id: string; error: string }
```

## Zustand Stores

### Project Store

```typescript
// src/store/project-store.ts
interface ProjectStore {
  projects: Project[]
  currentProject: Project | null
  projectState: ProjectState | null

  loadProjects: () => Promise<void>
  selectProject: (projectId: string) => Promise<void>
  loadProjectState: (projectId: string) => Promise<void>
}
```

### Agent Store

```typescript
// src/store/agent-store.ts
interface AgentStore {
  sessions: Record<string, AgentSession>
  currentSession: AgentSession | null
  messageQueue: AgentMessage[]

  createSession: (projectId: string) => Promise<string>
  sendMessage: (sessionId: string, message: string) => Promise<void>
  handleSSEEvent: (event: SSEEvent) => void
  interruptSession: (sessionId: string) => Promise<void>
}
```

### UI Store

```typescript
// src/store/ui-store.ts
interface UIStore {
  sidebarCollapsed: boolean
  currentView: string
  notifications: Notification[]

  toggleSidebar: () => void
  setCurrentView: (view: string) => void
  addNotification: (notification: Notification) => void
  removeNotification: (id: string) => void
}
```

## SSE Hook 设计

```typescript
// src/lib/sse-hooks.ts

export function useAgentEvents(sessionId: string | null) {
  // 连接到 GET /api/agent/sessions/{session_id}/events
  // 接收 SSE 事件并分发给 agent-store
  // 返回连接状态：{ connected, error }
}
```

## 基础 UI 组件

使用 shadcn/ui 或 radix-ui 作为基础，定制样式：

```tsx
// components/ui/button.tsx
// variants: default, secondary, outline, ghost, destructive
// sizes: sm, md, lg
```

## 路由结构

```
/                               → redirect to /projects
/projects                       → Project Rail（项目列表）
/projects/new                   → 创建项目

/projects/[project_id]          → Project Home（layout + page）
/projects/[project_id]/data-intake
/projects/[project_id]/agent    → Agent Command Center
/projects/[project_id]/timeline
/projects/[project_id]/dashboard
/projects/[project_id]/reports
/projects/[project_id]/memory
```

## 布局组件

### 根布局 (app/layout.tsx)

```tsx
<div className="flex h-screen">
  <Sidebar />           // 固定左侧，项目列表导航
  <div className="flex-1 flex flex-col">
    <Header />         // 顶部栏，项目信息 + 用户
    <MainContent />    // 主内容区，slot for page
  </div>
</div>
```

### 项目布局 (app/projects/[project_id]/layout.tsx)

```tsx
<div className="flex flex-col h-full">
  <ProjectTabs />      // 子导航：Home | Data | Agent | Timeline | Dashboard | Reports | Memory
  <div className="flex-1 overflow-auto">
    {children}
  </div>
</div>
```

## 环境配置

```bash
# frontend/.env.local
NEXT_PUBLIC_API_BASE_URL=http://localhost:8000
```

## 验收标准

1. `npm run dev` 能启动前端开发服务器
2. 访问 `/projects` 能看到项目列表（或空状态）
3. 访问 `/projects/[project_id]/agent` 能看到 Agent Command Center
4. SSE 连接状态正确反映（connected/error）
5. `POST /api/agent/messages` 能发送消息并显示响应
6. 前端不硬编码任何 mock 数据，所有数据来自 API
