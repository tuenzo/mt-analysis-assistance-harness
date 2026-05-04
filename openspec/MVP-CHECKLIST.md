# MVP 实施进度 Dashboard

> 本文档为临时工作文档，记录 MVP 0-4 各阶段的需求覆盖检查结果和待办事项。

**最后更新：** 2026-05-04（已创建 6 个前端 changes）
**关联 spec：** `openspec/specs/business-analysis-system/spec.md`

---

## MVP 总览

| 阶段 | 目标 | 状态 |
|------|------|------|
| MVP 0 | 骨架可跑 | 🔄 进行中（后端完成，前端骨架设计中） |
| MVP 1 | 真数据接入 | 📋 待启动 |
| MVP 2 | 真实分析 pipeline | 📋 待启动 |
| MVP 3 | 报告生成 | 📋 待启动 |
| MVP 4 | 记忆桥接 | 📋 待启动 |

---

## MVP 0 — 骨架搭建

**目标：** 证明架构可跑 —— 本地 Web 前端 + FastAPI 后端 + SQLite + workspace 创建 + Claude Adapter stub + business_analysis mock tool。

### 后端完成情况 ✅

| 组件 | Change | 状态 |
|------|--------|------|
| FastAPI backend | `add-backend-database-models` | ✅ |
| SQLite | `add-backend-database-models` | ✅ |
| workspace 创建 | `add-project-workspace-structure` | ✅ |
| Claude Agent SDK adapter stub | `add-claude-agent-sdk-adapter` | ✅ |
| business_analysis mock tool | `add-business-analysis-tool-gateway` | ✅ |
| agent message event stream (SSE) | `add-agent-message-runtime` | ✅ |

### 前端完成情况 🆕

| 页面/组件 | Change | 状态 |
|-----------|--------|------|
| 前端项目骨架 | `add-frontend-skeleton` | 🆕 已设计 |
| Agent Command Center | `add-frontend-agent-command-center-ui` | 🆕 已设计 |
| Project Home | `add-frontend-project-home-ui` | 🆕 已设计 |
| Data Intake | `add-frontend-data-intake-ui` | 🆕 已设计 |
| Run Timeline | `add-frontend-run-timeline-ui` | 🆕 已设计 |
| Result Dashboard | `add-frontend-result-dashboard-ui` | 🆕 已设计 |
| Report Studio | `add-report-studio-ui` | 📋 待设计 |
| Memory Review | `add-memory-review-ui` | 📋 待设计 |

### 已建 Changes（MVP 0 前端）

| 优先级 | Change | 覆盖内容 | 状态 |
|--------|--------|---------|------|
| P0 | `add-frontend-skeleton` | React 项目结构、路由、API client、SSE 连接 | ✅ 已创建 |
| P0 | `add-agent-command-center-ui` | 核心消息界面、tool call 显示、approval 事件 | ✅ 已创建 |
| P1 | `add-project-home-ui` | Project Home 页面 | ✅ 已创建 |
| P1 | `add-data-intake-ui` | Data Intake 页面（上传/字段映射） | ✅ 已创建 |
| P1 | `add-run-timeline-ui` | Run Timeline 页面 | ✅ 已创建 |
| P1 | `add-result-dashboard-ui` | Result Dashboard 页面 | ✅ 已创建 |
| P2 | `add-report-studio-ui` | Report Studio 页面 | 📋 待创建 |
| P2 | `add-memory-review-ui` | Memory Review 页面 | 📋 待创建 |

---

## MVP 1 — 真数据接入

**目标：** 上传三张表、自动识别 order/exposure/activity、字段校验、project_manifest、category_day_panel 生成、validation artifact。

### 需求覆盖

| 需求 | Change | 状态 | 缺口 |
|------|--------|------|------|
| 上传三张表 | `add-backend-database-models` | ✅ | |
| 自动识别 order/exposure/activity | `add-backend-database-models` | ✅ | |
| 字段校验 | `add-analysis-pipelines` | ⚠️ 分散 | 逻辑分散在两处 |
| project_manifest 联动 | `add-project-workspace-structure` | ⚠️ | Files API 未联动 update |
| category_day_panel 生成 | `add-analysis-pipelines` | ✅ | |
| validation artifact 注册 | `add-artifact-service` | ⚠️ | data.validate → ArtifactService 链路未完成 |

### 待完成事项（MVP 1）

| 优先级 | 事项 | 涉及 Change |
|--------|------|------------|
| P1 | 补全 `data.validate` → `ArtifactService.register()` 链路 | `add-artifact-service` |
| P1 | Files API (upload_file/apply_schema) 联动 `update_project_manifest` | `add-backend-database-models` |
| P2 | 统一字段校验逻辑（整合 schema_infer + validate_files） | `add-analysis-pipelines` |
| P1 | `add-data-intake-ui` 前端 | `add-data-intake-ui` |

---

## MVP 2 — 真实分析 pipeline

**目标：** diagnostics、PSM-DID、LocalGap、GPS-Uplift、strategy matrix、artifact dashboard。

### 需求覆盖

| 需求 | Change | 状态 | 缺口 |
|------|--------|------|------|
| diagnostics | `add-analysis-pipelines` | ✅ | |
| PSM-DID | `add-analysis-pipelines` | ⚠️ | 已实现但**未加入 full_pipeline** |
| LocalGap | `add-analysis-pipelines` | ✅ | |
| GPS-Uplift | `add-analysis-pipelines` | ⚠️ stub | stub 状态，非真实实现 |
| **strategy matrix** | — | ❌ | **完全无设计** |
| **artifact dashboard (UI)** | — | ❌ | 无前端设计 |

### 待完成/新建事项（MVP 2）

| 优先级 | 事项 | 涉及 Change |
|--------|------|------------|
| P0 | **新建 `add-strategy-matrix-design`** | strategy matrix 输入输出设计 |
| P0 | 将 PSM-DID 加入 full_pipeline | `add-analysis-pipelines` |
| P1 | GPS-Uplift 从 stub 升级为真实实现 | `add-analysis-pipelines` |
| P1 | `add-result-dashboard-ui` 前端 | `add-result-dashboard-ui` |
| P1 | `add-run-timeline-ui` 前端 | `add-run-timeline-ui` |

---

## MVP 3 — 报告生成

**目标：** report.md、report.tex/pdf、report sections、图表引用、可编辑报告预览。

### 需求覆盖

| 需求 | Change | 状态 | 缺口 |
|------|--------|------|------|
| report.md | `add-report-service` | ✅ | |
| report.pdf | `add-report-service` | ✅ | |
| report.tex | `add-report-service` | ⚠️ | 仅"后续扩展" mentions，无实际设计 |
| report sections | `add-report-service` | ✅ | |
| 图表引用 | `add-report-service` + `add-artifact-service` | ✅ | |
| **可编辑报告预览** | — | ❌ | **完全无设计** |

### 待完成事项（MVP 3）

| 优先级 | 事项 | 涉及 Change |
|--------|------|------------|
| P0 | **新建 `add-report-preview-design`** | 可编辑报告预览前后端设计 |
| P2 | LaTeX 导出明确规划（实现或排除出 MVP 3） | `add-report-service` |
| P2 | `add-report-studio-ui` 前端 | `add-report-studio-ui` |

---

## MVP 4 — 记忆桥接

**目标：** 生成项目复盘摘要、生成用户偏好摘要、Memory Review Panel、用户确认后同步到用户级 memory。

### 需求覆盖

| 需求 | Change | 状态 | 缺口 |
|------|--------|------|------|
| 项目复盘摘要 | `add-report-memory-system` + `add-memory-review-panel` | ✅ | |
| 用户偏好摘要 | `add-memory-review-panel` | ⚠️ | 生成策略是**占位**，无实际逻辑 |
| Memory Review Panel 后端 API | `add-memory-review-panel` | ✅ | |
| 用户级 memory 同步 | `add-report-memory-system` | ⚠️ | 机制有但流程不清晰 |

### 待完成事项（MVP 4）

| 优先级 | 事项 | 涉及 Change |
|--------|------|------------|
| P0 | **新建 `add-user-preference-memory`** | user_preference 候选生成逻辑 |
| P1 | 补充 `preferences.md` 写入逻辑 | `add-memory-review-panel` |
| P1 | 明确用户级 memory 手动同步操作步骤 | `add-report-memory-system` |
| P1 | Memory API 支持 scope/status 查询参数 | `add-memory-review-panel` |
| P2 | `add-memory-review-ui` 前端 | `add-memory-review-ui` |

---

## 完整 Changes 清单（按优先级）

### P0 — 阻断性问题

| # | Change | 状态 | MVP |
|---|--------|------|-----|
| 1 | `add-frontend-skeleton` | 🆕 新建 | 0 |
| 2 | `add-agent-command-center-ui` | 🆕 新建 | 0 |
| 3 | `add-strategy-matrix-design` | 🆕 新建 | 2 |
| 4 | `add-report-preview-design` | 🆕 新建 | 3 |
| 5 | `add-user-preference-memory` | 🆕 新建 | 4 |
| 6 | `add-validation-artifact-registration` | 🆕 新建 | 1 |
| 7 | `add-manifest-files-api-linkage` | 🆕 新建 | 1 |

### P1 — 功能完整性

| # | Change | 状态 | MVP |
|---|--------|------|-----|
| 8 | `add-project-home-ui` | 🆕 新建 | 0 |
| 9 | `add-data-intake-ui` | 🆕 新建 | 0/1 |
| 10 | `add-run-timeline-ui` | 🆕 新建 | 0/2 |
| 11 | `add-result-dashboard-ui` | 🆕 新建 | 0/2 |
| 12 | `add-gps-real-implementation` | 🆕 新建 | 2 |
| 13 | `add-psm-did-to-pipeline` | 🆕 新建 | 2 |

### P2 — 增强功能

| # | Change | 状态 | MVP |
|---|--------|------|-----|
| 14 | `add-report-studio-ui` | 🆕 新建 | 0/3 |
| 15 | `add-memory-review-ui` | 🆕 新建 | 0/4 |
| 16 | `add-latex-export-design` | 🆕 新建 | 3 |

### 已完成 Changes

| Change | 状态 |
|--------|------|
| `add-project-workspace-structure` | ✅ |
| `add-backend-database-models` | ✅ |
| `add-agent-message-runtime` | ✅ |
| `add-claude-agent-sdk-adapter` | ✅ (stub) |
| `add-business-analysis-tool-gateway` | ✅ (mock) |
| `add-analysis-pipelines` | ✅ (部分) |
| `add-artifact-service` | ✅ |
| `add-report-memory-system` | ✅ (部分) |
| `add-report-service` | ✅ |
| `add-memory-review-panel` | ✅ |

---

## MVP 串接计划

```
MVP 0: 骨架可跑
│
├─ ✅ 已有后端 (workspace/db/message/adapter/gateway)
│
└─ 🆕 前端 (最高优先级)
   ├─ add-frontend-skeleton           ← 第一个新建
   ├─ add-agent-command-center-ui
   ├─ add-project-home-ui
   ├─ add-data-intake-ui
   ├─ add-run-timeline-ui
   ├─ add-result-dashboard-ui
   ├─ add-report-studio-ui
   └─ add-memory-review-ui

MVP 1: 真数据接入
├─ ✅ add-analysis-pipelines (panel 部分)
├─ ✅ add-artifact-service
├─ 🆕 add-validation-artifact-registration    ← 补全链路
├─ 🆕 add-manifest-files-api-linkage         ← 补全联动
└─ 🆕 add-data-intake-ui (对接 Files API)

MVP 2: 真实分析 pipeline
├─ ⚠️ add-analysis-pipelines (需: PSM-DID 加入 pipeline, GPS stub→真实)
├─ 🆕 add-strategy-matrix-design              ← 核心缺口
├─ 🆕 add-gps-real-implementation
├─ 🆕 add-psm-did-to-pipeline
└─ 🆕 add-result-dashboard-ui + add-run-timeline-ui

MVP 3: 报告生成
├─ ✅ add-report-memory-system
├─ ✅ add-report-service
├─ 🆕 add-report-preview-design               ← 核心缺口
├─ 🆕 add-latex-export-design (或明确排除)
└─ 🆕 add-report-studio-ui

MVP 4: 记忆桥接
├─ ✅ add-memory-review-panel (后端 API)
├─ 🆕 add-user-preference-memory              ← 核心缺口
└─ 🆕 add-memory-review-ui
```

---

## 待确认问题

1. **可编辑报告预览** — 是前端富文本编辑器 + 实时预览，还是后端提供草稿状态？
2. **strategy matrix** — 具体指什么？（策略效果矩阵？竞争格局？）
3. **LaTeX 导出** — 是否在 MVP 3 范围内？
4. **用户级 memory 同步** — `global_memory_export.md` 如何格式化为可导入 Claude memory 的格式？
