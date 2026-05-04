## Tasks

### Phase 1: Message Runtime 核心

- [ ] **T1.1** — 创建 `backend/app/agent/session_store.py`
  ```python
  class SessionStore:
      def create_session(self, project_id: str, provider: str = "mock") -> AnalysisSession
      def get_session(self, session_id: str) -> AnalysisSession | None
      def update_session(self, session_id: str, **kwargs)
  ```
- [ ] **T1.2** — 创建 `backend/app/agent/event_mapper.py`
  ```python
  class EventMapper:
      def map_claude_event(self, raw_event: dict) -> AgentEvent
      def to_sse_format(self, event: AgentEvent) -> str
  ```
- [ ] **T1.3** — 创建 `backend/app/agent/context_builder.py`
  ```python
  class ContextBuilder:
      def build(self, project_id: str, ui_context: dict | None) -> dict
      # 返回 {project_name, current_stage, files, data_quality, latest_result, ui_view}
  ```
- [ ] **T1.4** — 创建 `backend/app/agent/prompt_composer.py`
  ```python
  class PromptComposer:
      def compose(self, context: dict, user_message: str) -> str
      # 构造 system prompt，包含：身份、当前项目状态、工作规则、可用 actions、用户消息
  ```

### Phase 2: Claude Adapter

- [ ] **T2.1** — 定义 `ClaudeRuntimeAdapter` 接口（ABC）
  ```python
  class ClaudeRuntimeAdapter(ABC):
      @abstractmethod
      def create_session(self, project_id: str) -> str: ...
      @abstractmethod
      def resume_session(self, session_id: str, project_id: str) -> None: ...
      @abstractmethod
      def send_message(self, session_id: str, message: str, context: dict) -> Generator[dict, None, None]: ...
      @abstractmethod
      def interrupt(self, session_id: str) -> None: ...
  ```
- [ ] **T2.2** — 创建 `MockClaudeRuntimeAdapter`
  ```python
  class MockClaudeRuntimeAdapter(ClaudeRuntimeAdapter):
      def send_message(self, session_id, message, context) -> Generator[dict, None, None]:
          # 模拟：
          # 1. yield assistant_message_delta ("正在分析...")
          # 2. yield tool_call_started (project.get_state)
          # 3. yield tool_call_finished
          # 4. yield final_answer (mock 结论)
  ```
- [ ] **T2.3** — 添加配置：`config.py` 的 `agent_runtime.provider`（mock | claude_agent_sdk）

### Phase 3: Message Runtime 主循环

- [ ] **T3.1** — 创建 `backend/app/agent/message_runtime.py`
  ```python
  class MessageRuntime:
      def handle_message(self, project_id: str, session_id: str | None, message: str, ui_context: dict) -> dict:
          # 1. session = get_or_create_session()
          # 2. turn = AgentTurn(session_id, message)
          # 3. context = context_builder.build(project_id, ui_context)
          # 4. for event in claude_adapter.send_message(session, message, context):
          #       persist event
          #       forward to SSE stream
          # 5. return {turn_id, session_id, status, event_stream_url}
  ```
- [ ] **T3.2** — 工具调用路由：当收到 `tool_call_started` 事件时，需要识别 action 并转发到 AnalysisToolGateway（暂不实现 gateway，先 mock tool result 返回）

### Phase 4: Agent Messages API

- [ ] **T4.1** — 创建 `backend/app/api/agent_messages.py`
  ```python
  @router.post("/agent/messages")
  def send_message(body: AgentMessageRequest) -> AgentMessageResponse:
      runtime = get_message_runtime()
      return runtime.handle_message(body.project_id, body.session_id, body.message, body.ui_context)

  @router.get("/agent/sessions/{session_id}/events")
  async def stream_events(session_id: str):
      # SSE stream，从 SessionStore 读取事件 buffer 或 pubsub
      ...

  @router.post("/agent/sessions/{session_id}/interrupt")
  def interrupt_session(session_id: str):
      adapter = get_adapter(session_id)
      adapter.interrupt(session_id)
  ```
- [ ] **T4.2** — `AgentMessageRequest` schema
  ```python
  class AgentMessageRequest(BaseModel):
      project_id: str
      session_id: str | None = None
      message: str
      ui_context: dict | None = None
  ```
- [ ] **T4.3** — 注册到 `main.py` 的 `app.include_router(agent_messages.router, prefix="/api")`

### Phase 5: Session 管理 API

- [ ] **T5.1** — 创建 `GET /api/projects/{project_id}/sessions` — 列出项目的 sessions
- [ ] **T5.2** — 创建 `GET /api/agent/sessions/{session_id}` — 获取 session 详情

### Phase 6: 前端改造（参考）

- [ ] **T6.1** — 前端 sendMessage 不再调用 `/api/agent/runs`，改为 `POST /api/agent/messages`
- [ ] **T6.2** — 前端 SSE 监听 `/api/agent/sessions/{session_id}/events`，渲染事件到 Agent Command Center
- （前端改动不在本 change 内，参考实现见 spec）

### Phase 7: 测试

- [ ] **T7.1** — `test_message_runtime.py` — 发送消息返回 turn_id
- [ ] **T7.2** — `test_sse_events.py` — 事件流正确推送
- [ ] **T7.3** — `test_mock_adapter.py` — mock 返回模拟事件
- [ ] **T7.4** — `test_interrupt.py` — interrupt 正确停止 session
- [ ] **T7.5** — 运行所有测试，修复问题

---

## 验收标准

1. `POST /api/agent/messages` 返回 turn_id 和 event_stream_url
2. 消息进入后 mock adapter 能返回 assistant_message_delta 和 final_answer 事件
3. SSE `/api/agent/sessions/{session_id}/events` 能持续接收事件
4. `POST /api/agent/sessions/{session_id}/interrupt` 能中断 session
5. Tool call 事件能正确路由（暂 mock result）
6. 所有测试通过