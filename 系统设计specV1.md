明白。那我们现在不要再基于“已有 demo 怎么补后端”来设计，而是从零设计一套真正合理的系统。

我建议这版设计的核心定位是：

> **商业分析助手不是一个独立 BI 系统，也不是 Claude Code 里的一个 Skill，而是一个基于 Claude Agent SDK 的 Companion Workspace Harness：它以网页工作区承载商业分析流程，以 Claude Code SDK 承载 agent loop，以内部工具网关承载真实分析执行。**

---

# 一、产品总定位

## 1. 产品名称

可以暂定为：

**Business Analysis Companion Workspace**

或者中文：

**商业分析伴随式工作区**

它不是“另一个 Claude Code”，也不是“一个带聊天框的数据分析系统”。

它的本质是：

```text
Claude Agent SDK
  + 商业分析专用网页工作区
  + 独立项目文件空间
  + 受控分析工具网关
  + 结果看板与报告系统
  + 记忆桥接机制
```

Claude Code 官方定位是一个可以读取代码库、编辑文件、运行命令并集成开发工具的 agentic coding tool。([Claude API Docs][1]) Claude Agent SDK 则允许应用把 Claude Code 的 agent loop 嵌入自己的系统，并控制工具、权限、成本和输出；它不要求必须安装 Claude Code CLI。([Claude][2]) 所以我们应该使用 **Claude Agent SDK 作为推理运行时**，而不是试图操控用户已经打开的 Claude Code 终端。

---

# 二、第一性设计判断

## 1. 为什么不能只做 Skill

Skill 解决的是“Claude 知道怎么做”，不是“用户怎么高效工作”。

Claude Code 的 Skill 机制适合沉淀重复流程、检查清单、多步说明和支持文件；Skill 只有在相关时加载，长参考材料不会一直占用上下文。([Claude API Docs][3]) 但商业分析助手需要的不只是方法说明，还需要文件上传、字段映射、数据校验、任务进度、图表、报告、历史结果、版本管理和策略复盘。

你的项目报告也已经说明，商业分析助手要处理订单表、曝光表、活动表，自动完成清洗、口径统一、面板构建，并围绕“活动是否有效、增量来自哪里、资源应投给谁”组织分析链路。 这已经明显超出了一个 Skill 的边界。

所以结论是：

```text
Skill 是分析方法说明书；
Workspace 才是分析工作系统。
```

---

## 2. 为什么不能做完全独立的数据分析系统

完全独立系统的问题是用户摩擦太大：

```text
用户已有 Claude / 文件习惯 / 报告习惯 / 工作记忆
  ↓
进入独立分析系统
  ↓
重新上传数据、重新解释背景、重新导出结果
  ↓
再回到 Claude、文档、会议、报告系统继续工作
```

这会产生新的工作孤岛。

尤其商业分析的最终产物不是“系统里的一张图”，而是报告、复盘、会议讨论、策略调整和下一轮活动计划。因此它应该嵌入用户已有个人助手生态，而不是替代用户已有工作流。

---

## 3. 为什么应该做 Companion Workspace Harness

最合理形态是：

```text
用户仍然使用 Claude 作为长期个人助手
但当进入商业分析任务时
打开一个专用商业分析工作区
这个工作区接入 Claude Agent SDK
并提供可视化流程、受控工具、项目文件和结果管理
```

这就是 harness 的含义：**不重写智能体，而是把通用智能体约束、增强、封装到一个垂直业务工作场景里。**

---

# 三、核心架构总览

```text
Browser Web App
  ├─ Project Workspace
  ├─ Data Intake
  ├─ Field Mapping
  ├─ Agent Command Center
  ├─ Run Timeline
  ├─ Result Dashboard
  ├─ Report Studio
  └─ Memory Review Panel

Local / Hosted Business Analysis Backend
  ├─ API Gateway
  ├─ Project Service
  ├─ Workspace Manager
  ├─ Message Runtime
  ├─ Context Builder
  ├─ Claude Runtime Adapter
  ├─ Analysis Tool Gateway
  ├─ Job Orchestrator
  ├─ Artifact Service
  ├─ Report Service
  ├─ Memory Bridge
  └─ Audit / Permission Service

Claude Agent SDK Runtime
  ├─ Agent Loop
  ├─ Claude Code-compatible tools
  ├─ Custom MCP tools
  ├─ Sessions
  ├─ Skills
  ├─ Hooks
  └─ Permissions

Analysis Workspace
  ├─ data/raw
  ├─ data/processed
  ├─ scripts
  ├─ artifacts/charts
  ├─ artifacts/tables
  ├─ reports
  ├─ logs
  ├─ .analysis
  └─ .claude
```

---

# 四、部署形态选择

这里必须批判性地说：**如果你想保留用户 Claude Code 的工作习惯、文件、配置和记忆，最合理的第一版不是纯云端 SaaS，而是 local-first。**

## 推荐第一版：Local-first Web Workspace

```text
用户电脑
  ├─ 浏览器访问 http://localhost:xxxx
  ├─ 本地 Business Analysis Backend
  ├─ 本地分析项目 workspace
  ├─ Claude Agent SDK
  ├─ 用户 ~/.claude 配置
  └─ 可选本地 Claude Code CLI
```

原因：

* 能访问本地文件；
* 能加载用户级 Claude 配置；
* 能和用户已有工作目录共存；
* 能减少数据上传到云端的敏感性；
* 能更自然地和 Claude Code 的文件系统生态结合。

Claude Agent SDK 会读取 Claude Code 的 filesystem-based 配置；如果省略 `settingSources`，`query()` 会读取用户、项目和本地设置、CLAUDE.md、`.claude/` skills、agents、commands 等；也可以传 `settingSources: []` 来禁用这些文件系统配置。([Claude][4]) 这对 local-first 方案非常关键。

## 后续可扩展：Hybrid Cloud

后续可以做成：

```text
本地 companion service
  负责文件、Claude 配置、敏感数据、SDK runtime

云端 control plane
  负责账号、模板、团队协作、版本发布、远程报告分享
```

纯云端第一版不建议，因为它会削弱你最想强调的“嵌入个人助手工作流”。

---

# 五、运行时设计：Message-first，而不是 Workflow-first

你之前系统的缺陷正是：UI 像聊天，但后端仍然是 workflow-first。旧分析中已经指出，当前系统把非 slash 的自然语言都路由到 `AgentRun`，Planner 又只是关键词型 workflow router，导致普通对话失败。

从零设计时必须采用：

```text
所有用户输入 → Agent Message
Agent Message → Claude Agent SDK
Claude 决定：
  - 直接回答
  - 追问
  - 读取状态
  - 调用 business_analysis 工具
  - 生成计划
  - 执行分析
  - 生成报告
```

而不是：

```text
用户输入 → Planner → Workflow → 失败或运行
```

## 统一消息入口

```http
POST /api/agent/messages
```

请求：

```json
{
  "project_id": "proj_001",
  "session_id": "sess_001",
  "message": "帮我分析这批 payday promotion 数据",
  "ui_context": {
    "active_view": "data_upload",
    "selected_artifact_id": null
  }
}
```

响应不应该只是文本，而应该是事件流：

```json
{
  "assistant_message": "...",
  "events": [
    {
      "type": "tool_call_started",
      "tool": "business_analysis",
      "action": "data.validate"
    },
    {
      "type": "artifact_created",
      "artifact_type": "validation_report"
    }
  ]
}
```

---

# 六、Claude Agent SDK 接入方式

## 1. Claude Runtime Adapter

后端不应该到处直接调用 SDK，而是封装一层：

```text
ClaudeRuntimeAdapter
  ├─ create_session(project_id)
  ├─ resume_session(external_session_id)
  ├─ send_user_message(message, context)
  ├─ stream_agent_events()
  ├─ handle_tool_call()
  ├─ request_approval()
  └─ stop_or_interrupt()
```

Claude Agent SDK 支持 streaming input，官方建议把它用于持久交互式 session；这种模式支持长生命周期进程、用户输入、中断、权限请求、session management 和实时反馈。([Claude][5]) 所以我们的网页工作区应该使用 **streaming input mode**，而不是每次都做一次 one-shot query。

---

## 2. SDK Session 映射

我们自己的 session 和 Claude SDK session 要分开存：

```text
AnalysisSession
  id: sess_001
  project_id: proj_001
  external_runtime: claude_agent_sdk
  external_session_id: claude_sess_xxx
  created_at
  last_active_at
```

Claude SDK 的 session 持久化的是对话，不是文件系统；如果需要快照或回滚文件变化，需要额外做 file checkpointing。([Claude][6]) 所以我们的系统不能把 Claude session 当成项目状态数据库。

正确边界是：

```text
Claude session
  记录对话和推理连续性

Analysis workspace
  记录文件、数据、产物和项目状态

Database
  记录结构化状态、任务、事件、artifact、权限和 memory 候选
```

---

# 七、工具设计：外部只暴露一个 business_analysis 工具

这是整套架构最重要的设计。

Claude Agent SDK 可以用 in-process MCP server 定义自定义工具，并让 Claude 调用应用自己的函数、API、数据库或领域逻辑。([Claude][7]) 但我们不应该暴露几十个工具给 Claude，而应该只暴露一个统一入口：

```text
business_analysis
```

## 外部工具 schema

```json
{
  "name": "business_analysis",
  "description": "Run controlled business analysis actions inside the current analysis workspace.",
  "input_schema": {
    "type": "object",
    "properties": {
      "project_id": { "type": "string" },
      "action": {
        "type": "string",
        "enum": [
          "project.get_state",
          "data.ingest",
          "data.validate",
          "schema.infer",
          "schema.apply_mapping",
          "panel.build_category_day",
          "analysis.run_diagnostics",
          "analysis.run_psm_did",
          "analysis.run_localgap",
          "analysis.run_gps_uplift",
          "analysis.run_full_pipeline",
          "result.get_latest",
          "chart.render",
          "report.generate",
          "memory.propose_update"
        ]
      },
      "payload": { "type": "object" },
      "reason": { "type": "string" }
    },
    "required": ["project_id", "action", "payload", "reason"]
  }
}
```

Claude 只知道：

```text
我要调用 business_analysis(action="analysis.run_localgap")
```

但真实执行由我们自己的工具网关完成：

```text
Analysis Tool Gateway
  ├─ 校验 action
  ├─ 校验 payload schema
  ├─ 校验权限
  ├─ 写 tool_call log
  ├─ 调用内部工具
  ├─ 保存 artifact
  ├─ 生成 event
  └─ 返回结构化结果
```

这能避免工具上下文爆炸，也能防止 Claude 直接乱改分析文件。

---

# 八、内部工具网关设计

```text
AnalysisToolGateway
  ├─ ProjectStateTools
  │   ├─ project.get_state
  │   └─ artifact.read
  │
  ├─ DataTools
  │   ├─ data.ingest
  │   ├─ data.validate
  │   ├─ schema.infer
  │   └─ schema.apply_mapping
  │
  ├─ PanelTools
  │   └─ panel.build_category_day
  │
  ├─ AnalysisTools
  │   ├─ analysis.run_diagnostics
  │   ├─ analysis.run_psm_did
  │   ├─ analysis.run_localgap
  │   ├─ analysis.run_gps_uplift
  │   └─ analysis.run_full_pipeline
  │
  ├─ VisualizationTools
  │   └─ chart.render
  │
  ├─ ReportTools
  │   └─ report.generate
  │
  └─ MemoryTools
      └─ memory.propose_update
```

每个工具必须返回统一结果：

```json
{
  "ok": true,
  "action": "analysis.run_localgap",
  "summary": "LocalGap analysis completed.",
  "artifacts": [
    {
      "artifact_id": "art_001",
      "type": "chart",
      "path": "artifacts/charts/localgap_total.png"
    }
  ],
  "state_patch": {
    "latest_stage": "localgap_done"
  },
  "assistant_hint": "You can now explain where the increment comes from."
}
```

---

# 九、项目工作区设计

每个商业分析项目必须是一个独立 workspace。

```text
workspaces/
  proj_001/
    data/
      raw/
        order_info.csv
        exposure_info.csv
        activity_timeline.csv
      processed/
        category_day_panel.parquet
        modeling_table.parquet

    scripts/
      build_panel.py
      run_diagnostics.py
      run_psm_did.py
      run_localgap.py
      run_gps_uplift.py
      generate_report.py

    artifacts/
      charts/
        trend.png
        localgap_total.png
        gps_dose_response.png
        uplift_curve.png
      tables/
        summary_metrics.csv
        category_strategy.csv
      model_outputs/
        psm_did_result.json
        localgap_result.json
        gps_result.json
        uplift_result.json

    reports/
      report.md
      report.tex
      report.pdf
      report.docx

    logs/
      agent_events.jsonl
      tool_calls.jsonl
      jobs.jsonl
      errors.jsonl

    .analysis/
      project_manifest.json
      context_summary.md
      latest_result.json
      artifact_manifest.json
      memory_candidates.md
      checkpoints/

    .claude/
      CLAUDE.md
      skills/
        promo-analysis/
          SKILL.md
      settings.json
```

这里要特别强调：

```text
.claude/
  给 Claude 读，是 agent context

.analysis/
  给我们的系统读，是事实状态源
```

不要让 Claude session 成为唯一记忆，也不要让 `.claude/CLAUDE.md` 直接承担所有项目状态。

---

# 十、文件一致性设计

你提到“用户移动修改文件可能导致 Claude Code 记忆混乱”，这是非常关键的问题。

所以需要 `project_manifest.json`：

```json
{
  "project_id": "proj_001",
  "files": [
    {
      "file_id": "file_order",
      "role": "order_info",
      "original_name": "order_info.csv",
      "current_path": "data/raw/order_info.csv",
      "checksum": "sha256:xxx",
      "schema_hash": "sha256:yyy",
      "last_verified_at": "2026-05-04T10:00:00Z"
    }
  ],
  "derived_assets": [
    {
      "asset_id": "panel_001",
      "role": "category_day_panel",
      "path": "data/processed/category_day_panel.parquet",
      "source_file_ids": ["file_order", "file_exposure", "file_activity"],
      "checksum": "sha256:zzz"
    }
  ]
}
```

每次进入项目或运行分析前：

```text
WorkspaceManager
  → 扫描文件
  → 对比 checksum
  → 检查 schema
  → 判断中间结果是否过期
  → 更新 context_summary
  → 再把状态交给 Claude
```

这样 Claude 不会凭旧记忆继续分析已经变化的数据。

---

# 十一、前端工作区设计

前端不应该只是聊天框，而是四区结构。

```text
┌────────────────────────────────────────────────────────────┐
│ Top Bar: Project / Runtime / Sync / Memory / Export         │
├───────────────┬──────────────────────────┬─────────────────┤
│ Project Rail  │ Agent Command Center     │ Artifact Panel  │
│               │                          │                 │
│ - 数据状态     │ - 对话                   │ - 图表预览       │
│ - 分析阶段     │ - 工具调用卡片            │ - 表格预览       │
│ - 报告状态     │ - 审批请求                │ - 报告预览       │
│ - 记忆状态     │ - 下一步建议              │ - 文件 diff      │
├───────────────┴──────────────────────────┴─────────────────┤
│ Bottom Timeline: data → panel → diagnostics → model → report │
└────────────────────────────────────────────────────────────┘
```

## 前端核心页面

```text
1. Project Home
   当前项目状态、数据完整性、最近结果、下一步建议

2. Data Intake
   文件上传、字段识别、字段映射、数据质量报告

3. Analysis Plan
   分析目标、方法选择、参数确认、运行前检查

4. Agent Command Center
   统一对话入口、工具调用卡片、审批、状态追踪

5. Result Dashboard
   趋势、LocalGap、GPS、Uplift、策略矩阵

6. Report Studio
   报告结构、段落编辑、图表引用、导出

7. Memory Review
   候选记忆、项目摘要、是否同步到用户级 Claude 记忆
```

---

# 十二、记忆系统设计

记忆不能简单“全量共享”。必须分层。

## 1. 项目内记忆

保存在：

```text
workspaces/proj_001/.analysis/context_summary.md
workspaces/proj_001/.analysis/latest_result.json
workspaces/proj_001/.analysis/memory_candidates.md
```

内容包括：

```text
- 项目背景
- 数据口径
- 字段映射
- 已完成分析
- 核心结论
- 已确认策略
- 未解决问题
```

## 2. Claude 项目级上下文

保存在：

```text
workspaces/proj_001/.claude/CLAUDE.md
```

只放 Claude 需要知道的工作指令：

```text
你正在 Business Analysis Companion Workspace 中工作。
不要臆造数据结果。
需要真实数据、图表、模型、报告时，调用 business_analysis 工具。
当前项目状态以 .analysis/context_summary.md 和 project_manifest.json 为准。
```

## 3. 用户级长期记忆

保存在用户级 Claude 配置或我们自己的 memory store 中：

```text
~/.claude/business-analysis-memory/
  index.md
  preferences.md
  projects/
    proj_001_summary.md
```

但写入必须经过用户确认：

```text
Memory Bridge
  → 生成候选记忆
  → UI 展示
  → 用户选择：
      保存到项目
      同步到用户级 Claude memory
      不保存
```

原则是：

```text
默认项目内保存；
全局记忆必须确认；
不写入敏感原始数据；
只写入可复用偏好和确认结论。
```

---

# 十三、权限和审计设计

Claude Agent SDK 提供 permission modes、rules 和 `canUseTool` 回调来控制工具使用。([Claude][8]) Hooks 可以在工具调用、session start、execution stop 等事件上运行自定义代码，用于阻止危险操作、记录审计、清洗输入输出、要求人工审批和管理 session 生命周期。([Claude][9])

因此第一版就要内建权限系统。

## 权限分级

```text
Level 0: read_state
  读取项目状态、结果摘要、artifact

Level 1: safe_compute
  数据校验、字段识别、生成只读诊断

Level 2: write_artifact
  生成图表、表格、报告草稿

Level 3: modify_workspace
  写入脚本、覆盖中间结果、删除旧 artifact

Level 4: external_sync
  写入用户级 Claude memory、调用外部 API、导出到外部系统
```

## 审计日志

```json
{
  "event_id": "evt_001",
  "session_id": "sess_001",
  "turn_id": "turn_001",
  "tool": "business_analysis",
  "action": "report.generate",
  "payload_hash": "sha256:xxx",
  "permission_level": 2,
  "approved_by_user": true,
  "created_at": "..."
}
```

---

# 十四、数据分析流程设计

你的业务分析流程已经很清楚，系统应该把它固化为标准 pipeline。

```text
Step 1: Data Intake
  order_info.csv
  exposure_info.csv
  activity_timeline.csv

Step 2: Schema & Quality
  字段识别
  缺失检查
  日期范围检查
  品类覆盖检查
  活动窗口检查

Step 3: Panel Build
  category × day panel
  GMV / discount / exposure / order / user metrics
  payday variables
  activity variables

Step 4: Descriptive Diagnostics
  GMV trend
  activity vs non-activity
  payday overlap
  category concentration

Step 5: Causal Direction
  PSM-DID / event study
  parallel trend
  placebo check

Step 6: Increment Decomposition
  LocalBaseline
  LocalGap
  exposure / discount / payday / interaction / residual

Step 7: Dose Response
  GPS exposure response
  GPS discount response
  heterogeneity by category tier and payday window

Step 8: Uplift & Strategy
  uplift ranking
  Persuadables / Sure Things / Lost Causes / Do Not Disturb

Step 9: Report Generation
  executive summary
  method explanation
  charts
  strategy matrix
  limitations
  next-cycle recommendations
```

你已有报告中使用的核心方法正是这条链路：先处理三张表并构建品类 × 日期面板，再围绕 PSM-DID、增量分解、GPS-Uplift 和策略分层输出结论。 因此系统不是泛化“数据分析助手”，而是先从**周期性促销评估助手**开始。

---

# 十五、后端模块设计

```text
backend/
  app/
    api/
      projects.py
      files.py
      agent_messages.py
      jobs.py
      artifacts.py
      reports.py
      memory.py

    core/
      config.py
      auth.py
      permissions.py
      events.py

    projects/
      service.py
      models.py
      schemas.py

    workspace/
      manager.py
      manifest.py
      scanner.py
      checkpoints.py

    agent/
      message_runtime.py
      context_builder.py
      prompt_composer.py
      claude_adapter.py
      session_store.py
      event_mapper.py

    tools/
      gateway.py
      registry.py
      schemas.py
      project_tools.py
      data_tools.py
      panel_tools.py
      analysis_tools.py
      chart_tools.py
      report_tools.py
      memory_tools.py

    jobs/
      orchestrator.py
      runner.py
      queue.py
      status.py

    analysis/
      pipelines/
        build_panel.py
        diagnostics.py
        psm_did.py
        localgap.py
        gps_uplift.py
        full_pipeline.py

    reports/
      renderer.py
      templates/
      exporters.py

    memory/
      bridge.py
      summarizer.py
      store.py
```

---

# 十六、数据库核心表

```text
projects
  id
  name
  workspace_path
  created_at
  updated_at

project_files
  id
  project_id
  role
  original_name
  current_path
  checksum
  schema_json
  status

agent_sessions
  id
  project_id
  runtime_provider
  external_session_id
  status
  created_at

agent_turns
  id
  session_id
  user_message
  assistant_message
  status
  created_at

agent_events
  id
  session_id
  turn_id
  type
  payload_json
  created_at

tool_calls
  id
  session_id
  turn_id
  action
  payload_json
  result_json
  status
  created_at

jobs
  id
  project_id
  action
  status
  progress
  started_at
  finished_at

artifacts
  id
  project_id
  job_id
  type
  title
  path
  metadata_json
  created_at

reports
  id
  project_id
  status
  source_path
  pdf_path
  docx_path
  created_at

memory_candidates
  id
  project_id
  content
  scope
  status
  approved_at
```

---

# 十七、API 设计

## 项目

```http
POST /api/projects
GET /api/projects
GET /api/projects/{project_id}
GET /api/projects/{project_id}/state
```

## 文件

```http
POST /api/projects/{project_id}/files
GET /api/projects/{project_id}/files
POST /api/projects/{project_id}/files/validate
POST /api/projects/{project_id}/schema/apply
```

## Agent

```http
POST /api/agent/messages
GET /api/agent/sessions/{session_id}/events
POST /api/agent/sessions/{session_id}/interrupt
POST /api/agent/approvals/{approval_id}/approve
POST /api/agent/approvals/{approval_id}/reject
```

## Jobs

```http
POST /api/projects/{project_id}/jobs
GET /api/projects/{project_id}/jobs
GET /api/jobs/{job_id}
```

## Artifacts

```http
GET /api/projects/{project_id}/artifacts
GET /api/artifacts/{artifact_id}
```

## Reports

```http
POST /api/projects/{project_id}/reports/generate
GET /api/projects/{project_id}/reports/latest
POST /api/reports/{report_id}/export
```

## Memory

```http
GET /api/projects/{project_id}/memory/candidates
POST /api/memory/candidates/{candidate_id}/approve
POST /api/memory/candidates/{candidate_id}/reject
```

---

# 十八、Claude Prompt 设计

每次进入 Claude SDK 的上下文应该由 `PromptComposer` 构造。

```text
你正在 Business Analysis Companion Workspace 中工作。

你的身份：
你是商业分析助手，负责帮助用户完成周期性促销评估、资源配置优化和报告生成。

当前项目：
- project_id: {{project_id}}
- 项目名称: {{project_name}}
- 当前阶段: {{current_stage}}
- 已上传文件: {{files}}
- 数据质量状态: {{data_quality}}
- 最新分析结果: {{latest_result_summary}}

工作规则：
1. 普通解释、讨论、下一步建议可以直接回答。
2. 需要读取真实数据、运行模型、生成图表、生成报告时，必须调用 business_analysis 工具。
3. 不允许根据记忆臆造最新数据结果。
4. 项目真实状态以 .analysis/project_manifest.json 和 .analysis/context_summary.md 为准。
5. 不要直接修改用户级记忆；只能提出 memory.propose_update。
6. 高风险操作需要用户确认。

可用工具：
business_analysis(project_id, action, payload, reason)

当前用户消息：
{{user_message}}
```

---

# 十九、MVP 切分

## MVP 0：本地可启动骨架

目标：证明 architecture 能跑。

```text
- 本地 Web 前端
- FastAPI / Node backend
- SQLite
- workspace 创建
- Claude Agent SDK adapter stub
- business_analysis mock tool
- agent message event stream
```

验收：

```text
用户输入消息 → Claude SDK / mock runtime → tool call → 前端显示事件
```

---

## MVP 1：真数据接入

目标：从 demo 变成真实分析项目。

```text
- 上传三张表
- 自动识别 order / exposure / activity
- 字段校验
- project_manifest
- category_day_panel 生成
- validation artifact
```

验收：

```text
上传数据后，系统能生成真实 panel 和数据质量报告
```

---

## MVP 2：真实分析 pipeline

目标：跑通核心业务链路。

```text
- diagnostics
- PSM-DID
- LocalGap
- GPS-Uplift
- strategy matrix
- artifact dashboard
```

验收：

```text
用户说“帮我分析”
→ Claude 调用 business_analysis(action="analysis.run_full_pipeline")
→ 系统生成图表、表格和结果摘要
```

---

## MVP 3：报告生成

目标：从分析结果到报告。

```text
- report.md
- report.tex / pdf
- report sections
- 图表引用
- 可编辑报告预览
```

验收：

```text
用户说“生成一版报告”
→ 系统生成可下载报告
→ Claude 能解释报告结论
```

---

## MVP 4：记忆桥接

目标：实现伴随式个人助手体验。

```text
- 生成项目复盘摘要
- 生成用户偏好摘要
- Memory Review Panel
- 用户确认后同步到用户级 memory
```

验收：

```text
用户确认后，其他 Claude 工作区可以通过用户级记忆看到已确认的商业分析偏好或项目摘要
```

---

# 二十、最重要的工程边界

这版从头设计必须坚持以下边界：

```text
1. Claude Agent SDK 是 agent loop，不是业务数据库。
2. Claude session 是对话记忆，不是文件系统状态。
3. Skill 是方法说明，不是完整产品。
4. Workspace 是项目事实源。
5. business_analysis 是唯一外部工具入口。
6. 内部工具必须 schema 化、可审计、可重试。
7. 前端是工作场景，不是聊天框皮肤。
8. 记忆同步必须经过用户确认。
9. 不把所有消息都路由成 AgentRun。
10. 不让 Claude 直接绕过工具网关操作分析资产。
```

---

# 二十一、最终系统定义

一句话版本：

> **商业分析伴随式工作区是一个基于 Claude Agent SDK 的垂直业务 harness：它通过网页工作区提供结构化分析场景，通过 Claude agent loop 提供自然语言推理和任务规划，通过单一 business_analysis 工具网关执行真实数据分析，通过独立 workspace 管理数据、代码、图表和报告，并通过受控 Memory Bridge 与用户长期个人助手记忆连接。**

这就是我们从零开始应该设计的系统。
下一步最合理的是把这套方案拆成 **技术架构文档 + 数据模型文档 + API 文档 + coding agent 一次性实现提示词**。

[1]: https://docs.anthropic.com/en/docs/claude-code/overview "Claude Code overview - Claude Code Docs"
[2]: https://code.claude.com/docs/en/agent-sdk/agent-loop?utm_source=chatgpt.com "How the agent loop works - Claude Code Docs"
[3]: https://docs.anthropic.com/en/docs/claude-code/skills "Extend Claude with skills - Claude Code Docs"
[4]: https://code.claude.com/docs/en/agent-sdk/claude-code-features?utm_source=chatgpt.com "Use Claude Code features in the SDK"
[5]: https://code.claude.com/docs/en/agent-sdk/streaming-vs-single-mode?utm_source=chatgpt.com "Streaming Input - Claude Code Docs"
[6]: https://code.claude.com/docs/en/agent-sdk/sessions?utm_source=chatgpt.com "Work with sessions - Claude Code Docs"
[7]: https://code.claude.com/docs/en/agent-sdk/custom-tools?utm_source=chatgpt.com "Give Claude custom tools"
[8]: https://code.claude.com/docs/en/agent-sdk/permissions?utm_source=chatgpt.com "Configure permissions - Claude Code Docs"
[9]: https://code.claude.com/docs/en/agent-sdk/hooks?utm_source=chatgpt.com "Intercept and control agent behavior with hooks"
