import os
import uuid
from typing import Generator, Optional
from pathlib import Path
from datetime import datetime

try:
    import anthropic
    from anthropic import Anthropic
    HAS_ANTHROPIC_SDK = True
except ImportError:
    HAS_ANTHROPIC_SDK = False

from app.agent.claude_adapter import ClaudeRuntimeAdapter
from app.tools.schemas import BusinessAnalysisAction
from app.tools.gateway import get_gateway


class BusinessAnalysisMCPServer:
    """In-process MCP server for business_analysis tool"""

    def __init__(self, gateway):
        self.gateway = gateway
        self._tool_call_id = 0

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
        tool_call_id = f"tc_{uuid.uuid4().hex[:12]}"
        result = self.gateway.execute(
            tool_call_id=tool_call_id,
            project_id=parameters["project_id"],
            action_str=parameters["action"],
            payload=parameters["payload"],
            reason=parameters.get("reason", ""),
        )
        return {
            "ok": result.ok,
            "summary": result.summary,
            "action": result.action,
            "artifacts": result.artifacts,
            "error": result.error,
        }


class ClaudeAgentSDKAdapter(ClaudeRuntimeAdapter):
    """
    Real Claude Agent SDK adapter

    Requires ANTHROPIC_API_KEY environment variable and config.provider="claude_agent_sdk"
    Falls back to MockClaudeRuntimeAdapter if SDK is not available or no API key
    """

    def __init__(self, settings: dict | None = None):
        from app.core.config import settings as app_settings

        self._settings = settings or {}
        self._sessions: dict[str, dict] = {}
        self._interrupted: set[str] = set()
        self._gateway = get_gateway()
        self._mcp_server = BusinessAnalysisMCPServer(self._gateway)

        self._api_key = os.environ.get("ANTHROPIC_API_KEY") or app_settings.anthropic_api_key
        self._base_url = os.environ.get("ANTHROPIC_API_BASE_URL") or app_settings.anthropic_api_base_url or None
        self._model = os.environ.get("ANTHROPIC_API_MODEL") or app_settings.anthropic_api_model or "claude-opus-4-5-20250501"
        self._client: Optional["Anthropic"] = None
        self._permission_mode = self._settings.get("permission_mode", "dontAsk")
        self._enable_user_settings = self._settings.get("enable_user_setting_sources", True)
        self._workspace_root = Path(self._settings.get("workspace_root", "./workspaces"))

        if self._api_key and HAS_ANTHROPIC_SDK:
            if self._base_url:
                self._client = Anthropic(
                    api_key=self._api_key,
                    base_url=self._base_url.rstrip("/") + "/",
                    default_headers={"Authorization": f"Bearer {self._api_key}"}
                )
            else:
                self._client = Anthropic(api_key=self._api_key)

    def create_session(self, project_id: str) -> str:
        if not self._client:
            return self._create_mock_session(project_id)

        workspace_path = self._workspace_root / project_id
        workspace_path.mkdir(parents=True, exist_ok=True)

        session_id = f"sdk_{uuid.uuid4().hex[:12]}"
        self._sessions[session_id] = {
            "project_id": project_id,
            "workspace_path": str(workspace_path),
            "interrupted": False,
            "messages": [],
        }
        return session_id

    def _create_mock_session(self, project_id: str) -> str:
        session_id = f"mock_{uuid.uuid4().hex[:12]}"
        self._sessions[session_id] = {"project_id": project_id, "interrupted": False}
        return session_id

    def resume_session(self, session_id: str, project_id: str) -> None:
        if session_id not in self._sessions:
            self._sessions[session_id] = {"project_id": project_id, "interrupted": False}

    def send_message(self, session_id: str, message: str, context: dict) -> Generator[dict, None, None]:
        if session_id in self._interrupted:
            self._interrupted.discard(session_id)
            return

        session = self._sessions.get(session_id, {})
        is_sdk_session = session_id.startswith("sdk_")

        if not self._client or not is_sdk_session:
            yield from self._mock_send_message(session_id, message, context)
            return

        workspace_path = session.get("workspace_path", str(self._workspace_root / session.get("project_id", "")))
        turn_id = f"turn_{uuid.uuid4().hex[:8]}"

        yield {"type": "assistant_message_delta", "turn_id": turn_id, "delta": ""}

        tools = self._mcp_server.get_tools()

        prompt = self._build_prompt(context, message)

        try:
            response = self._client.messages.create(
                model=self._model,
                max_tokens=4096,
                tools=tools,
                messages=[{"role": "user", "content": prompt}],
            )

            for content_block in response.content:
                if content_block.type == "text":
                    yield {"type": "assistant_message_delta", "turn_id": turn_id, "delta": content_block.text}
                elif content_block.type == "tool_use":
                    tool_name = content_block.name
                    tool_input = content_block.input

                    yield {
                        "type": "tool_call_started",
                        "turn_id": turn_id,
                        "tool": tool_name,
                        "action": tool_input.get("action", tool_name),
                        "payload": tool_input,
                    }

                    result = self._mcp_server.handle_tool_call(tool_name, tool_input)

                    yield {
                        "type": "tool_call_finished",
                        "turn_id": turn_id,
                        "tool": tool_name,
                        "action": tool_input.get("action", tool_name),
                        "ok": result.get("ok", False),
                        "summary": result.get("summary", ""),
                    }

            yield {"type": "final_answer", "turn_id": turn_id, "message": "处理完成"}

        except Exception as e:
            yield {"type": "runtime_error", "turn_id": turn_id, "error": str(e)}

    def _mock_send_message(self, session_id: str, message: str, context: dict) -> Generator[dict, None, None]:
        from app.agent.claude_adapter import MockClaudeRuntimeAdapter
        mock = MockClaudeRuntimeAdapter()
        yield from mock.send_message(session_id, message, context)

    def interrupt(self, session_id: str) -> None:
        self._interrupted.add(session_id)
        if session_id in self._sessions:
            self._sessions[session_id]["interrupted"] = True

    def _build_prompt(self, context: dict, message: str) -> str:
        project_name = context.get("project_name", "unknown")
        current_stage = context.get("current_stage", "unknown")
        data_quality = context.get("data_quality", "unknown")

        prompt = f"""你是一个商业分析助手。用户正在与项目「{project_name}」对话。

当前项目状态：
- 项目阶段: {current_stage}
- 数据质量: {data_quality}

可用工具: business_analysis
- project.get_state: 获取项目状态
- data.validate: 校验数据文件
- panel.build_category_day: 构建分析面板
- analysis.run_diagnostics: 运行诊断分析
- analysis.run_localgap: 运行增量分解
- analysis.run_psm_did: 运行因果推断
- report.generate: 生成报告

用户消息: {message}

请根据用户消息，调用适当的工具来完成分析任务。"""

        return prompt


def get_claude_adapter(settings: dict | None = None) -> ClaudeRuntimeAdapter:
    """
    Get appropriate adapter based on configuration and API key availability
    """
    from app.core.config import settings as app_settings

    api_key = os.environ.get("ANTHROPIC_API_KEY") or app_settings.anthropic_api_key
    provider = (settings or {}).get("provider", "mock")

    if provider == "claude_agent_sdk" and api_key and HAS_ANTHROPIC_SDK:
        return ClaudeAgentSDKAdapter(settings)
    else:
        from app.agent.claude_adapter import MockClaudeRuntimeAdapter
        return MockClaudeRuntimeAdapter()
