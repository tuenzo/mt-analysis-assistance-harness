# Business Analysis Companion Workspace — Agent Context

> 商业分析伴随式工作区。当前处于 **MVP 0：骨架验证阶段**。

## Current Dev Environment Record (2026-05-13)

This section is the current source of truth for local development environment
usage confirmed in the active agent-flow validation conversation.

- Setup scripts are not validated yet. Do not use `setup.ps1`, `setup.sh`, or
  `scripts/local_setup.py` as the acceptance path for the current agent-flow
  stage until they have their own verification pass.
- Before starting a new validation run, scan and stop stale backend/frontend
  processes from this repository. Old runs have used ports including `8000`,
  `8010`, `8017`, `8025`, `18080`, `18081`, `18191`-`18194`, `3010`, `3025`,
  and `4180`.
- Current manual backend command:

```powershell
cd backend
$env:APP_DATABASE_URL='sqlite:///E:/CodingProject/meituancomp-analysis-assistance-harness/backend/business_analysis.db'
.\.venv\Scripts\python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 18081
```

- Current manual frontend command:

```powershell
cd frontend
$env:NEXT_PUBLIC_API_BASE_URL='http://127.0.0.1:18081'
npm run dev -- -H 127.0.0.1 -p 3010
```

- Current validation URLs:
  - Backend: `http://127.0.0.1:18081`
  - Frontend: `http://127.0.0.1:3010`
  - Agent runtime metadata: `GET http://127.0.0.1:18081/api/agent/runtime`
- Default SQLite path: repository-root `business_analysis.db` unless
  `APP_DATABASE_URL` is explicitly set. Current validation runs explicitly use
  `backend/business_analysis.db` because it contains the active real-data
  projects.
- Agent-flow validation project name: `Keemart 促销增长全流程项目`. All current
  end-to-end tests should be run under that project unless the user changes the
  validation target.
- Documentation maintenance rule: whenever the dev environment, service ports,
  startup procedure, validation project, or setup-script status changes and that
  change is persisted to disk, the agent must check and update this section and
  `README.md` in the same work session. If setup-script status changes, also
  check `SETUP.md`.

---

## 1. 系统定位（一句话）

一个基于 Codex Agent SDK 的本地优先商业分析 harness：前端工作区承载分析流程，后端 Message Runtime 承载 agent loop，`business_analysis` 单一工具网关承载真实分析执行，workspace 文件系统承载项目状态。

---

## 2. 不可违背的架构原则

### P1：Message-first，不是 Workflow-first
所有自然语言输入必须经过 `POST /api/agent/messages`，由 `MessageRuntime` 送入 Codex Agent SDK，由 Codex 决定是回答、追问、读取状态还是调用工具。前端不允许把普通消息直接路由到 `/api/agent/runs`。

### P2：Codex Agent SDK 是推理运行时，不是业务后端
Codex 只负责推理、工具调用决策、session 连续性。项目状态、文件一致性、schema、artifact、审计日志必须由后端数据库和 workspace manifest 管理。Codex session 不是事实源。

### P3：外部只暴露一个业务工具
向 Codex 注册的唯一自定义工具是 `business_analysis(project_id, action, payload, reason)`。内部工具网关 (`AnalysisToolGateway`) 负责 action 校验、权限审批、执行、写日志、生成 artifact。禁止直接暴露几十个内部工具给 Codex。

### P4：Workspace 是项目事实源
每个项目独立目录 `workspaces/{project_id}/`：
- `.analysis/` —— 系统读写：manifest、context_summary、checkpoints
- `.Codex/` —— agent 上下文：skills、settings、项目级 AGENTS.md
- `data/`、`artifacts/`、`reports/`、`logs/` —— 业务产物

进入项目时必须校验 `project_manifest.json` checksum，检测到文件变更要更新 context_summary 再交给 Codex。

### P5：记忆同步必须受控
分析结论默认写入项目内记忆（`.analysis/context_summary.md`、`memory_candidates.md`）。同步到用户级 Codex memory 必须经用户显式确认。禁止自动写入敏感原始数据或临时假设。

---

## 3. 技术栈与目录职责

```text
frontend/      Next.js 14 (App Router), TypeScript, Tailwind CSS, Zustand
backend/       FastAPI, Python 3.10+, SQLite, SQLAlchemy
openspec/      OpenSpec 工作流：changes/（提案）→ specs/（归档）
workspaces/    运行时生成，不提交到 git
```

### 后端模块边界

| 目录 | 职责 | 关键文件 |
|------|------|----------|
| `app/api/` | HTTP 路由、SSE event stream | `agent_messages.py` 是唯一消息入口 |
| `app/agent/` | MessageRuntime、ClaudeAdapter、ContextBuilder、SessionStore | 禁止业务代码直接调用 SDK |
| `app/tools/` | 工具网关、注册表、各域工具实现 | `gateway.py` 是所有 tool call 的必经入口 |
| `app/workspace/` | 目录初始化、manifest 管理、checksum、scanner | `manager.py`, `manifest.py` |
| `app/analysis/pipelines/` | 分析 pipeline：build_panel、diagnostics、psm_did、localgap、gps_uplift | 当前 MVP0 可为 stub/mock，但接口必须稳定 |
| `app/jobs/` | 长任务编排：panel build、full pipeline、report generation | `orchestrator.py` |
| `app/artifacts/` | artifact 注册与读取 | `service.py` |
| `app/reports/` | 报告渲染与导出 | `renderer.py`, `exporters.py` |
| `app/memory/` | memory candidate 生成、用户确认、同步 | `bridge.py`, `summarizer.py` |
| `app/core/` | 配置、数据库、权限、事件 | `config.py`, `database.py`, `permissions.py` |
| `app/projects/` | 项目 CRUD、状态管理 | `service.py`, `models.py`, `schemas.py` |

### 前端模块边界

| 目录 | 职责 |
|------|------|
| `src/app/` | 页面路由、layout |
| `src/features/` | 业务组件：project、data-intake、agent-command-center、run-timeline、dashboard、report-studio、memory-review |
| `src/components/ui/` | 通用 UI：button、card、input、modal、select、badge |
| `src/lib/` | API 客户端、类型定义、SSE hooks |
| `src/store/` | Zustand 全局状态：agent-store、project-store、ui-store |

---

## 4. 契约与格式

### API 统一响应

```python
{ "ok": bool, "data": Any | None, "error": str | None }
```

所有后端路由必须返回此结构。前端 `api-client.ts` 统一处理。

### SSE Event Stream

`POST /api/agent/messages` 返回 `MessageResponse`，前端通过 `event_stream_url` 接收 SSE：

```ts
type SSEEvent =
  | { type: 'assistant_message_delta'; delta: string }
  | { type: 'tool_call_started'; tool: string; action: string }
  | { type: 'tool_call_finished'; tool: string; action: string; ok: boolean }
  | { type: 'job_progress'; job_id: string; progress: number; message: string }
  | { type: 'artifact_created'; artifact_id: string; name: string }
  | { type: 'approval_requested'; approval_id: string; action: string; reason: string }
  | { type: 'final_answer'; message: string }
  | { type: 'error'; error: string }
```

### Tool Result 结构

内部工具返回统一结构：

```python
class ToolResult(BaseModel):
    ok: bool
    action: str
    summary: str
    artifacts: list[ArtifactRef] = []
    state_patch: dict = {}
    assistant_hint: str = ""
    error: ToolError | None = None
```

---

## 5. 权限分级

| Level | 名称 | 允许操作 |
|-------|------|----------|
| 0 | read_state | 读取项目状态、artifact |
| 1 | safe_compute | 数据校验、字段识别、只读诊断 |
| 2 | write_artifact | 生成图表、表格、报告草稿 |
| 3 | modify_workspace | 写入脚本、覆盖中间结果、删除旧 artifact |
| 4 | external_sync | 写入用户级 memory、调用外部 API |

高风险 action（如 `analysis.run_full_pipeline`、`report.generate`）自动触发 `ApprovalRequest`，需用户在 UI 确认。

---

## 6. 当前阶段：MVP 0（骨架验证）

目标：证明架构可跑 —— 本地 Web 前端 + FastAPI 后端 + SQLite + workspace 创建 + agent message 循环 + business_analysis mock tool。

### MVP 0 已完成
- [x] 后端 FastAPI 骨架 + SQLite ORM + 统一 API 响应
- [x] 项目 CRUD + workspace 初始化 + manifest/checksum
- [x] Agent 模块：MessageRuntime、ClaudeAdapter stub、SessionStore、ContextBuilder
- [x] Tool Gateway + Registry + 权限框架
- [x] Analysis pipeline stubs（build_panel、diagnostics、psm_did、localgap）
- [x] Job Orchestrator stub
- [x] Memory Bridge stub
- [x] 前端 Next.js 骨架 + 项目列表 + 项目内各页面路由
- [x] Agent Command Center：消息输入、SSE 接收、tool call 卡片、approval banner
- [x] Data Intake 页面 + File Upload
- [x] Dashboard / Timeline / Reports / Memory Review 页面占位

### MVP 0 待完成（优先级排序）
1. **真数据接入**：文件上传后实际解析 CSV，写入 `data/raw/`，更新 manifest
2. **Schema 识别与映射**：`data.validate`、`schema.infer`、`schema.apply_mapping`
3. **真分析 pipeline**：`build_panel.py` 生成真实的 category × day panel（pandas）
4. **Agent message 端到端打通**：ClaudeAdapter 从 stub 改为真实调用（或配置化 mock）
5. **Artifact 服务**：图表/表格生成后注册到 artifact 表并返回 path

### 后续阶段
- **MVP 1**：真数据接入 + 真实 panel build + 基础 diagnostics
- **MVP 2**：PSM-DID / LocalGap / GPS-Uplift 真实运行
- **MVP 3**：Report Studio 报告生成与导出
- **MVP 4**：Memory Bridge 用户确认与同步

---

## 7. 开发规则

### 7.1 变更必须通过 OpenSpec

1. 新需求 → 写入 `openspec/changes/` 的 proposal（YAML）
2. 实现 → 按 proposal 任务列表执行
3. 验收 → 测试通过后，archive 到 `openspec/specs/`

### 7.2 修改范围约束
- 后端新增 API：必须在 `app/api/` 加路由，在 `app/` 对应模块加逻辑，禁止在路由里写业务逻辑
- 新增 tool action：必须在 `app/tools/registry.py` 注册，在对应工具模块实现，经过 gateway 执行
- 新增分析 pipeline：必须在 `app/analysis/pipelines/` 实现，接口与现有 stub 保持一致
- 前端新增页面：使用 App Router，`src/app/projects/[project_id]/{feature}/page.tsx`
- 新增组件：业务组件放 `src/features/`，通用 UI 放 `src/components/ui/`

### 7.3 测试要求
- 后端新增模块必须附带 pytest 测试，放 `app/tests/`
- 修改后运行 `pytest`（后端）和 `npm run build`（前端）验证
- mock/stub 阶段允许测试覆盖 gateway 和 API 契约，不强制要求分析算法精度测试

### 7.4 数据库变更
- MVP 阶段使用 SQLite，模型定义在 `app/projects/models.py`
- 新增表/字段后，SQLAlchemy 会在 `init_db()` 自动建表（开发阶段允许删库重建）
- 非开发阶段需要迁移脚本

### 7.5 Git 约束（项目特有）
- 原子提交，使用 Conventional Commits：`feat:`, `fix:`, `refactor:`, `test:`, `docs:`
- 提交前 `git diff` 检查：无密钥、无 `.env`、无 `__pycache__`、无 `node_modules`
- 不自动 `git push`，不执行 `git reset --hard` / `git clean -fd`
- 工作区存在未知改动时，先识别来源再操作

---

## 8. 环境配置

复制 `.env.example` → `.env`：

```bash
cp .env.example .env
```

关键变量：

| 变量 | 说明 | 默认值 |
|------|------|--------|
| `ANTHROPIC_API_KEY` | API 密钥 | - |
| `ANTHROPIC_API_BASE_URL` | 代理地址 | - |
| `ANTHROPIC_API_MODEL` | 模型名称 | `LongCat-Flash-Chat` |
| `APP_AGENT_RUNTIME_PROVIDER` | `mock` / `claude_agent_sdk` | `claude_agent_sdk` |
| `APP_AGENT_PERMISSION_MODE` | `dontAsk` / `manual` | `dontAsk` |
| `APP_DATABASE_URL` | 显式数据库 URL；未设置时固定为仓库根 `business_analysis.db` | - |
| `APP_WORKSPACE_ROOT` | 工作区根目录 | `./workspaces` |

配置优先级：环境变量 > `.env` > 代码默认值。

---

## 9. 常用命令

```bash
# 后端
cd backend
.venv\Scripts\activate          # Windows
pytest                          # 运行测试
uvicorn app.main:app --reload   # 开发服务

# 前端
cd frontend
npm install
npm run dev                     # 开发服务
npm run build                   # 构建验证
```

---

## 10. 数据分析 Pipeline（固化流程）

系统目标分析链路（从 specV1）：

1. **Data Intake** — `order_info.csv` / `exposure_info.csv` / `activity_timeline.csv`
2. **Schema & Quality** — `schema.infer`, `data.validate`, `quality.audit_lineage`
3. **Panel Build** — `panel.build_category_day`（category × day，GMV/discount/exposure/order/user）
4. **Descriptive Diagnostics** — `analysis.run_diagnostics`
5. **Causal Direction** — `analysis.run_psm_did`
6. **Increment Decomposition** — `analysis.run_localgap`
7. **Dose Response** — `analysis.run_gps_uplift`
8. **Uplift & Strategy** — 策略矩阵（Persuadables / Sure Things / Lost Causes / Do Not Disturb）
9. **Reference Alignment Quality** — `quality.score_reference_alignment`
10. **Report Generation** — `report.generate`

当前 MVP0 阶段：stub 实现，接口先行，逐步替换为真实算法。
