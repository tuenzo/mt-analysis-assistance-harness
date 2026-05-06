# Agent Prompt Composition Notes

Last updated: 2026-05-06

本文档记录当前 agent 消息链路里的提示词拼接逻辑、实际送入不同 runtime 的内容，以及我在测试 agent 分析全流程时看到的可优化点。目标是先把“现在到底拼了什么”讲清楚，后续再一起调 prompt。

## 1. Runtime 入口流程

入口仍然符合 Message-first 原则：

1. 前端调用 `POST /api/agent/messages`。
2. `MessageRuntime.handle_message(...)` 创建 `AgentTurn`。
3. `ContextBuilder.build(project_id, ui_context)` 从数据库和 workspace 组装项目上下文。
4. `MessageRuntime` 注入运行时字段：
   - `runtime_session_id`
   - `runtime_turn_id`
   - `user_message`
5. `PromptComposer.compose(context, message)` 会生成一份 `prompt`。
6. 当前代码把这份 prompt 存到 `context["composed_prompt"]`。
7. 当前代码调用 adapter 时传入的是原始用户消息：
   - `adapter.send_message(external_session_id, message, context)`

关键点：`PromptComposer.compose(...)` 生成的 `context["composed_prompt"]` 目前不是所有 runtime 的实际输入。

## 2. ContextBuilder 当前输出字段

`backend/app/agent/context_builder.py` 当前输出：

```python
{
    "project_id": project.id,
    "project_name": project.name,
    "current_stage": project.current_stage,
    "workspace_path": str(workspace_path),
    "files": [
        {"role": f.role, "path": f.current_path, "status": f.status}
        for f in files
    ],
    "data_quality": data_quality,
    "schema_status": schema_status,
    "latest_result": latest_result,
    "latest_result_available": list(latest_result.keys()) if isinstance(latest_result, dict) else [],
    "latest_pipeline": {
        "job_id": latest_job.id,
        "status": latest_job.status,
        "progress": latest_job.progress,
        "steps": output.get("steps", []),
        "finished_at": latest_job.finished_at,
    } or None,
    "recent_artifacts": [
        {"type": a.type, "title": a.title, "path": a.path}
        for a in recent_artifacts
    ],
    "ui_view": ui_context.get("active_view") if ui_context else "agent_command_center",
    "available_actions": AVAILABLE_ACTIONS,
    "context_summary": ctx_content,
}
```

其中 `AVAILABLE_ACTIONS` 当前是：

```text
project.get_state
data.discover_source_files
data.ingest
data.validate
schema.infer
schema.apply_mapping
panel.build_category_day
analysis.run_diagnostics
analysis.run_psm_did
analysis.run_localgap
analysis.run_gps_uplift
analysis.run_full_pipeline
result.get_latest
artifact.read
chart.render
report.generate
memory.propose_update
```

## 3. PromptComposer.compose 当前模板

位置：`backend/app/agent/prompt_composer.py`

这份模板当前会被 `MessageRuntime` 生成并存入 `context["composed_prompt"]`。它在 mock runtime 中不作为分类依据；在 Claude Agent SDK runtime 中也不会直接被 `_build_prompt(...)` 使用。

当前完整模板如下：

```text
You are working inside Business Analysis Companion Workspace.
You are a business analysis assistant helping the user complete cyclical promotion evaluation, resource allocation optimization, and report generation.

Current project:
- project_id: {project_id}
- project_name: {project_name}
- current_stage: {current_stage}
- uploaded_files:
{files_str}
- data_quality: {data_quality}
- latest_result: {latest_result_summary}

Rules:
1. You may answer directly for explanations, discussion, and next-step suggestions.
2. When real data must be read, models must be run, charts must be generated, or reports must be generated, call the business_analysis tool.
3. Do not invent current data results from memory.
4. The project fact source is .analysis/project_manifest.json and .analysis/context_summary.md.
5. Do not directly modify user-level memory; only propose memory.propose_update.
6. High-risk actions require user approval.
7. When the user asks to load CSV data from a local machine directory, run a Claude Code style tool loop: project.get_state -> data.discover_source_files -> data.ingest -> schema.infer -> data.validate.
8. For data.discover_source_files, use payload {} for the saved source directory, or {"source_path": "<absolute directory>"} when the user provides a path.
9. For data.ingest, only select direct CSV candidates returned by discovery and pass selected_files: [{"source_path": "...", "role": "order_info|exposure_info|activity_timeline|unknown", "reason": "..."}]. Do not ingest files you cannot classify.
10. Never read local source data files directly; the backend copies them into the project workspace and updates the manifest.
11. Data load is complete only after data.validate succeeds. If discover, ingest, schema.infer, or data.validate fails, explain the exact partial state and propose concrete fixes.
12. Before citing project metrics or conclusions, call result.get_latest or artifact.read and cite the artifact path.
13. Do not overclaim causality: use "observed" for diagnostics, "directional" for LocalGap/PSM-DID, and "exploratory" for stub outputs.
14. For reports, ask the backend to generate report.generate and use .analysis/report_plan.json as the evidence skeleton.
15. Reports and business-facing summaries should default to Chinese unless the user explicitly requests another language.

Tool:
business_analysis(project_id, action, payload, reason)

Available actions:
{actions_str}

User message:
{user_message}
```

`files_str` 的格式：

```text
  - {role}: {path} ({status})
```

无文件时：

```text
  none
```

`latest_result_summary` 的格式：

```text
none
```

或：

```text
latest analysis result exists ({latest_result.stage or "unknown"})
```

## 4. Claude Agent SDK 当前实际 prompt

位置：`backend/app/agent/claude_agent_sdk_adapter.py`

真实 Claude Agent SDK 路径中，实际送入 SDK 的是 `_build_prompt(context, message)` 的返回值，不是 `context["composed_prompt"]`。

当前完整模板如下：

```text
You are a business analysis assistant working in project "{project_name}".

Project state:
- project_id: {project_id}
- current_stage: {current_stage}
- data_quality: {data_quality}
- project_facts: {json.dumps(project_facts, ensure_ascii=False)}

You may answer directly for discussion or clarification. When project state, data, analysis pipelines,
artifacts, reports, or memory candidates are needed, use exactly this tool:
business_analysis(project_id, action, payload, reason)

When calling business_analysis, always pass exactly this project_id: "{project_id}".
Do not use the route name, page name, project name, or any guessed identifier as project_id.

Only use project facts from the backend workspace context and tool results. Do not read local source
data files directly. For CSV directory ingest, first call business_analysis with action
"data.discover_source_files". Inspect filenames, headers, and previews, then call "data.ingest"
with selected_files: [{"source_path": "...", "role": "order_info|exposure_info|activity_timeline|unknown", "reason": "..."}].
For data-load requests, use a Claude Code style loop:
project.get_state -> data.discover_source_files -> data.ingest -> schema.infer -> data.validate.
Use the same source_path in discovery and ingest when the user gives an absolute directory. If any step
fails or validation does not pass, explain the partial state, list the blocking files/roles/issues, and
ask for the smallest concrete correction. Do not call data load complete until data.validate succeeds.
If latest_pipeline.steps contains analysis.run_gps_uplift with ok=true, say the GPS-Uplift step has run.
If latest_result_available contains "uplift", say uplift_result.json is available. Do not claim uplift has not run
when either of those facts is true.
Before citing metrics or recommendations, call result.get_latest or artifact.read and cite artifact paths.
Use observed/descriptive language for diagnostics-only claims, directional language for LocalGap or PSM-DID,
and exploratory language for stub outputs. When generating reports, use report.generate and treat
.analysis/report_plan.json as the evidence skeleton.
Reports and business-facing summaries should default to Chinese unless the user explicitly requests another language.

User message:
{message}
```

`project_facts` 当前只包含：

```python
{
    "latest_result_available": latest_result_available,
    "latest_pipeline": latest_pipeline,
    "recent_artifacts": recent_artifacts,
}
```

也就是说，SDK prompt 目前没有直接放入：

- uploaded files 明细
- schema_status
- available_actions 列表
- context_summary 全文
- workspace_path
- ui_view

这些字段虽然在 `ContextBuilder` 里存在，但 SDK prompt 没有显式使用。

## 5. Mock runtime 当前行为

位置：`backend/app/agent/claude_adapter.py`

mock runtime 当前不靠 prompt 推理，而是用原始用户消息做关键词意图识别：

```python
intent_message = context.get("user_message") or self._extract_user_message(message)
msg_lower = intent_message.lower()
```

它会识别这些意图：

- data load：触发 `project.get_state -> data.discover_source_files -> data.ingest -> schema.infer -> data.validate`
- full pipeline：触发 `project.get_state -> analysis.run_full_pipeline`
- panel build：触发 `project.get_state -> panel.build_category_day`
- report：触发 `project.get_state -> result.get_latest -> report.generate`
- generic analysis：触发 `project.get_state -> data.validate`
- status：触发 `project.get_state`

我这次修复的误判点是：之前 mock adapter 实际拿到的是拼接后的长 prompt，里面包含 data-load 规则，所以用户说 “full pipeline” 时也会被规则文本里的 data-load 关键词污染。现在 mock 使用 `context["user_message"]`，避免系统规则反过来影响 intent 分类。

## 6. SDK tool contract

Claude Agent SDK 注册的唯一业务工具仍是：

```text
business_analysis
```

工具描述：

```text
Run controlled business analysis actions inside the current project workspace.
```

工具 JSON schema：

```json
{
  "type": "object",
  "properties": {
    "project_id": { "type": "string" },
    "action": {
      "type": "string",
      "enum": [
        "project.get_state",
        "data.discover_source_files",
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
        "artifact.read",
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
```

SDK options 还会限制 allowed tools：

```python
allowed_tools = ["mcp__business_analysis__business_analysis"]
```

只有配置 `allow_builtin_read_tools` 时才会追加：

```python
["Read", "Glob", "Grep", "LS"]
```

真实 SDK 路径还做了一个运行时保护：即使模型传错 `project_id`，工具执行层也会用 `MessageRuntime` 注入的当前项目 ID 覆盖，避免把页面路由名或模型猜测 ID 写入工具网关。

## 7. 我看到的主要问题

1. 当前有两套 prompt：`PromptComposer.compose` 和 `ClaudeAgentSDKAdapter._build_prompt`。真实 SDK 路径使用后者，前者只被存进 context，容易让维护者以为改了 `PromptComposer` 就会改真实 agent 行为。

2. mock runtime 不使用 prompt。这个对 deterministic 测试有好处，但也意味着改 prompt 后，mock E2E 不能证明真实模型会按新 prompt 行动。

3. 已修复：真实 SDK prompt 原先没有显式列出 `project_id`，模型可能把页面路由名 `agent-analysis-test` 当成项目 ID。现在 prompt 明确写入当前 `project_id`，工具执行层也会强制绑定 runtime project。

4. SDK prompt 没有纳入 `context_summary`、uploaded files、schema status、available actions 等上下文。agent 可能需要先调 `project.get_state` 才能看到更多事实；这符合“工具为事实源”的原则，但会牺牲首轮判断质量。

5. `PromptComposer` 说项目事实源是 `.analysis/project_manifest.json` 和 `.analysis/context_summary.md`，但 SDK prompt 没有显式放入 context_summary 内容，也不鼓励先 `project.get_state` 读取 manifest 摘要。

6. data-load 规则比较具体，但 full pipeline、panel build、report generate 的策略规则较少。比如什么时候先 validate、什么时候直接请求 high-risk approval，目前依赖模型自行判断或 mock 的关键词逻辑。

7. 中文输出规则只写在 prompt 末尾，可能不够强。业务总结、审批说明、错误恢复都应该更明确地默认中文，但 action、artifact path、字段名保留英文。

8. `project_facts` 以 JSON 字符串嵌入 prompt，结构清楚但不易读。后续可以考虑改成短 YAML/Markdown 列表，或保留 JSON 但限制字段长度。

## 8. 可以一起优化的方向

建议下一步先决定一个架构问题：

```text
是否把 PromptComposer 作为唯一 prompt 入口？
```

如果是，可以让 `ClaudeAgentSDKAdapter._build_prompt(...)` 直接使用 `context["composed_prompt"]`，再把 SDK 特有的内容作为附加段落，而不是维护第二套模板。

我建议优化目标按这个顺序：

1. 统一 prompt 入口，避免双轨。
2. 明确每类用户意图的 tool policy：
   - status/read
   - data load
   - schema/validation
   - panel build
   - full pipeline
   - report generation
   - memory proposal
3. 把 `context_summary` 以压缩摘要形式纳入真实 SDK prompt。
4. 明确中文业务输出规范。
5. 明确“何时必须先 `result.get_latest` 或 `artifact.read`”。
6. 给 high-risk approval 的 `reason` 写固定规范，方便前端展示和审计。
## 9. SDK skill loading update

The real `claude_agent_sdk` request now explicitly loads the project skill:

```python
ClaudeAgentOptions(
    skills=["business-analysis"],
    allowed_tools=["mcp__business_analysis__business_analysis"],
    ...
)
```

The workspace manager creates this project-local skill file for new projects:

```text
.claude/skills/business-analysis/SKILL.md
```

The SDK adapter also ensures the same skill file exists for existing projects before
creating/resuming a real SDK session. `runtime_diagnostic` now exposes:

```json
{
  "skills": ["business-analysis"],
  "skill_allowed_tools": ["Skill(business-analysis)"],
  "workspace_path": "<project workspace path>"
}
```

This makes the skill part of the SDK request instead of relying on prompt text alone.
