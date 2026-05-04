# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.



## 系统定位

**商业分析伴随式工作区 (Business Analysis Companion Workspace)** —— 基于 Claude Agent SDK 的垂直业务 harness，通过网页工作区提供结构化分析场景，以 Claude agent loop 承载自然语言推理，以单一 `business_analysis` 工具网关执行真实数据分析。

核心设计原则：
- Claude Agent SDK 是 agent loop，不是业务数据库
- Workspace 是项目事实源 (`.analysis/`)，Claude session 不是文件系统状态
- Skill 是分析方法说明，不是完整产品
- `business_analysis` 是唯一外部工具入口，内部工具必须 schema 化、可审计
- 记忆同步必须经过用户确认

## 技术架构

```
Browser Web App (前端工作区)
  ├─ Project Workspace / Data Intake / Field Mapping
  ├─ Agent Command Center / Run Timeline
  └─ Result Dashboard / Report Studio / Memory Review Panel

Local Business Analysis Backend (FastAPI)
  ├─ API Gateway (/api/projects, /api/agent/messages, ...)
  ├─ Workspace Manager (manifest, scanner, checkpoints)
  ├─ Claude Runtime Adapter (session, event stream)
  ├─ Analysis Tool Gateway (单一入口，路由到内部工具)
  ├─ Job Orchestrator (pipeline runner)
  └─ Memory Bridge (项目级/用户级分层)

Claude Agent SDK Runtime
  ├─ Agent Loop + Sessions + streaming input mode
  ├─ Custom MCP tools (仅 business_analysis 一个)
  └─ Hooks + Permissions (Level 0-4)

Analysis Workspace (每个项目独立目录)
  ├─ data/raw/ | data/processed/
  ├─ scripts/ (build_panel.py, run_psm_did.py, ...)
  ├─ artifacts/charts/ | artifacts/tables/ | artifacts/model_outputs/
  ├─ reports/
  ├─ logs/agent_events.jsonl
  ├─ .analysis/ (project_manifest.json, context_summary.md, memory_candidates.md)
  └─ .claude/CLAUDE.md (agent context，不承担项目状态)
```

## 项目阶段

当前为 **MVP 0 阶段**（骨架搭建）：
目标：证明架构可跑 —— 本地 Web 前端 + FastAPI 后端 + SQLite + workspace 创建 + Claude Adapter stub + business_analysis mock tool。

后续阶段：MVP 1 真数据接入 → MVP 2 真实分析 pipeline → MVP 3 报告生成 → MVP 4 记忆桥接。

## 开发约定

- 使用 **OpenSpec** 工作流管理变更：变更先写入 `openspec/changes/` 作为 proposal，批准后实现，验收完成后 archive。
- 所有 API 端点返回统一结构：`{ok, data, error}`。
- 工具调用必须写审计日志到 `logs/tool_calls.jsonl`。
- Workspace 文件一致性由 `project_manifest.json` 管理，每次进入项目时校验 checksum。

## 常用命令

项目开始构建后补充。当前为空项目，无可执行命令。

## 环境配置

敏感配置通过 `.env` 文件管理（不会被提交到 git）。

**配置步骤：**
1. 复制 `.env.example` 为 `.env`
2. 填写你的 API Key 和 Base URL
3. 重启服务生效

```bash
cp .env.example .env
# 编辑 .env 填入你的配置
```

**关键配置项：**

| 变量名 | 说明 | 默认值 |
|--------|------|--------|
| `ANTHROPIC_API_KEY` | 第三方 API 密钥 | - |
| `ANTHROPIC_API_BASE_URL` | 自定义 API 地址 | - |
| `APP_AGENT_RUNTIME_PROVIDER` | 运行时类型 (`mock`/`claude_agent_sdk`) | `mock` |
| `APP_AGENT_PERMISSION_MODE` | 权限模式 (`dontAsk`/`manual`) | `dontAsk` |
| `APP_WORKSPACE_ROOT` | 工作区根目录 | `./workspaces` |

**配置优先级：** 环境变量 > `.env` 文件 > 代码默认值

## 数据分析流程

系统固化的标准 pipeline（从 specV1）：

1. **Data Intake** — 上传 order_info.csv / exposure_info.csv / activity_timeline.csv
2. **Schema & Quality** — 字段识别、缺失检查、日期范围、品类覆盖、活动窗口
3. **Panel Build** — category × day panel，GMV/discount/exposure/order/user metrics
4. **Descriptive Diagnostics** — GMV trend、activity vs non-activity、payday overlap
5. **Causal Direction** — PSM-DID / event study、parallel trend、placebo check
6. **Increment Decomposition** — LocalBaseline、LocalGap、exposure/discount/payday/interaction/residual
7. **Dose Response** — GPS exposure response、GPS discount response
8. **Uplift & Strategy** — Persuadables / Sure Things / Lost Causes / Do Not Disturb
9. **Report Generation** — executive summary、method、charts、strategy matrix、limitations、next-cycle


## Git 使用习惯与版本管理规范

你在本项目中进行任何代码修改时，必须遵守以下 Git 习惯与规范。

### 1. 修改前先检查仓库状态

在开始修改前，先运行：

```bash
git status
````

确认当前分支、未提交文件和已有改动。

如果发现工作区中存在用户已有改动，尤其是你没有创建的改动，禁止直接覆盖、删除或重置。应先识别这些改动的来源，并在回复中说明。

严禁在未经明确授权的情况下执行：

```bash
git reset --hard
git checkout -- .
git clean -fd
git restore .
```

### 2. 每次修改应保持原子性

一次提交只解决一个明确问题，例如：

* 修复一个 bug
* 新增一个功能
* 重构一个模块
* 添加一组测试
* 更新一类文档

不要把无关修改混在同一次提交中。

### 3. 修改后必须再次检查 diff

完成修改后，必须运行：

```bash
git diff
```

检查实际改动是否符合任务目标。

需要重点确认：

* 没有误改无关文件
* 没有删除用户已有内容
* 没有提交临时调试代码
* 没有提交密钥、token、路径、隐私数据
* 没有提交大体积中间文件、缓存文件或运行输出

必要时检查暂存区：

```bash
git diff --cached
```

### 4. 提交前运行必要验证

在提交前，根据项目类型运行必要的检查，例如：

```bash
pytest
npm test
npm run lint
npm run build
python -m pytest
```

如果无法运行测试，需要明确说明原因，并说明已经完成了哪些替代性检查。

### 5. 提交信息规范

提交信息应清晰、简洁，优先使用 Conventional Commits 风格：

```text
feat: add user authentication flow
fix: handle empty input in optimizer
refactor: simplify continuous subproblem solver
test: add regression tests for QUBO builder
docs: update deployment instructions
chore: update dependencies
```

提交信息要说明“做了什么”，不要写成模糊内容，例如：

```text
update
fix bug
change files
final version
```

### 6. 分支使用规范

如果任务较大，应优先新建任务分支：

```bash
git checkout -b feat/short-task-name
```

分支命名建议：

```text
feat/xxx
fix/xxx
refactor/xxx
docs/xxx
test/xxx
experiment/xxx
```

不要直接在主分支上进行大型、不确定或实验性修改。

### 7. 不要随意提交自动生成文件

除非任务明确要求，否则不要提交以下内容：

```text
__pycache__/
*.pyc
.DS_Store
.env
.venv/
node_modules/
dist/
build/
outputs/
logs/
*.log
.ipynb_checkpoints/
```

如果发现这些文件未被忽略，应建议更新 `.gitignore`。

### 8. 保护用户已有代码

你必须区分：

* 本次任务需要修改的代码
* 用户已有但与你任务无关的代码
* 其他工具或用户正在修改的代码

禁止为了让测试通过而粗暴删除、绕过或重写大段已有逻辑。

如果必须重构，应说明：

1. 为什么需要重构；
2. 重构影响范围；
3. 如何验证行为保持一致。

### 9. 每轮工作结束后给出 Git 摘要

完成任务后，请在回复中给出：

```text
Git 状态：
- 当前分支：
- 修改文件：
- 新增文件：
- 删除文件：
- 是否已运行测试：
- 是否已提交：
- 建议提交信息：
```

如果已经提交，还需要给出 commit hash。

### 10. 默认不要自动 push

除非用户明确要求，否则不要执行：

```bash
git push
```

如果需要 push，应先确认远程分支和目标仓库，避免推送到错误分支。

### 11. 遇到冲突或异常时暂停破坏性操作

如果出现以下情况，应停止继续执行高风险 Git 操作，并向用户报告：

* merge conflict
* rebase conflict
* detached HEAD
* remote rejected
* 工作区存在大量未知改动
* 当前分支不是预期分支
* 用户已有改动可能被覆盖

禁止通过强制覆盖来“快速解决”。

### 12. 推荐工作流程

一般任务应遵循以下流程：

```bash
git status
git checkout -b task/short-name   # 如有必要
# 修改代码
git diff
# 运行测试或构建
git status
git add <relevant-files>
git diff --cached
git commit -m "type: concise description"   # 用户允许时再提交
```

核心原则：小步修改、清晰 diff、可回滚、可审查、不覆盖用户已有工作。

```
```
