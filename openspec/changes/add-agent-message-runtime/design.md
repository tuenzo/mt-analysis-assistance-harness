## Overview

本变更实现 message-first 主循环，包括 MessageRuntime、ClaudeRuntimeAdapter 接口 + Mock 实现、SSE 事件流。核心设计是：所有用户输入进入统一消息入口，MessageRuntime 负责编排 context、调用 adapter、持久化事件、转发 SSE。

## Message Runtime 流程

```
POST /api/agent/messages
  │
  ├─ [session] = get_or_create_session(project_id)
  ├─ [turn] = AgentTurn(session_id, user_message)
  ├─ [context] = ContextBuilder.build(project_id, ui_context)
  │
  ├─ for [event] in ClaudeAdapter.send_message(session, message, context):
  │     ├─ AgentEvent.create(event)
  │     ├─ if tool_call → route to AnalysisToolGateway (stub for now)
  │     └─ SSE.publish(session_id, event)
  │
  └─ return {turn_id, session_id, status, event_stream_url}
```

## SSE 事件格式

每个事件是 JSON 行：
```
data: {"type": "assistant_message_delta", "turn_id": "xxx", "delta": "正在分析..."}
data: {"type": "tool_call_started", "turn_id": "xxx", "tool": "business_analysis", "action": "data.validate"}
data: {"type": "tool_call_finished", "turn_id": "xxx", "action": "data.validate", "ok": true}
data: {"type": "final_answer", "turn_id": "xxx", "message": "分析完成"}
```

## Mock Adapter 行为

MockClaudeRuntimeAdapter.send_message() 模拟以下行为：

1. **普通对话**（"你好"、"今天天气"）：
   - yield assistant_message_delta
   - yield final_answer

2. **状态查询**（"当前项目状态"）：
   - yield assistant_message_delta
   - yield tool_call_started (project.get_state)
   - yield tool_call_finished
   - yield final_answer (mock 状态摘要)

3. **分析请求**（"帮我分析这批数据"）：
   - yield assistant_message_delta
   - yield tool_call_started (analysis.run_full_pipeline)
   - yield job_started
   - yield job_progress (多次)
   - yield job_finished
   - yield artifact_created
   - yield final_answer

## Prompt Composer 模板

```
你正在 Business Analysis Companion Workspace 中工作。

你的身份：你是商业分析助手，负责帮助用户完成周期性促销评估、资源配置优化和报告生成。

当前项目：
- project_id: {project_id}
- 项目名称: {project_name}
- 当前阶段: {current_stage}
- 已上传文件: {files}
- 数据质量状态: {data_quality}
- 最新分析结果: {latest_result_summary}

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
{message}
```

## Context Builder 返回值

```python
{
    "project_id": "proj_001",
    "project_name": "Keemart Payday Promotion",
    "current_stage": "data_intake",
    "workspace_path": "./workspaces/proj_001",
    "files": [
        {"role": "order_info", "path": "data/raw/order_info.csv", "status": "uploaded"}
    ],
    "data_quality": "unknown",
    "schema_status": "pending",
    "latest_result": None,
    "ui_view": "agent_command_center",
    "available_actions": ["project.get_state", "data.ingest", "data.validate", ...]
}
```

## Session 管理

AnalysisSession 表映射：
- `runtime_provider`: "mock" | "claude_agent_sdk"
- `external_session_id`: Claude SDK 的 session id（mock 时生成随机字符串）
- `status`: active | paused | completed | interrupted | error

MessageRuntime 不直接操作数据库，通过 SessionStore 间接管理。