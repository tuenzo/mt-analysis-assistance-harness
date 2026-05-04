## Tasks

### Phase 1: 项目初始化

- [ ] **T1.1** — 初始化 Next.js 14 项目
  ```bash
  cd frontend
  npx create-next-app@latest . --typescript --tailwind --app --src-dir --import-alias "@/*"
  # 选择：Yes to all defaults
  ```

- [ ] **T1.2** — 安装依赖
  ```bash
  npm install zustand swr ky @radix-ui/react-dialog @radix-ui/react-dropdown-menu @radix-ui/react-select @radix-ui/react-tabs @radix-ui/react-badge
  ```

- [ ] **T1.3** — 配置 `tailwind.config.ts` 和 `globals.css`
  - 设置 CSS 变量（背景色、文字色等）
  - 引入 fonts

### Phase 2: API Client

- [ ] **T2.1** — 创建 `src/lib/api-types.ts`
  ```typescript
  // 定义所有 API 请求/响应类型、SSE 事件类型、enums
  // Project, ProjectFile, Artifact, Report, MemoryCandidate, SSEEvent...
  ```

- [ ] **T2.2** — 创建 `src/lib/api-client.ts`
  ```typescript
  // 实现 api 命名空间对象，包含所有 API 函数
  // 统一错误处理、统一响应格式转换
  ```

- [ ] **T2.3** — 创建 `src/lib/sse-hooks.ts`
  ```typescript
  // useAgentEvents(sessionId) hook
  // useProjectState(projectId) hook
  ```

### Phase 3: Zustand Stores

- [ ] **T3.1** — 创建 `src/store/project-store.ts`
  - projects, currentProject, projectState
  - loadProjects, selectProject, loadProjectState

- [ ] **T3.2** — 创建 `src/store/agent-store.ts`
  - sessions, currentSession, messageQueue
  - createSession, sendMessage, handleSSEEvent, interruptSession

- [ ] **T3.3** — 创建 `src/store/ui-store.ts`
  - sidebarCollapsed, currentView, notifications
  - toggleSidebar, setCurrentView, addNotification, removeNotification

### Phase 4: 基础 UI 组件

- [ ] **T4.1** — `src/components/ui/button.tsx`
  - variants: default, secondary, outline, ghost, destructive
  - sizes: sm, md, lg

- [ ] **T4.2** — `src/components/ui/card.tsx`
- [ ] **T4.3** — `src/components/ui/input.tsx`
- [ ] **T4.4** — `src/components/ui/select.tsx`
- [ ] **T4.5** — `src/components/ui/badge.tsx`
- [ ] **T4.6** — `src/components/ui/modal.tsx`

### Phase 5: 布局组件

- [ ] **T5.1** — `src/features/layout/sidebar.tsx`
  - 项目列表（可折叠）
  - 导航链接

- [ ] **T5.2** — `src/features/layout/header.tsx`
  - 当前项目名称
  - 用户信息

- [ ] **T5.3** — `src/app/layout.tsx`
  - 根布局：Sidebar + Header + MainContent

- [ ] **T5.4** — `src/app/projects/[project_id]/layout.tsx`
  - 项目布局：ProjectTabs + children

- [ ] **T5.5** — `src/features/layout/project-tabs.tsx`
  - 子导航 tabs

### Phase 6: 页面路由

- [ ] **T6.1** — `src/app/page.tsx`
  ```tsx
  // 重定向到 /projects
  import { redirect } from 'next/navigation'
  export default () => redirect('/projects')
  ```

- [ ] **T6.2** — `src/app/projects/page.tsx`
  - Project Rail：项目列表（create project button + project cards）

- [ ] **T6.3** — `src/app/projects/[project_id]/page.tsx`
  - Project Home

### Phase 7: 环境配置

- [ ] **T7.1** — 创建 `frontend/.env.local`
  ```
  NEXT_PUBLIC_API_BASE_URL=http://localhost:8000
  ```

- [ ] **T7.2** — 验证 proxy 配置（如需要）

### Phase 8: 验证测试

- [ ] **T8.1** — `npm run dev` 能启动
- [ ] **T8.2** — 访问 `/projects` 正常显示
- [ ] **T8.3** — 访问 `/projects/test/agent` 正常显示（无数据但组件渲染正常）
- [ ] **T8.4** — 确认控制台无 Error level 日志

---

## 验收标准

1. `npm run dev` 成功启动，端口 3000
2. `/projects` 页面渲染正常（可无数据）
3. `/projects/[project_id]` 子路由正常（可无数据）
4. Sidebar、Header 布局正确
5. API client 的函数签名与 design.md 一致
6. Zustand stores 初始化正常，无 hydration 错误
7. 前端无硬编码 mock 数据（数据全来自 API）
