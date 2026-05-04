---
name: business-analysis-system
description: 商业分析伴随式工作区完整系统规格
type: spec
version: 1
created_at: 2026-05-04
source: 系统设计specV1.md
---

# Business Analysis Companion Workspace - 系统规格

## 1. 产品定位

### 1.1 产品名称

**Business Analysis Companion Workspace** / 商业分析伴随式工作区

### 1.2 核心定位

不是一个独立 BI 系统，也不是 Claude Code 里的单个 Skill，而是一个基于 Claude Agent SDK 的商业分析工作区 harness。

```
Claude Agent SDK
  + 商业分析专用网页工作区
  + 独立项目文件空间
  + 受控分析工具网关
  + 结果看板与报告系统
  + 记忆桥接机制
```

### 1.3 设计目标

让用户在已有个人助手工作流中，进入一个商业分析专用工作区；保留自然语言协作体验；补足数据上传、字段映射、任务进度、图表看板、报告生成、记忆复盘等结构化能力；避免独立分析系统带来的数据迁移、结果导出和上下文割裂。

---

## 2. 设计原则

### P1: Message-first，不是 Workflow-first

所有自然语言输入必须先进入统一消息入口 `POST /api/agent/messages`，不允许前端把普通自然语言默认发送到 `/api/agent/runs`。

每个 message turn 由后端 `MessageRuntime` 与 Claude Agent SDK 共同决定：直接回答、追问澄清、读取项目状态、调用 business_analysis 工具、生成分析计划、启动分析任务、解释结果、生成报告、生成记忆候选。

### P2: Claude Agent SDK 是推理运行时，不是业务后端

Claude SDK 负责：多轮推理、agent loop、工具调用决策、session 连续性、用户级/项目级 Claude 配置加载、permissions/hooks/MCP 生态能力。

业务后端负责：项目状态、文件状态、数据 schema、分析任务、图表和报告产物、权限审计、记忆同步、artifact manifest。

Claude session 不能作为项目事实源。项目事实源必须是数据库和 workspace manifest。

### P3: 外部只暴露一个业务工具

系统只向 Claude 暴露一个工具：`business_analysis(project_id, action, payload, reason)`。不直接暴露几十个内部工具，避免工具上下文膨胀和权限失控。

### P4: Workspace 是项目事实源

每个项目都有独立 workspace：

```
workspaces/{project_id}/
  data/
  scripts/
  artifacts/
  reports/
  logs/
  .analysis/    ← 由系统读写，是项目事实源
  .claude/      ← 由 Claude 读取，是 agent 上下文和指令层
```

### P5: 记忆同步必须受控

不能把所有分析过程自动写入用户级 Claude 记忆。系统必须先生成 memory candidate，再由用户确认是否同步。

```
默认：写入项目内记忆
可选：用户确认后同步到用户级 Claude memory
禁止：自动写入敏感原始数据、临时假设、中间错误结论
```

---

## 3. 总体架构

```
┌───────────────────────────────────────────────────────────────┐
│ Browser Web App                                                │
│ ├─ Project Rail                                                │
│ ├─ Data Intake                                                 │
│ ├─ Agent Command Center                                        │
│ ├─ Run Timeline                                                │
│ ├─ Result Dashboard                                            │
│ ├─ Report Studio                                               │
│ └─ Memory Review Panel                                         │
└───────────────────────────────┬───────────────────────────────┘
                                │
                                │ HTTP / SSE / WebSocket
                                ▼
┌───────────────────────────────────────────────────────────────┐
│ Business Analysis Backend                                      │
│ ├─ API Gateway                                                 │
│ ├─ Project Service                                             │
│ ├─ Workspace Manager                                           │
│ ├─ Message Runtime                                             │
│ ├─ Context Builder / Prompt Composer                           │
│ ├─ Claude Runtime Adapter                                     │
│ ├─ Analysis Tool Gateway                                      │
│ ├─ Job Orchestrator                                           │
│ ├─ Artifact Service                                           │
│ ├─ Report Service                                             │
│ ├─ Memory Bridge                                               │
│ └─ Audit / Permission Service                                  │
└──────────────────────┬──────────────────────┬────────────────────┘
                       │                      │
                       ▼                      ▼
┌──────────────────────────────┐   ┌─────────────────────────────┐
│ Claude Agent SDK Runtime     │   │ Analysis Workspace          │
│ ├─ Agent Loop                │   │ ├─ data/raw                  │
│ ├─ Sessions                  │   │ ├─ data/processed            │
│ ├─ Custom MCP Tool           │   │ ├─ scripts                   │
│ ├─ Permissions               │   │ ├─ artifacts                 │
│ ├─ Hooks                     │   │ ├─ reports                   │
│ └─ Skills / .claude context  │   │ ├─ logs                      │
└──────────────────────────────┘   │ ├─ .analysis                 │
                                   │ └─ .claude                    │
                                   └──────────────────────────────┘
```

---

## 4. 前端架构

### 页面结构

```
frontend/
  src/
    app/
      routes/
      layout/
      state/
      api/
    features/
      project/
      data-intake/
      agent-command-center/
      run-timeline/
      dashboard/
      report-studio/
      memory-review/
      artifacts/
    components/
      ui/
      charts/
      tables/
      events/
```

### 核心页面

1. **Project Home** — 展示项目状态、数据状态、最新结果、下一步建议
2. **Data Intake** — 上传 order_info / exposure_info / activity_timeline，支持字段识别、字段映射、数据质量报告
3. **Agent Command Center** — 唯一自然语言入口，展示 assistant message、tool call、approval、artifact created、run status
4. **Run Timeline** — 展示 data → panel → diagnostics → causal → uplift → report 的执行过程
5. **Result Dashboard** — 展示趋势图、LocalGap、GPS、Uplift、策略矩阵
6. **Report Studio** — 展示报告草稿、图表引用、段落编辑、导出
7. **Memory Review** — 展示 memory candidates，让用户选择是否同步到全局记忆

### 前端原则

- 所有自然语言输入只调用 `POST /api/agent/messages`
- 前端不直接调用 `/api/agent/runs` 作为默认消息路径
- 分析按钮、生成报告按钮等结构化 UI 也应该生成 message 或 job intent
- 前端根据 event stream 更新 UI，不在前端硬编码 mock 结果作为真实状态

---

## 5. 后端模块职责

### API Gateway

负责 HTTP API、SSE/WebSocket event stream、错误格式统一。

### Project Service

负责项目创建、项目状态、项目元数据。

### Workspace Manager

负责：
- 初始化 workspace 目录
- 保存上传文件
- 计算 checksum
- 维护 project_manifest.json
- 检测文件移动/修改/过期
- 生成 context_summary.md
- 管理 checkpoints

### Message Runtime

统一消息循环：
```
User Message
  → build context
  → send to Claude Agent SDK
  → receive assistant/tool events
  → if tool call, forward to Analysis Tool Gateway
  → persist events
  → stream to frontend
```

### Claude Runtime Adapter

封装 Claude Agent SDK，不允许业务代码到处直接调用 SDK。

方法：
- `create_session(project_id)`
- `resume_session(session_id)`
- `send_message(session, message, context)`
- `stream_events(session)`
- `interrupt(session)`

### Analysis Tool Gateway

统一执行 Claude 调用的 `business_analysis` action。

必须做：
- action enum 校验
- payload schema 校验
- permission level 校验
- 审批判断
- tool call log
- job 创建/同步执行
- artifact 写入
- state patch
- structured ToolResult

### Job Orchestrator

负责长任务：panel build、full pipeline、report generation、export。

### Artifact Service

负责图表、表格、模型结果、报告文件注册和读取。

### Memory Bridge

负责：
- 从项目结果生成 memory candidate
- 展示给用户确认
- 同步到项目内 memory
- 可选同步到用户级 memory

---

## 6. Claude SDK 配置建议

Claude SDK 应使用 streaming input mode。推荐默认配置：

```ts
const options = {
  cwd: workspacePath,
  permissionMode: "dontAsk",
  allowedTools: ["mcp__business_analysis__business_analysis"],
  mcpServers: [businessAnalysisMcpServer],
  settingSources: ["user", "project"],
  systemPrompt: {
    type: "preset",
    preset: "claude_code",
    append: businessAnalysisSystemPrompt
  }
}
```

权限必须收紧。Claude SDK 提供 permission modes、permission rules 和 `canUseTool` runtime callback。hooks 可用于工具调用前后、session start、execution stop 等事件拦截和审计。

---

## 7. 项目阶段 (MVP)

### MVP 0：本地可启动骨架

目标：证明架构能跑。

```
- 本地 Web 前端
- FastAPI / Node backend
- SQLite
- workspace 创建
- Claude Agent SDK adapter stub
- business_analysis mock tool
- agent message event stream
```

验收：用户输入消息 → Claude SDK / mock runtime → tool call → 前端显示事件

### MVP 1：真数据接入

目标：从 demo 变成真实分析项目。

```
- 上传三张表
- 自动识别 order / exposure / activity
- 字段校验
- project_manifest
- category_day_panel 生成
- validation artifact
```

验收：上传数据后，系统能生成真实 panel 和数据质量报告

### MVP 2：真实分析 pipeline

目标：跑通核心业务链路。

```
- diagnostics
- PSM-DID
- LocalGap
- GPS-Uplift
- strategy matrix
- artifact dashboard
```

验收：用户说"帮我分析" → Claude 调用 business_analysis(action="analysis.run_full_pipeline") → 系统生成图表、表格和结果摘要

### MVP 3：报告生成

目标：从分析结果到报告。

```
- report.md
- report.tex / pdf
- report sections
- 图表引用
- 可编辑报告预览
```

验收：用户说"生成一版报告" → 系统生成可下载报告 → Claude 能解释报告结论

### MVP 4：记忆桥接

目标：实现伴随式个人助手体验。

```
- 生成项目复盘摘要
- 生成用户偏好摘要
- Memory Review Panel
- 用户确认后同步到用户级 memory
```

验收：用户确认后，其他 Claude 工作区可以通过用户级记忆看到已确认的商业分析偏好或项目摘要

---

## 8. 最重要的工程边界

1. Claude Agent SDK 是 agent loop，不是业务数据库
2. Claude session 是对话记忆，不是文件系统状态
3. Skill 是方法说明，不是完整产品
4. Workspace 是项目事实源
5. business_analysis 是唯一外部工具入口
6. 内部工具必须 schema 化、可审计、可重试
7. 前端是工作场景，不是聊天框皮肤
8. 记忆同步必须经过用户确认
9. 不把所有消息都路由成 AgentRun
10. 不让 Claude 直接绕过工具网关操作分析资产

---

## 9. 数据分析流程

系统固化的标准 pipeline：

1. **Data Intake** — 上传 order_info.csv / exposure_info.csv / activity_timeline.csv
2. **Schema & Quality** — 字段识别、缺失检查、日期范围、品类覆盖、活动窗口
3. **Panel Build** — category × day panel，GMV/discount/exposure/order/user metrics
4. **Descriptive Diagnostics** — GMV trend、activity vs non-activity、payday overlap
5. **Causal Direction** — PSM-DID / event study、parallel trend、placebo check
6. **Increment Decomposition** — LocalBaseline、LocalGap、exposure/discount/payday/interaction/residual
7. **Dose Response** — GPS exposure response、GPS discount response
8. **Uplift & Strategy** — Persuadables / Sure Things / Lost Causes / Do Not Disturb
9. **Report Generation** — executive summary、method、charts、strategy matrix、limitations、next-cycle