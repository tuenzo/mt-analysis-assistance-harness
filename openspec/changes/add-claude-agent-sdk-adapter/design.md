## Overview

本变更实现真实的 Claude Agent SDK adapter，替换 MVP 阶段的 MockClaudeRuntimeAdapter。核心目标是让系统能利用 Claude 的推理能力进行真正的商业分析对话。

## Adapter 接口实现

```python
class ClaudeAgentSDKAdapter(ClaudeRuntimeAdapter):
    def __init__(self, settings: AgentRuntimeConfig, tool_gateway: AnalysisToolGateway):
        self.settings = settings
        self.gateway = tool_gateway
        self._sessions: dict[str, Any] = {}
        self._mcp_server = BusinessAnalysisMCPServer(tool_gateway)

    def create_session(self, project_id: str) -> str:
        workspace_path = self.settings.workspace_root / project_id
        session = Claude.AgentSession(
            cwd=str(workspace_path),
            permissionMode=self.settings.permission_mode,
            mcpServers=[self._mcp_server],
            settingSources=["user", "project"] if self.settings.enable_user_setting_sources else [],
        )
        external_id = session.id
        self._sessions[external_id] = session
        return external_id

    def send_message(self, session_id: str, message: str, context: dict) -> Generator[dict, None, None]:
        session = self._sessions.get(session_id)
        if not session:
            raise ValueError(f"Session {session_id} not found")

        prompt = self._build_prompt(context, message)

        for event in session.generate(prompt):
            yield self._map_sdk_event(event)
```

## MCP Server 实现

```python
class BusinessAnalysisMCPServer:
    def __init__(self, gateway: AnalysisToolGateway):
        self.gateway = gateway

    def get_tools(self):
        return [
            {
                "name": "business_analysis",
                "description": "Run controlled business analysis actions inside the current analysis workspace.",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "project_id": {"type": "string"},
                        "action": {
                            "type": "string",
                            "enum": [e.value for e in BusinessAnalysisAction]
                        },
                        "payload": {"type": "object"},
                        "reason": {"type": "string"}
                    },
                    "required": ["project_id", "action", "payload", "reason"]
                }
            }
        ]

    def handle_tool_call(self, tool_name: str, parameters: dict) -> dict:
        result = self.gateway.execute(
            tool_call_id=parameters.get("_tool_call_id"),
            project_id=parameters["project_id"],
            action=BusinessAnalysisAction(parameters["action"]),
            payload=parameters["payload"],
            reason=parameters.get("reason", "")
        )
        return {"ok": result.ok, "summary": result.summary, ...}
```

## 配置项

```python
@dataclass
class AgentRuntimeConfig:
    provider: str = "mock"  # "mock" | "claude_agent_sdk"
    workspace_root: Path = Path("./workspaces")
    enable_user_setting_sources: bool = True
    permission_mode: str = "dontAsk"  # "dontAsk" | "manual"
    allow_builtin_read_tools: bool = False
    allow_global_memory_write: bool = False
```

## Streaming Input Mode

Claude Agent SDK 支持 streaming input mode，适合持久交互式 session。

```python
options = {
    "streaming": True,
    "cwd": workspace_path,
    "permissionMode": "dontAsk",
    "allowedTools": ["mcp__business_analysis__business_analysis"],
    "mcpServers": [mcp_server],
    "settingSources": ["user", "project"],
}
```

## Session Persistence

```python
# 创建时
session_record = AnalysisSession(
    id=uuid.uuid4().hex,
    project_id=project_id,
    runtime_provider="claude_agent_sdk",
    external_session_id=external_id,  # Claude SDK 的 session id
    status="active"
)

# 恢复时
def resume_session(self, session_id: str, project_id: str):
    session_record = self.session_store.get(session_id)
    external_id = session_record.external_session_id
    session = Claude.AgentSession(external_id, cwd=workspace_path)
    self._sessions[session_id] = session
```

## 配置切换

```
ANTHROPIC_API_KEY 环境变量存在 + config.provider="claude_agent_sdk"
  → 使用 ClaudeAgentSDKAdapter

否则
  → 自动降级到 MockClaudeRuntimeAdapter（不报错）
```

优雅降级保证开发阶段无需 API key 也能运行。

## 事件映射

SDK 事件 → AgentEvent：
- `assistant_message` → `assistant_message_delta`
- `tool_use` → `tool_call_started`（action=tool.name）
- `tool_result` → `tool_call_finished`
- `error` → `tool_call_failed` 或 `runtime_error`
- `final` → `final_answer`