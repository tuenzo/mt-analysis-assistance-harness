## Tasks

### Phase 1: Claude Agent SDK Adapter

- [x] **T1.1** — 创建 `backend/app/agent/claude_agent_sdk_adapter.py`
  ```python
  class ClaudeAgentSDKAdapter(ClaudeRuntimeAdapter):
      def __init__(self, settings: Settings):
          self.settings = settings
          self._sessions: dict[str, Any] = {}

      def create_session(self, project_id: str) -> str:
          # 使用 project workspace 作为 cwd
          # 调用 Claude Agent SDK 创建 session
          # 返回 external_session_id

      def send_message(self, session_id: str, message: str, context: dict) -> Generator[dict, None, None]:
          # 构造 prompt（用 PromptComposer）
          # 调用 SDK streaming mode
          # yield events: assistant_message_delta, tool_call_started, etc.
  ```
- [x] **T1.2** — 配置 `config.py` 的 `agent_runtime` 部分：
  ```python
  class AgentRuntimeConfig(BaseSettings):
      provider: str = "mock"  # "mock" | "claude_agent_sdk"
      workspace_root: Path = Path("./workspaces")
      enable_user_setting_sources: bool = True
      permission_mode: str = "dontAsk"  # "dontAsk" | "manual"
      allow_builtin_read_tools: bool = False
  ```

### Phase 2: MCP Server 注册

- [x] **T2.1** — 创建 in-process MCP server
  ```python
  from anthropic.agent import MCPServer

  class BusinessAnalysisMCPServer:
      def __init__(self, tool_gateway: AnalysisToolGateway):
          self.gateway = tool_gateway

      def get_tools(self):
          return [
              {
                  "name": "business_analysis",
                  "description": "Run controlled business analysis actions",
                  "input_schema": {
                      "type": "object",
                      "properties": {
                          "project_id": {"type": "string"},
                          "action": {"type": "string", "enum": [...]},
                          "payload": {"type": "object"},
                          "reason": {"type": "string"}
                      }
                  }
              }
          ]

      def handle_tool_call(self, tool_name: str, parameters: dict):
          return self.gateway.execute(...)
  ```
- [x] **T2.2** — adapter 中注册 MCP server：
  ```python
  mcp_server = BusinessAnalysisMCPServer(tool_gateway)
  options = {
      "mcpServers": [mcp_server],
      "allowedTools": ["mcp__business_analysis__business_analysis"],
  }
  ```

### Phase 3: Streaming Input Mode

- [x] **T3.1** — 配置 streaming input mode
  ```python
  options = {
      "streaming": True,  # streaming input mode
      "cwd": workspace_path,
  }
  ```
- [x] **T3.2** — 处理 streaming 响应：
  - 从流中读取 assistant_message_delta
  - 检测 tool_call_started 事件
  - 处理 tool result 并继续

### Phase 4: Session Persistence

- [x] **T4.1** — `external_session_id` 持久化到 `analysis_sessions.external_session_id`
- [x] **T4.2** — `resume_session` 时用 stored external_session_id 恢复
- [x] **T4.3** — session 状态同步（active/paused/completed/interrupted/error）

### Phase 5: Hooks & Permissions

- [x] **T5.1** — 配置 permission mode
  ```python
  permissionMode = "dontAsk"  # MVP 默认不询问
  ```
- [x] **T5.2** — 工具调用前 hooks（可记录审计日志）
  ```python
  def before_tool_call(tool_name, parameters):
      log_tool_call(tool_name, parameters)
  ```
- [x] **T5.3** — 可选：添加 `canUseTool` callback 自定义权限逻辑

### Phase 6: 文档与配置

- [x] **T6.1** — 创建 `docs/CLAUDE_ADAPTER_SETUP.md`
  ```
  # Claude Agent SDK Adapter 配置指南

  ## 环境要求
  - ANTHROPIC_API_KEY 环境变量
  - anthropic >= 0.x.x

  ## 启用真实 SDK

  设置环境变量或配置：

  ```bash
  export ANTHROPIC_API_KEY=your_api_key
  ```

  或在 config 中：
  ```python
  agent_runtime:
    provider: claude_agent_sdk
    permission_mode: dontAsk
  ```

  ## Mock vs Real

  - `provider: mock` — 使用 MockClaudeRuntimeAdapter，不消耗 API
  - `provider: claude_agent_sdk` — 使用真实 Claude SDK，需 API key
  ```
- [x] **T6.2** — 添加优雅 fallback：没有 API key 时自动降级到 mock

### Phase 7: 测试

- [x] **T7.1** — `test_claude_adapter_interface.py` — 验证接口一致性（mock 和 real 实现同一接口）
- [x] **T7.2** — `test_claude_adapter_streaming.py` — streaming 模式正确 yield events（需要 api key，标记为 integration test）
- [x] **T7.3** — `test_session_persistence.py` — external_session_id 正确存储和恢复
- [x] **T7.4** — 运行测试，修复问题

---

## 验收标准

1. `ClaudeAgentSDKAdapter` 实现 `ClaudeRuntimeAdapter` 接口
2. 配置 `provider: claude_agent_sdk` 后，系统使用真实 SDK 而非 mock
3. MCP server 正确注册 `business_analysis` 工具
4. streaming mode 正确 yield assistant_message_delta 和 tool_call 事件
5. `external_session_id` 持久化到数据库
6. 无 API key 时系统优雅降级到 mock
7. 所有测试通过