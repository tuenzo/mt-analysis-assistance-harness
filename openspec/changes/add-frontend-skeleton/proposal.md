## Why

MVP 0 的后端已完成，但前端完全空白。前端是用户直接交互的工作区，没有前端就无法验证"用户输入消息 → Claude SDK / mock runtime → tool call → 前端显示事件"这条核心链路。前端 skeleton 是所有 UI changes 的基础设施。

## What Changes

- **新增** Next.js 14 项目（App Router，TypeScript）
- **新增** 项目目录结构：`frontend/src/app/`, `frontend/src/features/`, `frontend/src/components/`
- **新增** API client 层：封装后端 REST API 和 SSE 事件流
- **新增** 全局状态管理：Zustand store（project store, agent store, ui store）
- **新增** 基础布局组件：Sidebar, Header, MainContent
- **新增** 基础 UI 组件：Button, Card, Input, Select, Badge, Modal
- **新增** SSE 事件流连接 hook：`useAgentEvents(session_id)`
- **新增** API client 函数：`api.postMessage()`, `api.getProjectState()`, `api.uploadFile()` 等
- **新增** `.env.local` 配置（API_BASE_URL）

## Capabilities

### New Capabilities
- `frontend-skeleton`: Next.js 项目、目录结构、API client、状态管理、基础组件

### Modified Capabilities
- 无（首个前端变更，无历史依赖）

## Impact

- **新建**: `frontend/` — Next.js 14 项目根目录
- **新建**: `frontend/src/app/layout.tsx` — 根布局（Sidebar + Header）
- **新建**: `frontend/src/app/page.tsx` — 根页面（重定向到 /projects）
- **新建**: `frontend/src/app/globals.css` — 全局样式（Tailwind）
- **新建**: `frontend/src/lib/api-client.ts` — API client（REST + SSE）
- **新建**: `frontend/src/store/project-store.ts` — Zustand project store
- **新建**: `frontend/src/store/agent-store.ts` — Zustand agent store
- **新建**: `frontend/src/store/ui-store.ts` — Zustand ui store
- **新建**: `frontend/src/components/ui/` — 基础 UI 组件
- **新建**: `frontend/src/features/layout/` — Sidebar, Header
- **测试**: 骨架 smoke test（页面能加载、SSE 能连接）

## 技术栈

- **Framework**: Next.js 14+ (App Router)
- **Language**: TypeScript
- **Styling**: Tailwind CSS
- **State**: Zustand
- **Data Fetching**: SWR
- **HTTP**: ky 或 native fetch
- **SSE**: native EventSource + custom hook

## 架构原则

1. **API client 统一封装**：所有后端调用通过 `src/lib/api-client.ts`，不直接使用 fetch
2. **SSE 事件流统一管理**：通过 `useAgentEvents` hook 订阅事件，状态更新到 agent-store
3. **前端不维护业务状态**：所有业务状态来自后端 API，前端只做展示和用户交互
4. **Feature 目录隔离**：按页面/功能模块划分 `features/`，每个 feature 独立

## 前端 Principle

根据 spec.md 第 170-175 行"前端原则"：
- 所有自然语言输入只调用 `POST /api/agent/messages`
- 分析按钮、生成报告按钮等结构化 UI 也应该生成 message 或 job intent
- 前端根据 event stream 更新 UI，不在前端硬编码 mock 结果作为真实状态
